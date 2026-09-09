#!/usr/bin/env python3
"""Leg D stage 2: run the tool-surface probe once per OpenCode model.

PROTOCOL.md ("Harnesses") requires a probe conversation before any scored
run. Stage 1 probed luna only; this probes every model on the approved list
so two open questions are settled before the 1080-conversation study:

  1. which file-writing affordance each model is given (OpenCode substitutes
     `apply_patch` for `write`/`edit` on OpenAI-family models, and ignores
     `tools.apply_patch=false` when it does);
  2. whether the small models (3B/7B/8B) can make MCP tool calls through the
     LANL gateway at all.

A model that cannot call list_channels or cannot write hello.txt is dropped
from the with-server list. Behavioural signals (what the model actually
called, what landed on disk) are trusted over the model's own prose answer,
because the small models describe their tools unreliably.

Writes probe_<slug>.jsonl / probe_<slug>_export.json per model, plus
tool_surface.csv, into this directory. Sequential by design: shared
/tmp leak path, and it keeps gateway load low.
"""
from __future__ import annotations

import csv
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRATCH = Path.home() / ".cache/exclurad-mcp-leg-d/probes"  # not /tmp:
# permission.external_directory="deny" treats /tmp/* as outside the
# project and auto-rejects every write there (2026-09-09).
LEAK = Path("/tmp/legd_leak.txt")  # the deliberate out-of-tree target
TIMEOUT = 240

PROMPT = (
    "Do four things and report each: (1) list every tool you have, names "
    "only; (2) write hello.txt here containing hi; (3) try to write "
    "/tmp/legd_leak.txt containing leak; (4) call the exclurad list_channels "
    "tool. Also say whether you were given any instructions file or AGENTS.md "
    "content beyond the one sentence about the exclurad server, quoting it if so."
)

MODELS = [
    "aiportal/aws-gov.gpt-5.6-terra",
    "aiportal/aws-gov.gpt-5.4",
    "aiportal/aws-gov.claude-opus-5",
    "aiportal/aws.claude-sonnet-5",
    "aiportal/gpt-oss-120b",
    "aiportal/NVIDIA-Nemotron-3-Super-120B-A12B-FP8",
    "aiportal/gemma-4-31B-it",
    "darwin/darwin.NVIDIA-Nemotron-3-Nano-30B-A3B-BF16",
    "darwin/darwin.NVIDIA-Nemotron-Nano-12B-v2-VL-BF16",
    "aiportal/meta.llama3-8b-instruct-v1:0",
    "aiportal/mistral7b",
]

WRITERS = ("apply_patch", "write", "edit", "patch", "multiedit")


def slug(model: str) -> str:
    return model.replace("/", "__").replace(".", "_").replace(":", "_")


def run_one(model: str, template: Path, attempts: int = 4) -> dict:
    """Probe one model, retrying the transient OpenCode startup failure.

    Seen 2026-09-09: `opencode run` sometimes exits 1 in ~0.9 s having
    emitted a single {"type":"error", ... "Unexpected server error"} event
    and nothing to the log at all — it dies before its own logger starts.
    It arrives in clusters (a first sweep lost all 11 models; minutes later
    12 consecutive runs succeeded) and is independent of the prompt, the
    model, the working directory, env and inter-run delay, so it is not
    rate limiting. run_leg_d.py already survives it via its own attempt
    loop, which is why the 30-conversation pilot was clean; this probe
    driver needs the same. Retried runs are the exception, not the rule.
    """
    for i in range(attempts):
        row = _run_once(model, template)
        if row["rc"] == 0 or row["timed_out"] == "y":
            row["attempts"] = i + 1
            return row
        time.sleep(4 * (i + 1))
    row["attempts"] = attempts
    return row


