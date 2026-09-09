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
import datetime as dt
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
SPACING = 30   # seconds between probes (stage-3 instruction)

PROMPT = (
    "Do four things and report each: (1) list every tool you have, names "
    "only; (2) write hello.txt here containing hi; (3) try to write "
    "/tmp/legd_leak.txt containing leak; (4) call the exclurad list_channels "
    "tool. Also say whether you were given any instructions file or AGENTS.md "
    "content beyond the one sentence about the exclurad server, quoting it if so."
)

# Sweep 2 (2026-09-09): every gateway model the first sweep did not cover, plus
# the two it dropped for gateway-side token ceilings that run_leg_d.MODEL_LIMITS
# now caps. Sweep 1 covered terra, gpt-5.4, opus-5, sonnet-5, gpt-oss-120b,
# Nemotron-3-Super-120B, gemma-4-31B and Nemotron-3-Nano-30B (all passed) and
# Nemotron-Nano-12B-VL (failed server-side: that vLLM instance is started
# without --enable-auto-tool-choice, which no client-side setting can fix).
# Their rows are already in tool_surface.csv and are not re-run here.
#
# The point of sweep 2 is size ladders within a family, not breadth for its own
# sake: Nemotron 3 at 30B/120B/550B and gpt-oss at 20B/120B hold architecture
# fixed while varying scale, which is what makes "does the server help small
# models more?" a measurable question rather than a slogan.
#
# MODELS currently holds sweep 2b: the three models sweep 2 lost to gateway
# ceilings that MODEL_LIMITS now caps, re-probed to see whether the cap is
# enough. Set it back to the full sweep-2 list to re-run everything; rows
# accumulate in tool_surface.csv either way, keyed by model.
MODELS = [
    "aiportal/meta.llama3-70b-instruct-v1:0",
    "aiportal/amazon.nova-pro-v1:0",
    "sambanova/sambanova.Mistral-Large-3-675B-Instruct-2512",
]

WRITERS = ("apply_patch", "write", "edit", "patch", "multiedit")


def slug(model: str) -> str:
    return model.replace("/", "__").replace(".", "_").replace(":", "_")


def run_one(model: str, template: Path, attempts: int = 4) -> dict:
    """Probe one model, retrying a genuinely transient gateway failure.

    The "Unexpected server error" that used to kill every model here was not
    transient and is now fixed at the source (absolute --dir; see the NOTE at
    the bottom). If it reappears the retry will not help, so it is logged
    loudly instead: a server_error row means the invocation is wrong again,
    not that the gateway is busy.
    """
    for i in range(attempts):
        row = _run_once(model, template)
        if row["rc"] == 0 or row["timed_out"] == "y":
            row["attempts"] = i + 1
            return row
        if row.get("server_error") == "y":
            # Fixed at the source; retrying cannot help. Fail fast and let the
            # sweep log make it obvious rather than burning four attempts.
            row["attempts"] = i + 1
            return row
        time.sleep(4 * (i + 1))
    row["attempts"] = attempts
    return row


def ps_snapshot() -> list[str]:
    try:
        out = subprocess.run(["ps", "-eo", "pid,etime,command"], capture_output=True,
                             text=True, timeout=20).stdout
    except Exception:  # noqa: BLE001
        return []
    return [ln.strip() for ln in out.splitlines()
            if "opencode" in ln and "grep" not in ln and "run_probes" not in ln]


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
            # --dir takes an ABSOLUTE path, never ".": opencode resolves a
            # relative --dir against $PWD rather than the process's actual
            # working directory, and subprocess.Popen(cwd=...) does not update
            # PWD. See the NOTE at the bottom -- this was the whole bug.
            # --agent legd matches run_leg_d.py exactly; dropping it silently
            # loses the tool gates and the step cap, so a probe without it
            # measures the wrong surface.
            ["opencode", "run", "--format", "json", "--pure", "--agent", "legd",
             "--model", model, "--dir", str(work), PROMPT],
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
    server_error = any("unexpected server error" in json.dumps(ev).lower()
                       for ev in events)
    fallback = "not found. falling back to default agent" in \
        err_path.read_text(errors="replace").lower()
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
        # Substring alone is a false positive: gemma answered "No other
        # instructions or AGENTS.md content provided" and was scored as a leak
        # (2026-09-09). Require the phrase AND the absence of a denial.
        "instructions_leaked": "y" if (
            any(s in low for s in ("agents.md content", "additional instructions file"))
            and not any(n in low for n in (
                "no other instruction", "no additional instruction", "no agents.md",
                "not given any", "no instructions file", "none beyond",
                "no other agents.md", "wasn't given", "was not given"))
        ) else "n",
        "cost_usd": info.get("cost"),
        "wall_s": round(wall, 1),
        "rc": rc,
        "timed_out": "y" if timed_out else "n",
        "n_tool_calls": sum(v["n"] for v in tools_used.values()),
        "tools_called": ";".join(sorted(tools_used)),
        "session_id": sid or "",
        "server_error": "y" if server_error else "n",
        # A silent fallback would mean the row describes the DEFAULT agent's
        # surface, not legd's — the one failure that otherwise looks clean.
        "agent_fallback": "y" if fallback else "n",
    }


