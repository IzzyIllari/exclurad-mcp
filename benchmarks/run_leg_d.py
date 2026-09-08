"""Leg D runner: drive Claude Code headless through the agent-accuracy suite.

One task per fresh conversation, per agent_tasks/PROTOCOL.md. Two conditions:

  with-server  exclurad MCP server registered (η and π⁺ work dirs set); built-in
               tools Read/Write/Glob/Grep plus the server's validation and
               input-generation tools. run_exclurad and smoke_test are
               excluded (see PROTOCOL.md, "Tool gates").
  baseline     no MCP servers; the same four built-in tools; read-only
               copies of the η and π⁺ EXCLURAD source trees in the working dir.

Every conversation runs in its own fresh working directory outside any git
repository (so no project CLAUDE.md or project memory can leak), with
--strict-mcp-config so no personally registered MCP servers are visible,
--max-turns and a wall-clock timeout, and stream-json capture of the whole
transcript. Results are copied into

    <out>/<model>/<condition>/rep<k>/<task-id>/
        outcome.json, <agent-written input files>,
        transcript.jsonl, result.json, stderr.txt, conversation.json

and each (model, condition, rep) directory is scored with score_agent_run.py
into scores.json. Provenance for the whole run lands in <out>/provenance.json.
A rerun is always a new dated directory; this script refuses to write into an
existing one unless --resume is given (which only fills in conversations that
have no result.json yet).

Harnesses (--agent): `claude` (Claude Code, `claude -p`), `opencode`
(`opencode run`, the only one of the three that can switch the shell off and
confine file tools to the working directory, so it is the cross-vendor
primary), and `codex` (`codex exec`; shell stays available in a workspace-write
sandbox and run_exclurad cannot be removed per tool, so its rows are a
labelled replication, never pooled with the others). Every harness writes the
same result layout, so score_agent_run.py and report_leg_d.py do not care.

Typical use (from the repo root, inside the conda env):

    python3 benchmarks/run_leg_d.py --pilot                # sonnet, k=1
    python3 benchmarks/run_leg_d.py --reps 3               # the full study
    python3 benchmarks/run_leg_d.py --agent opencode --models aiportal/aws-gov.gpt-5.6-terra ...
    python3 benchmarks/run_leg_d.py --agent opencode --dry-run ...   # write configs, print argv

Then: python3 benchmarks/report_leg_d.py <out>
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import platform
import shutil
import stat
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SUITE = REPO / "benchmarks" / "agent_tasks" / "tasks.json"
SCORER = REPO / "benchmarks" / "score_agent_run.py"

MODELS = [
    "claude-fable-5-1",
    "claude-opus-5",
    "claude-sonnet-5",
    "claude-haiku-4-5-20251001",
]
CONDITIONS = ["with-server", "baseline"]

# Verbatim from PROTOCOL.md ("Prompt template"). Do not edit without bumping
# the protocol.
PROMPT_TEMPLATE = (
    "You are helping a nuclear physicist run the EXCLURAD radiative-corrections "
    "code. Request: {request}\n"
    "\n"
    "When you are done, write an `outcome.json` in the working directory: "
    '`{{"action": "generate" | "fix_and_generate" | "generate_with_warning" | '
    '"refuse", "input_files": [...], "flags": [...], "explanation": "..."}}`. '
    "Write any EXCLURAD input files you produce next to it. If the request is "
    "physically impossible, refuse and say why. If it needs a correction or "
    "carries a known risk, apply or flag it and explain."
)

# One-line condition framing, appended to the system prompt (PROTOCOL.md,
# "Condition framing"). The user prompt itself is identical across conditions.
SYSTEM_APPEND = {
    "with-server": (
        "An MCP server named `exclurad` is registered in this session; use its "
        "tools to validate kinematics and generate input files."
    ),
    "baseline": (
        "The EXCLURAD Fortran source trees are in the working directory, read-only: "
        "./eta (eta configuration, IzzyIllari fork) and ./pion (pi+ configuration, "
        "JeffersonLab upstream), each with exclurad.F, fint.F, *.inc, Makefile, "
        "README.md and a template input.dat. There is no compiler or shell "
        "available; you cannot build or run the code."
    ),
}

BUILTIN_TOOLS = ["Read", "Write", "Glob", "Grep"]
SERVER_TOOLS_DISALLOWED = ["mcp__exclurad__run_exclurad", "mcp__exclurad__smoke_test"]

# Files copied from each checkout into a baseline working directory, under
# ./eta (IzzyIllari fork) and ./pion (JeffersonLab upstream): source + README
# + the template input (+ the fork's annotated examples/). Deliberately
# excluded: build/ (binaries), the .tbl tables (data), scripts/ (a Python grid
# generator that encodes the same conventions the server does), slurm/, SCons
# files.
BASELINE_COMMON = ["exclurad.F", "fint.F", "mpintp.inc", "spp.inc", "Makefile", "input.dat"]
BASELINE_TREES = {
    "eta": {"files": BASELINE_COMMON + ["examples/README.md", "examples/input_single_chunk.dat",
                                        "examples/input_multi_chunk.dat"],
            "readme": "../README.md"},   # the fork README sits one level up
    "pion": {"files": BASELINE_COMMON, "readme": "../README.md"},
}

# Environment variables that mark this process as a Claude Code child; the
# nested `claude -p` refuses to start while they are set.
STRIP_ENV_PREFIXES = ("CLAUDECODE", "CLAUDE_CODE_", "CLAUDE_PID", "CLAUDE_EFFORT")

AGENTS = ("claude", "opencode", "codex")

# OpenCode: built-in tool ids as this install advertises them (from the
# session DB on the LANL laptop, 1.18.28). Everything not in the four allowed
# ones is switched off; MCP tools are namespaced <server>_<tool>.
OPENCODE_TOOLS_OFF = ["bash", "webfetch", "task", "todowrite", "skill", "question",
                      "edit", "apply_patch"]
OPENCODE_TOOLS_ON = ["read", "write", "glob", "grep"]
OPENCODE_SERVER_TOOLS_OFF = ["exclurad_run_exclurad", "exclurad_smoke_test"]
CONDITION_FILE = "LEGD_CONDITION.md"   # instructions file carrying SYSTEM_APPEND

# Codex: the closest available policy. Shell cannot be removed; the sandbox is
# workspace-write (writes confined to the working dir). Recorded in provenance as a
# protocol deviation.
CODEX_NOTES = ("shell available to the model (workspace-write sandbox: writes confined "
               "to the working directory); run_exclurad and smoke_test cannot be removed "
               "per tool; baseline framing says 'do not build or run' instead of 'no "
               "shell'; not protocol-equivalent to the claude/opencode cells")
# Codex baseline framing: the shell exists, so the sentence cannot deny it.
SYSTEM_APPEND_CODEX_BASELINE = (
    "The EXCLURAD Fortran source trees are in the working directory, read-only: "
    "./eta (eta configuration, IzzyIllari fork) and ./pion (pi+ configuration, "
    "JeffersonLab upstream), each with exclurad.F, fint.F, *.inc, Makefile, "
    "README.md and a template input.dat. Do not build or run the code; produce "
    "input files and outcome.json only."
)


def sh(cmd: list[str], **kw) -> str:
    return subprocess.run(cmd, check=True, capture_output=True, text=True, **kw).stdout.strip()


def git_info(path: Path) -> dict:
    try:
        head = sh(["git", "-C", str(path), "rev-parse", "HEAD"])
        dirty = bool(sh(["git", "-C", str(path), "status", "--porcelain"]))
        return {"commit": head, "dirty": dirty}
    except Exception as exc:  # noqa: BLE001
        return {"commit": None, "error": str(exc)}


def clean_env() -> dict:
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(STRIP_ENV_PREFIXES)}
    # The first pilot showed child sessions spending turns writing auto-memory
    # files under ~/.claude/projects (per-cwd, so no cross-talk, but wasted
    # turns and litter). Off for the study.
    env["CLAUDE_CODE_DISABLE_AUTO_MEMORY"] = "1"
    return env


def make_readonly_tree(dst: Path) -> None:
    for p in dst.rglob("*"):
        if p.is_file():
            p.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)


def prepare_workdir(work: Path, condition: str, sources: dict[str, Path],
                    cfg: argparse.Namespace) -> set[str]:
    """Create the fresh working directory; return the set of pre-existing
    relative paths so agent-written files can be told apart afterwards."""
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    if condition == "baseline":
        for name, spec in BASELINE_TREES.items():
            src_root = sources[name]
            for rel in spec["files"]:
                dst = work / name / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_root / rel, dst)
            shutil.copy2((src_root / spec["readme"]).resolve(), work / name / "README.md")
        make_readonly_tree(work)
    if cfg.agent == "opencode":
        # Project-level config: merged over the user's global provider config.
        (work / CONDITION_FILE).write_text(SYSTEM_APPEND[condition] + "\n")
        (work / "opencode.json").write_text(json.dumps(opencode_config(condition, cfg), indent=2))
    elif cfg.agent == "codex":
        # Codex reads AGENTS.md from the working root; that is the append channel.
        (work / "AGENTS.md").write_text(system_append(condition, cfg) + "\n")
    return {str(p.relative_to(work)) for p in work.rglob("*") if p.is_file()}


def system_append(condition: str, cfg: argparse.Namespace) -> str:
    if cfg.agent == "codex" and condition == "baseline":
        return SYSTEM_APPEND_CODEX_BASELINE
    return SYSTEM_APPEND[condition]


def opencode_config(condition: str, cfg: argparse.Namespace) -> dict:
    tools = {t: False for t in OPENCODE_TOOLS_OFF}
    tools.update({t: True for t in OPENCODE_TOOLS_ON})
    permission = {"edit": "allow", "bash": "deny", "webfetch": "deny",
                  "external_directory": "deny"}
    conf = {
        "$schema": "https://opencode.ai/config.json",
        "share": "disabled",
        "instructions": [CONDITION_FILE],
        "tools": dict(tools),
        "permission": permission,
        "agent": {"legd": {"mode": "primary", "description": "leg D benchmark agent",
                           "maxSteps": cfg.max_turns, "tools": dict(tools),
                           "permission": permission}},
    }
    if condition == "with-server":
        conf["mcp"] = {"exclurad": {
            "type": "local", "command": [str(cfg.server_bin)],
            "environment": {"EXCLURAD_WORK_DIR_ETA": str(cfg.eta_src),
                            "EXCLURAD_WORK_DIR_PIPLUS": str(cfg.pion_src)},
            "enabled": True, "timeout": 30000}}
        for t in OPENCODE_SERVER_TOOLS_OFF:
            conf["tools"][t] = False
            conf["agent"]["legd"]["tools"][t] = False
    return conf


def claude_args(condition: str, model: str, max_turns: int, mcp_config: Path,
                empty_mcp: Path) -> list[str]:
    args = [
        "claude", "-p",
        "--model", model,
        "--output-format", "stream-json", "--verbose",
        # --restricted: no code-running tools, file tools confined to the
        # working directory, user/project settings ignored, and (verified
        # 2026-09-08) the global ~/.claude/CLAUDE.md is not loaded.
        "--restricted",
        "--strict-mcp-config",
        "--tools", ",".join(BUILTIN_TOOLS),
        "--permission-mode", "dontAsk",
        "--max-turns", str(max_turns),
        "--no-session-persistence",
        "--append-system-prompt", SYSTEM_APPEND[condition],
    ]
    if condition == "with-server":
        args += ["--mcp-config", str(mcp_config),
                 "--allowedTools", ",".join(BUILTIN_TOOLS + ["mcp__exclurad__*"]),
                 "--disallowedTools", ",".join(SERVER_TOOLS_DISALLOWED)]
    else:
        args += ["--mcp-config", str(empty_mcp),
                 "--allowedTools", ",".join(BUILTIN_TOOLS)]
    return args


def opencode_args(model: str, work: Path) -> list[str]:
    # --pure: no external plugins (the user's budget gauge); the project
    # opencode.json in `work` carries tools, permissions, MCP, and the step cap.
    return ["opencode", "run", "--format", "json", "--pure", "--agent", "legd",
            "--model", model, "--dir", str(work)]


def codex_args(condition: str, model: str, max_turns: int, work: Path,
               cfg: argparse.Namespace, last_msg: Path) -> list[str]:
    args = ["codex", "exec", "--json", "--model", model, "--sandbox", "workspace-write",
            "--cd", str(work), "--skip-git-repo-check", "--ignore-user-config",
            "--ignore-rules", "-c", f"max_turns={max_turns}",
            "-c", "tools.web_search=false",
            "--output-last-message", str(last_msg)]
    if condition == "with-server":
        env = (f'{{EXCLURAD_WORK_DIR_ETA="{cfg.eta_src}", '
               f'EXCLURAD_WORK_DIR_PIPLUS="{cfg.pion_src}"}}')
        args += ["-c", f'mcp_servers.exclurad.command="{cfg.server_bin}"',
                 "-c", f"mcp_servers.exclurad.env={env}"]
    return args


def build_command(condition: str, model: str, work: Path, dest: Path,
                  cfg: argparse.Namespace) -> tuple[list[str], str]:
    """argv and how the prompt is delivered ('stdin' or 'argv')."""
    if cfg.agent == "claude":
        return claude_args(condition, model, cfg.max_turns, cfg.mcp_config, cfg.empty_mcp), "stdin"
    if cfg.agent == "opencode":
        return opencode_args(model, work), "argv"
    return codex_args(condition, model, cfg.max_turns, work, cfg, dest / "last_message.txt"), "stdin"


def _walk(obj, fn):
    """Call fn on every dict in a nested JSON structure."""
    if isinstance(obj, dict):
        fn(obj)
        for v in obj.values():
            _walk(v, fn)
    elif isinstance(obj, list):
        for v in obj:
            _walk(v, fn)


def parse_claude(lines: list[dict]) -> dict:
    init, result, last_rate_limit = None, None, None
    tool_names: dict[str, int] = {}
    for ev in lines:
        if ev.get("type") == "system" and ev.get("subtype") == "init":
            init = ev
        elif ev.get("type") == "result":
            result = ev
        elif ev.get("type") == "rate_limit_event":
            last_rate_limit = ev.get("rate_limit_info")
        elif ev.get("type") == "assistant":
            for blk in ev.get("message", {}).get("content", []):
                if isinstance(blk, dict) and blk.get("type") == "tool_use":
                    tool_names[blk["name"]] = tool_names.get(blk["name"], 0) + 1
    return {
        "init": None if init is None else {
            "tools": init.get("tools"), "mcp_servers": init.get("mcp_servers"),
            "model": init.get("model"), "permissionMode": init.get("permissionMode"),
            "claude_code_version": init.get("claude_code_version"),
            "session_id": init.get("session_id")},
        "result": None if result is None else {
            k: result.get(k) for k in (
                "subtype", "is_error", "num_turns", "duration_ms", "duration_api_ms",
                "total_cost_usd", "usage", "modelUsage", "stop_reason",
                "terminal_reason", "permission_denials", "session_id")},
        "final_text": None if result is None else result.get("result"),
        "tool_calls": tool_names, "last_rate_limit": last_rate_limit,
    }


def parse_opencode(lines: list[dict], dest: Path, rc: int, env: dict) -> dict:
    """OpenCode's --format json stream is a sequence of events whose exact
    shapes vary by version; harvest tolerantly, then ask `opencode export`
    for the authoritative cost/token/time record of the session."""
    session_id = None
    tool_names: dict[str, int] = {}
    texts: list[str] = []
    errors: list[str] = []

    def visit(d: dict):
        nonlocal session_id
        sid = d.get("sessionID") or d.get("session_id")
        if session_id is None and isinstance(sid, str) and sid.startswith("ses_"):
            session_id = sid
        if session_id is None and isinstance(d.get("id"), str) and d["id"].startswith("ses_") \
                and "directory" in d:
            session_id = d["id"]
        if d.get("type") == "tool" and isinstance(d.get("tool"), str):
            key = (d.get("callID") or d.get("id"), d["tool"])
            if key not in seen_calls:
                seen_calls.add(key)
                tool_names[d["tool"]] = tool_names.get(d["tool"], 0) + 1
        if d.get("type") == "text" and isinstance(d.get("text"), str):
            texts.append(d["text"])
        if d.get("type") == "session.error" or "error" in d and isinstance(d.get("error"), dict):
            errors.append(json.dumps(d.get("error") or d)[:500])

    seen_calls: set = set()
    for ev in lines:
        _walk(ev, visit)

    export = None
    if session_id:
        try:
            out = subprocess.run(["opencode", "export", session_id], capture_output=True,
                                 text=True, timeout=120, env=env)
            if out.returncode == 0 and out.stdout.strip():
                export = json.loads(out.stdout[out.stdout.index("{"):])
                (dest / "session_export.json").write_text(json.dumps(export, indent=2))
        except Exception as exc:  # noqa: BLE001
            errors.append(f"export failed: {exc}")
    info = (export or {}).get("info") or {}
    tokens = info.get("tokens") or {}
    cache = tokens.get("cache") or {}
    n_assistant = sum(1 for m in (export or {}).get("messages", [])
                      if (m.get("info") or m).get("role") == "assistant")
    t = info.get("time") or {}
    duration_ms = (t.get("updated", 0) - t.get("created", 0)) if t else None
    ok = rc == 0 and export is not None
    return {
        "init": {"session_id": session_id, "model": info.get("model"),
                 "agent": info.get("agent"), "opencode_version": info.get("version")},
        "result": {
            "subtype": "success" if ok else "error_during_execution",
            "is_error": not ok, "num_turns": n_assistant or None,
            "duration_ms": duration_ms, "total_cost_usd": info.get("cost"),
            "usage": {"input_tokens": tokens.get("input"), "output_tokens": tokens.get("output"),
                      "reasoning_tokens": tokens.get("reasoning"),
                      "cache_read_input_tokens": cache.get("read"),
                      "cache_creation_input_tokens": cache.get("write")},
            "session_id": session_id, "errors": errors[:5]},
        "final_text": texts[-1] if texts else None,
        "tool_calls": tool_names, "last_rate_limit": None,
    }


def parse_codex(lines: list[dict], dest: Path, rc: int) -> dict:
    """Codex --json JSONL: harvest tool calls, the last token_count event,
    and the final message written by --output-last-message."""
    tool_names: dict[str, int] = {}
    usage, rate, thread_id, errors = None, None, None, []

    def visit(d: dict):
        nonlocal usage, rate, thread_id
        if d.get("type") == "token_count" or "total_token_usage" in d:
            info = d.get("info") or d
            if "total_token_usage" in info:
                usage = info["total_token_usage"]
            if d.get("rate_limits"):
                rate = d["rate_limits"]
        if isinstance(d.get("thread_id"), str) and thread_id is None:
            thread_id = d["thread_id"]
        t = d.get("type", "")
        if t in ("function_call", "mcp_tool_call", "custom_tool_call", "local_shell_call") \
                or t.endswith("tool_call"):
            name = d.get("name") or d.get("tool") or t
            tool_names[name] = tool_names.get(name, 0) + 1
        if t == "error" or (isinstance(d.get("error"), dict)):
            errors.append(json.dumps(d)[:500])

    for ev in lines:
        _walk(ev, visit)
    last = dest / "last_message.txt"
    final_text = last.read_text() if last.exists() else None
    ok = rc == 0
    return {
        "init": {"session_id": thread_id, "harness_notes": CODEX_NOTES},
        "result": {
            "subtype": "success" if ok else "error_during_execution", "is_error": not ok,
            "num_turns": None, "duration_ms": None, "total_cost_usd": None,
            "usage": None if usage is None else {
                "input_tokens": usage.get("input_tokens"),
                "output_tokens": usage.get("output_tokens"),
                "reasoning_tokens": usage.get("reasoning_output_tokens"),
                "cache_read_input_tokens": usage.get("cached_input_tokens"),
                "cache_creation_input_tokens": usage.get("cache_write_input_tokens")},
            "session_id": thread_id, "errors": errors[:5]},
        "final_text": final_text, "tool_calls": tool_names,
        "last_rate_limit": rate,
    }


NOT_RETRYABLE_SUBTYPES = {"success", "error_max_turns", "error_max_budget_usd"}


class Throttle:
    """Shared pause: when one conversation is rejected for rate limiting, every
    worker waits until the reported reset time before starting another."""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.paused_until = 0.0

    def wait(self) -> None:
        while True:
            with self.lock:
                delay = self.paused_until - time.time()
            if delay <= 0:
                return
            time.sleep(min(delay, 30))

    def pause_until(self, when: float) -> None:
        with self.lock:
            self.paused_until = max(self.paused_until, when)


THROTTLE = Throttle()


def classify(summary: dict, last_rate_limit: dict | None) -> tuple[bool, float | None]:
    """(retryable, resume_at). Rate-limit rejections and API-side errors are
    retryable; max-turns, timeouts, and ordinary completions are outcomes."""
    if summary["timed_out"]:
        return False, None
    res = summary["result"]
    if res is None:  # process died before emitting a result event
        return True, None
    if res.get("subtype") in NOT_RETRYABLE_SUBTYPES and not res.get("is_error"):
        return False, None
    if res.get("subtype") in NOT_RETRYABLE_SUBTYPES:
        return False, None
    resume_at = None
    if last_rate_limit and last_rate_limit.get("status") == "rejected":
        resume_at = float(last_rate_limit.get("resetsAt") or 0) or None
    return True, resume_at


def run_one(job: dict, cfg: argparse.Namespace, lock: threading.Lock) -> dict:
    model, condition, rep, task = job["model"], job["condition"], job["rep"], job["task"]
    tag = f"{model}/{condition}/rep{rep}/{task['id']}"
    dest = cfg.out / model / condition / f"rep{rep}" / task["id"]
    if cfg.resume and (dest / "result.json").exists():
        return {"tag": tag, "skipped": True}
    for attempt in range(1, cfg.max_attempts + 1):
        THROTTLE.wait()
        out = run_attempt(job, cfg, lock, attempt)
        if cfg.dry_run:
            return out
        retry, resume_at = classify(out["summary"], out["last_rate_limit"])
        if not retry:
            return out
        if attempt < cfg.max_attempts:
            when = resume_at or (time.time() + 120 * attempt)
            THROTTLE.pause_until(when + 5)
            with lock:
                print(f"  {tag}: attempt {attempt} not scoreable "
                      f"({(out['summary']['result'] or {}).get('subtype')}); "
                      f"paused until {dt.datetime.fromtimestamp(when).strftime('%H:%M:%S')}",
                      flush=True)
    return out


def run_attempt(job: dict, cfg: argparse.Namespace, lock: threading.Lock, attempt: int) -> dict:
    model, condition, rep, task = job["model"], job["condition"], job["rep"], job["task"]
    tag = f"{model}/{condition}/rep{rep}/{task['id']}"
    work = cfg.work_root / model / condition / f"rep{rep}" / task["id"]
    dest = cfg.out / model / condition / f"rep{rep}" / task["id"]
    if attempt > 1 and dest.exists():
        # keep the failed attempt's transcript for the record, then start clean
        keep = dest.parent / f"{task['id']}.attempt{attempt - 1}"
        shutil.rmtree(keep, ignore_errors=True)
        dest.rename(keep)

    pre = prepare_workdir(work, condition, {"eta": cfg.eta_src, "pion": cfg.pion_src}, cfg)
    prompt = PROMPT_TEMPLATE.format(request=task["request"])
    dest.mkdir(parents=True, exist_ok=True)
    args, delivery = build_command(condition, model, work, dest, cfg)
    (dest / "prompt.txt").write_text(prompt)
    (dest / "conversation.json").write_text(json.dumps({
        "harness": cfg.agent, "argv": args + (["<prompt>"] if delivery == "argv" else []),
        "stdin": "prompt.txt" if delivery == "stdin" else None, "prompt": prompt,
        "cwd": str(work), "system_append": system_append(condition, cfg),
    }, indent=2))
    if cfg.dry_run:
        summary = {"model": model, "condition": condition, "rep": rep, "task_id": task["id"],
                   "class": task["class"], "dry_run": True, "timed_out": False, "result": None,
                   "outcome_json_present": False, "wall_seconds": 0}
        (dest / "result.json").write_text(json.dumps(summary, indent=2))
        with lock:
            print(f"  {tag:60s} DRY-RUN  {' '.join(args)}" + (" <prompt>" if delivery == "argv" else " < prompt.txt"),
                  flush=True)
        return {"tag": tag, "summary": summary, "last_rate_limit": None}
    started = dt.datetime.now(dt.timezone.utc)
    t0 = time.monotonic()
    timed_out = False
    env = clean_env()
    with open(dest / "prompt.txt") as inp, open(dest / "transcript.jsonl", "w") as out, \
            open(dest / "stderr.txt", "w") as err:
        # claude/codex: the prompt goes over stdin (claude's variadic
        # --allowedTools/--tools flags would swallow a trailing positional).
        # opencode: positional message, stdin closed.
        proc = subprocess.Popen(args + ([prompt] if delivery == "argv" else []),
                                cwd=work, env=env,
                                stdin=inp if delivery == "stdin" else subprocess.DEVNULL,
                                stdout=out, stderr=err, start_new_session=True)
        try:
            rc = proc.wait(timeout=cfg.timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            try:
                os.killpg(proc.pid, 15)
                rc = proc.wait(timeout=15)
            except Exception:  # noqa: BLE001
                os.killpg(proc.pid, 9)
                rc = proc.wait()
    wall = time.monotonic() - t0

    # Parse the stream into the common result contract.
    lines = []
    for line in (dest / "transcript.jsonl").read_text().splitlines():
        try:
            lines.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    if cfg.agent == "claude":
        parsed = parse_claude(lines)
    elif cfg.agent == "opencode":
        parsed = parse_opencode(lines, dest, rc, env)
    else:
        parsed = parse_codex(lines, dest, rc)
    init, result = parsed["init"], parsed["result"]
    last_rate_limit, tool_names = parsed["last_rate_limit"], parsed["tool_calls"]
    n_tool_calls = sum(tool_names.values())

    # Copy what the agent wrote (and nothing that was there before).
    written = []
    for p in work.rglob("*"):
        if not p.is_file():
            continue
        rel = str(p.relative_to(work))
        if rel in pre:
            continue
        (dest / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, dest / rel)
        written.append(rel)

    summary = {
        "model": model, "condition": condition, "rep": rep, "task_id": task["id"],
        "class": task["class"], "harness": cfg.agent,
        "started_utc": started.isoformat(), "attempt": attempt,
        "last_rate_limit": last_rate_limit,
        "wall_seconds": round(wall, 1), "exit_code": rc, "timed_out": timed_out,
        "work_dir": str(work), "files_written": sorted(written),
        "outcome_json_present": (dest / "outcome.json").exists()
                                or bool(list(dest.glob("*/outcome.json"))),
        "n_tool_calls": n_tool_calls, "tool_calls": tool_names,
        "init": init, "result": result, "final_text": parsed["final_text"],
    }
    if result is not None and result.get("duration_ms") is None:
        result["duration_ms"] = int(wall * 1000)
    (dest / "result.json").write_text(json.dumps(summary, indent=2))
    with lock:
        cost = summary["result"]["total_cost_usd"] if result else None
        turns = summary["result"]["num_turns"] if result else None
        flag = "TIMEOUT" if timed_out else ("ok" if summary["outcome_json_present"] else "NO-OUTCOME")
        print(f"  {tag:60s} {wall:6.0f}s  turns={turns!s:>3}  cost=${cost or 0:.3f}  {flag}",
              flush=True)
    return {"tag": tag, "summary": summary, "last_rate_limit": last_rate_limit}


def score_dir(run_dir: Path, python: str) -> dict:
    env = dict(os.environ, PYTHONPATH=str(REPO / "src"))
    subprocess.run([python, str(SCORER), "--suite", str(SUITE), "--run-dir", str(run_dir),
                    "--json", str(run_dir / "scores.json")],
                   env=env, capture_output=True, text=True)
    return json.loads((run_dir / "scores.json").read_text())


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--agent", choices=AGENTS, default="claude",
                    help="harness that drives the conversation (default: Claude Code)")
    ap.add_argument("--models", nargs="+", default=MODELS,
                    help="model ids as the harness expects them (opencode: provider/model)")
    ap.add_argument("--dry-run", action="store_true",
                    help="prepare working dirs and configs, print argv, run nothing")
    ap.add_argument("--conditions", nargs="+", default=CONDITIONS, choices=CONDITIONS)
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--tasks", nargs="+", help="subset of task ids")
    ap.add_argument("--pilot", action="store_true",
                    help="sonnet only, both conditions, k=1 (30 conversations)")
    ap.add_argument("--out", type=Path,
                    help="results dir (default benchmarks/<today>-agent-accuracy)")
    ap.add_argument("--work-root", type=Path,
                    default=Path.home() / ".cache" / "exclurad-mcp-leg-d",
                    help="where fresh per-conversation working dirs are created "
                         "(must be outside any git repo)")
    ap.add_argument("--eta-src", type=Path,
                    default=Path(os.environ.get("EXCLURAD_WORK_DIR_ETA",
                                                "~/Documents/GitHub/exclurad/exclurad")).expanduser(),
                    help="η fork checkout: source for the baseline copy and the server's eta work dir")
    ap.add_argument("--pion-src", type=Path,
                    default=Path(os.environ.get("EXCLURAD_WORK_DIR_PIPLUS",
                                                "~/Documents/GitHub/JeffersonLab-exclurad/exclurad")).expanduser(),
                    help="π⁺ upstream checkout: source for the baseline copy and the server's pion work dir")
    ap.add_argument("--server-bin", default=shutil.which("exclurad-mcp") or "exclurad-mcp",
                    help="absolute path to exclurad-mcp (Claude Code spawns it outside conda)")
    ap.add_argument("--max-turns", type=int, default=25)
    ap.add_argument("--timeout", type=int, default=900, help="wall-clock seconds per conversation")
    ap.add_argument("--parallel", type=int, default=4)
    ap.add_argument("--max-attempts", type=int, default=3,
                    help="reruns of a conversation that ended in a rate-limit or API error")
    ap.add_argument("--resume", action="store_true",
                    help="fill in missing conversations of an existing --out dir")
    ap.add_argument("--label", default="agent-accuracy")
    cfg = ap.parse_args()

    if cfg.pilot:
        cfg.models, cfg.reps = ["claude-sonnet-5"], 1
        cfg.label = "agent-accuracy-pilot"
    today = dt.date.today().isoformat()
    if cfg.agent != "claude":
        cfg.label = f"{cfg.label}-{cfg.agent}"
    cfg.out = cfg.out or (REPO / "benchmarks" / f"{today}-{cfg.label}")
    if cfg.out.exists() and not cfg.resume:
        sys.exit(f"{cfg.out} exists; runs are never overwritten (use --resume to fill gaps "
                 "or pick a new --out)")
    cfg.out.mkdir(parents=True, exist_ok=True)
    cfg.work_root = cfg.work_root / cfg.out.name
    cfg.work_root.mkdir(parents=True, exist_ok=True)
    try:
        sh(["git", "-C", str(cfg.work_root), "rev-parse", "--show-toplevel"])
        sys.exit(f"--work-root {cfg.work_root} is inside a git repository; pick another")
    except subprocess.CalledProcessError:
        pass
    for name, src in (("η", cfg.eta_src), ("π⁺", cfg.pion_src)):
        if not (src / "exclurad.F").exists():
            sys.exit(f"{name} source not found at {src}")

    suite = json.loads(SUITE.read_text())
    tasks = [t for t in suite["tasks"] if not cfg.tasks or t["id"] in cfg.tasks]

    # MCP configs live in the results dir so the exact registration is on record.
    cfg.mcp_config = cfg.out / "mcp-with-server.json"
    cfg.empty_mcp = cfg.out / "mcp-empty.json"
    cfg.mcp_config.write_text(json.dumps({"mcpServers": {"exclurad": {
        "command": str(cfg.server_bin), "args": [],
        "env": {"EXCLURAD_WORK_DIR_ETA": str(cfg.eta_src),
                "EXCLURAD_WORK_DIR_PIPLUS": str(cfg.pion_src)}}}}, indent=2))
    cfg.empty_mcp.write_text(json.dumps({"mcpServers": {}}, indent=2))

    harness_version = {"claude": ["claude", "--version"], "opencode": ["opencode", "--version"],
                       "codex": ["codex", "--version"]}[cfg.agent]
    try:
        hv = sh(harness_version)
    except Exception as exc:  # noqa: BLE001
        hv = f"unavailable ({exc})"
        if not cfg.dry_run:
            sys.exit(f"{cfg.agent} not runnable here: {exc}")
    prov = {
        "date": today, "started_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "harness": cfg.agent, "harness_version": hv, "dry_run": cfg.dry_run,
        "harness_notes": CODEX_NOTES if cfg.agent == "codex" else None,
        "suite": str(SUITE.relative_to(REPO)), "suite_version": suite["suite_version"],
        "suite_sha256": hashlib.sha256(SUITE.read_bytes()).hexdigest(),
        "models": cfg.models, "conditions": cfg.conditions, "reps": cfg.reps,
        "tasks": [t["id"] for t in tasks],
        "exclurad_mcp": git_info(REPO),
        "eta_checkout": {"path": str(cfg.eta_src), **git_info(cfg.eta_src)},
        "pion_checkout": {"path": str(cfg.pion_src), **git_info(cfg.pion_src)},
        "server_bin": str(cfg.server_bin),
        "machine": {"platform": platform.platform(), "machine": platform.machine(),
                    "python": platform.python_version()},
        "max_turns": cfg.max_turns, "timeout_seconds": cfg.timeout, "parallel": cfg.parallel,
        "max_attempts": cfg.max_attempts,
        "tool_policy": {
            "claude": {"permission_mode": "dontAsk", "strict_mcp_config": True,
                       "restricted": True, "builtin_tools": BUILTIN_TOOLS,
                       "with_server_allowed": BUILTIN_TOOLS + ["mcp__exclurad__*"],
                       "with_server_disallowed": SERVER_TOOLS_DISALLOWED},
            "opencode": {"tools_on": OPENCODE_TOOLS_ON, "tools_off": OPENCODE_TOOLS_OFF,
                         "server_tools_off": OPENCODE_SERVER_TOOLS_OFF,
                         "permission": {"edit": "allow", "bash": "deny", "webfetch": "deny",
                                        "external_directory": "deny"},
                         "agent": "legd", "pure": True, "share": "disabled"},
            "codex": {"sandbox": "workspace-write", "ignore_user_config": True,
                      "web_search": False, "notes": CODEX_NOTES},
        }[cfg.agent],
        "baseline_trees": {k: v["files"] + ["README.md (repository top-level)"]
                           for k, v in BASELINE_TREES.items()},
        "prompt_template": PROMPT_TEMPLATE, "system_append": SYSTEM_APPEND,
        "work_root": str(cfg.work_root),
        "known_leaks": {
            "claude": ["The CLI places the account email address and today's date in "
                       "the model's context. With --restricted the global "
                       "~/.claude/CLAUDE.md does NOT load (verified with a probe "
                       "conversation on 2026-09-08). Nothing in context mentions "
                       "EXCLURAD or physics."],
            "opencode": ["The user's global ~/.config/opencode config (providers) is "
                         "merged under the per-conversation opencode.json; --pure skips "
                         "plugins. Whether a global AGENTS.md/instructions file loads is "
                         "to be verified with a probe conversation on the run machine."],
            "codex": ["The user's config.toml is ignored (--ignore-user-config); the "
                      "model's own default instructions and the sandboxed shell remain."],
        }[cfg.agent],
    }
    prov_path = cfg.out / "provenance.json"
    if prov_path.exists() and cfg.resume:
        old = json.loads(prov_path.read_text())
        old.setdefault("resumed_utc", []).append(prov["started_utc"])
        prov = old
    prov_path.write_text(json.dumps(prov, indent=2))

    jobs = [{"model": m, "condition": c, "rep": r, "task": t}
            for m in cfg.models for c in cfg.conditions
            for r in range(1, cfg.reps + 1) for t in tasks]
    print(f"{len(jobs)} conversations -> {cfg.out}  (parallel={cfg.parallel})", flush=True)
    lock = threading.Lock()
    t0 = time.monotonic()
    with ThreadPoolExecutor(max_workers=cfg.parallel) as ex:
        futs = [ex.submit(run_one, j, cfg, lock) for j in jobs]
        for f in as_completed(futs):
            f.result()
    print(f"all conversations done in {(time.monotonic() - t0) / 60:.1f} min", flush=True)
    if cfg.dry_run:
        print("dry run: nothing executed; inspect the work dirs and conversation.json files")
        return

    # Score every (model, condition, rep) directory that has all its tasks.
    total_cost = 0.0
    for m in cfg.models:
        for c in cfg.conditions:
            for r in range(1, cfg.reps + 1):
                d = cfg.out / m / c / f"rep{r}"
                if not d.exists():
                    continue
                s = score_dir(d, sys.executable)
                cost = 0.0
                for t in tasks:
                    rj = d / t["id"] / "result.json"
                    if rj.exists():
                        res = json.loads(rj.read_text()).get("result") or {}
                        cost += res.get("total_cost_usd") or 0.0
                total_cost += cost
                print(f"{m:28s} {c:12s} rep{r}: {s['passed']}/{s['n_tasks']}  "
                      f"{s['by_class']}  ${cost:.2f}", flush=True)
    print(f"total list-price cost: ${total_cost:.2f}")
    print(f"next: python3 benchmarks/report_leg_d.py {cfg.out}")


if __name__ == "__main__":
    main()