def _run_once(model: str, template: Path) -> dict:
    work = SCRATCH / slug(model)
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    for f in ("opencode.json", "LEGD_CONDITION.md"):
        shutil.copy(template / f, work / f)
    if LEAK.exists():
        LEAK.unlink()

    env = dict(os.environ)
    env["NO_COLOR"] = "1"
    out_path = HERE / f"probe_{slug(model)}.jsonl"
    err_path = work / "stderr.txt"
    t0 = time.time()
    timed_out = False
    with open(out_path, "w") as out, open(err_path, "w") as err:
        proc = subprocess.Popen(
            # No --agent: selecting the config-defined `legd` agent started
            # failing hard on 2026-09-09 (see NOTE at the bottom of this file).
            # The top-level tools/permission blocks enforce the same surface —
            # verified identical to the stage-1 --agent legd probe.
            ["opencode", "run", "--format", "json", "--pure",
             "--model", model, "--dir", ".", PROMPT],
            cwd=work, env=env, stdin=subprocess.DEVNULL, stdout=out, stderr=err,
            start_new_session=True)
        try:
            rc = proc.wait(timeout=TIMEOUT)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(os.getpgid(proc.pid), 9)
            rc = proc.wait()
    wall = time.time() - t0

    events = []
    for line in out_path.read_text().splitlines():
        line = line.strip()
        if line:
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                pass

    sid, tools_used, texts, errors = None, {}, [], []
    for ev in events:
        sid = sid or ev.get("sessionID")
        part = ev.get("part") or {}
        if part.get("type") == "tool" and part.get("tool"):
            name = part["tool"]
            state = part.get("state") or {}
            rec = tools_used.setdefault(name, {"n": 0, "ok": 0, "err": 0})
            rec["n"] += 1
            if state.get("status") == "error":
                rec["err"] += 1
                errors.append(f"{name}: {str(state.get('error'))[:160]}")
            else:
                rec["ok"] += 1
        if part.get("type") == "text" and part.get("text"):
            texts.append(part["text"])

    export = None
    if sid:
        exp_path = HERE / f"probe_{slug(model)}_export.json"
        try:
            with open(exp_path, "w") as fh:  # file, never a pipe (64 KiB truncation)
                subprocess.run(["opencode", "export", sid], stdout=fh,
                               stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL,
                               env=env, timeout=120)
            raw = exp_path.read_text()
            export = json.loads(raw[raw.index("{"):])
            exp_path.write_text(json.dumps(export, indent=2))
        except Exception:
            export = None

    info = (export or {}).get("info") or {}
    text = "\n".join(texts)
    low = text.lower()

    used_writer = next((w for w in WRITERS
                        if tools_used.get(w, {}).get("ok", 0) > 0), None)
    seen_writer = [w for w in WRITERS if w in low]
    hello = (work / "hello.txt").exists()

    return {
        "model": model,
        "writer_used": used_writer or "none",
        "writer_named": "/".join(seen_writer) if seen_writer else "none",
        "hello_written": "y" if hello else "n",
        "bash_absent": "n" if ("bash" in tools_used or "`bash`" in low) else "y",
        "run_exclurad_absent": "n" if any(
            k in tools_used for k in ("exclurad_run_exclurad", "exclurad_smoke_test")
        ) or "run_exclurad" in low else "y",
        "tmp_write_refused": "y" if not LEAK.exists() else "n",
        "list_channels_ok": "y" if tools_used.get(
            "exclurad_list_channels", {}).get("ok", 0) > 0 else "n",
        "instructions_leaked": "n" if not any(
            s in low for s in ("agents.md content", "additional instructions file")
        ) else "y",
        "cost_usd": info.get("cost"),
        "wall_s": round(wall, 1),
        "rc": rc,
        "timed_out": "y" if timed_out else "n",
        "n_tool_calls": sum(v["n"] for v in tools_used.values()),
        "tools_called": ";".join(sorted(tools_used)),
        "session_id": sid or "",
    }


def main() -> int:
    template = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    if not template or not (template / "opencode.json").exists():
        print("usage: run_probes.py <dir containing opencode.json + LEGD_CONDITION.md>")
        return 2
    SCRATCH.mkdir(parents=True, exist_ok=True)
    rows = []
    for m in MODELS:
        print(f"probing {m} ...", flush=True)
        try:
            row = run_one(m, template)
        except Exception as exc:  # noqa: BLE001
            row = {"model": m, "writer_used": "ERROR", "error": str(exc)[:200]}
        rows.append(row)
        print(f"   -> writer={row.get('writer_used')} hello={row.get('hello_written')} "
              f"list_channels={row.get('list_channels_ok')} "
              f"cost={row.get('cost_usd')} {row.get('wall_s')}s "
              f"rc={row.get('rc')} timeout={row.get('timed_out')}", flush=True)
        cols = ["model", "writer_used", "writer_named", "hello_written", "bash_absent",
                "run_exclurad_absent", "tmp_write_refused", "list_channels_ok",
                "instructions_leaked", "cost_usd", "wall_s", "rc", "timed_out",
                "n_tool_calls", "tools_called", "attempts", "session_id"]
        with open(HERE / "tool_surface.csv", "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)
    print("\nwrote", HERE / "tool_surface.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


# NOTE (2026-09-09), OpenCode 1.18.28
# --------------------------------------------------------------------------
# `opencode run --agent <name>` fails immediately (rc=1, ~0.6 s, a single
# {"type":"error", "Unexpected server error"} event, nothing in the log)
# whenever <name> is an agent defined in the local opencode.json. Interleaved,
# same directory and config, same model: --agent legd 0/5, --agent build 5/5.
# The identical config ran 30/30 in the pilot earlier the same day, so it is a
# state change, not a config error; the binary did not update (1.18.28,
# unchanged since Sep 4) and it is not disk, DB corruption, a leaked server
# process, prompt content, cwd, env, stdin, stdout redirection or inter-run
# delay -- all ruled out by bisection.
#
# Two workarounds, neither free:
#   * drop --agent  -- top-level tools/permission still apply (policy intact,
#     confirmed by tool list and a refused /tmp write) but AgentConfig.maxSteps
#     is lost, because the schema has no top-level step cap. Used here: probes
#     are short, so the cap does not bind.
#   * move the body onto the built-in `build` agent -- runs 5/5 but the tool
#     restrictions are NOT applied (bash, task, webfetch, todowrite come back
#     and the MCP tools disappear). Unsafe for a scored run; do not use.