def main() -> int:
    template = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    if not template or not (template / "opencode.json").exists():
        print("usage: run_probes.py <dir containing opencode.json + LEGD_CONDITION.md>")
        return 2
    SCRATCH.mkdir(parents=True, exist_ok=True)
    pslog = HERE / "sweep_ps.log"
    pslog.write_text(f"# opencode processes before each probe, {dt.datetime.now()}\n")
    # tool_surface.csv accumulates across sweeps. It used to be rewritten from
    # the current MODELS list alone, which silently dropped every model of an
    # earlier sweep; a partial sweep is meant to add rows, not replace the file.
    # Keyed by model so a deliberate re-probe (e.g. under new MODEL_LIMITS)
    # overwrites its own stale row and nothing else.
    prior: dict[str, dict] = {}
    csv_path = HERE / "tool_surface.csv"
    if csv_path.exists():
        with open(csv_path, newline="") as fh:
            for r in csv.DictReader(fh):
                if r.get("model"):
                    prior[r["model"]] = r
    rows = []
    for n, m in enumerate(MODELS):
        if n:
            time.sleep(SPACING)   # keep gateway load low and episodes distinguishable
        procs = ps_snapshot()
        with open(pslog, "a") as fh:
            fh.write(f"--- {dt.datetime.now().isoformat()} before {m}\n")
            fh.write("".join(f"    {p}\n" for p in procs) or "    (none)\n")
        print(f"probing {m} ... ({len(procs)} opencode proc(s) alive)", flush=True)
        try:
            row = run_one(m, template)
        except Exception as exc:  # noqa: BLE001
            row = {"model": m, "writer_used": "ERROR", "error": str(exc)[:200]}
        rows.append(row)
        if row.get("server_error") == "y":
            with open(pslog, "a") as fh:
                fh.write(f"!!! server-error episode on {m}; ps at failure:\n")
                fh.write("".join(f"    {p}\n" for p in ps_snapshot()) or "    (none)\n")
        print(f"   -> writer={row.get('writer_used')} hello={row.get('hello_written')} "
              f"list_channels={row.get('list_channels_ok')} "
              f"cost={row.get('cost_usd')} {row.get('wall_s')}s "
              f"rc={row.get('rc')} timeout={row.get('timed_out')}", flush=True)
        cols = ["model", "writer_used", "writer_named", "hello_written", "bash_absent",
                "run_exclurad_absent", "tmp_write_refused", "list_channels_ok",
                "instructions_leaked", "cost_usd", "wall_s", "rc", "timed_out",
                "n_tool_calls", "tools_called", "attempts", "server_error",
                "agent_fallback", "session_id"]
        merged = dict(prior)
        for r in rows:
            merged[r["model"]] = r
        with open(csv_path, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            w.writerows(merged.values())
    print(f"\nwrote {csv_path} ({len(prior)} prior + {len(rows)} this sweep)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


# NOTE (2026-09-09), OpenCode 1.18.28 -- "Unexpected server error" SOLVED
# --------------------------------------------------------------------------
# Root cause: `opencode run` resolves a RELATIVE --dir against the $PWD
# environment variable, not against the process's actual working directory.
# subprocess.Popen(cwd=D) changes the child's cwd but leaves PWD pointing at
# the parent, so `--dir .` sent opencode to the PARENT directory, where no
# opencode.json defines the `legd` agent -- and `--agent legd` there dies with
# the generic {"type":"error", ... "Unexpected server error"}.
#
# Proven by holding everything else fixed and toggling one thing at a time,
# same model and same minute:
#     Popen(cwd=D), --dir .                     rc=1 FAIL (3/3)
#     Popen(cwd=D), --dir <absolute>            rc=0 ok
#     Popen(cwd=D), --dir ., env PWD=D          rc=0 ok
#     Popen(cwd=D), --dir ., no --agent         rc=0 ok
#     zsh -c 'cd D && ... --dir .' from python  rc=0 ok
# Ruled out along the way: env contents (parent and child environments were
# byte-identical but for `_`), start_new_session, NO_COLOR, stdin, stdout to
# file vs pipe, CLAUDE* variables, binary path, and directory recreation.
#
# This also retires the "episodes" story in earlier versions of this note. The
# failure was never intermittent. It was 100% reproducible from a Python
# parent and 0% from a shell, and I had been mixing the two while bisecting:
# shell tests (PWD correct) passed, driver runs (PWD stale) failed, and the
# alternation looked like something coming and going on its own. It also
# explains the one observation that seemed impossible -- the built-in `build`
# agent working at the instant `legd` failed. In the wrong directory `build`
# still exists and `legd` does not.
#
# run_leg_d.py was never affected: it has always passed an absolute --dir.
# That is why the 30-conversation pilot and every shakedown came out clean
# while this driver failed every model it touched.
#
# Still true, and still the reason --agent must stay: dropping it loses the
# tool gates (bash and the MCP tools come back) and AgentConfig.maxSteps has
# no top-level equivalent, so the step cap goes too.
