"""Deterministic scorer for leg D agent-accuracy runs. No LLM judges.

A run directory contains one subdirectory per task id. Each holds the
agent's `outcome.json`:

    {"action": "generate" | "fix_and_generate" | "generate_with_warning"
               | "refuse",
     "input_files": ["relative/path.dat", ...],   // empty when refusing
     "flags": ["near_threshold", ...],            // optional
     "explanation": "..."}                        // required when refusing

plus whatever input files it wrote. See agent_tasks/PROTOCOL.md for how a
run is conducted.

Scoring per task:
  1. direction  — proceeded vs refused matches the ground truth;
  2. validity   — every written input file parses, respects the 10-point
                  limit, carries the right header, and every point passes
                  preflight (table-coverage WARN tolerated; the expected
                  WARN tolerated on generate_with_warning tasks);
  3. specifics  — required fixes applied (cos clamped, phi mapped), required
                  flags raised, refusals mention one of the required facts.

A task passes only if all applicable checks pass. Aggregates by class.

Run: PYTHONPATH=src python3 benchmarks/score_agent_run.py \
        --suite benchmarks/agent_tasks/tasks.json --run-dir <dir> [--json out]
"""

import argparse
import json
import sys
from pathlib import Path

from exclurad_mcp.channels import get_channel
from exclurad_mcp.validators import KinematicPoint, preflight

PROCEED = {"generate", "fix_and_generate", "generate_with_warning"}
IGNORABLE_CHECKS = {"table_coverage"}


def parse_input_file(path: Path):
    """Header tokens + points, exactly what the Fortran reader consumes."""
    lines = path.read_text().splitlines()
    header = [ln.split("!")[0].strip() for ln in lines[:7]]
    n_idx = next(i for i, ln in enumerate(lines) if "no. of points" in ln)
    n = int(lines[n_idx].split("!")[0])
    axes = []
    for off in range(1, 5):
        toks = lines[n_idx + off].split("!")[0].split()
        axes.append([float(t) for t in toks[:n]])
    pts = [KinematicPoint(w=axes[0][i], q2=axes[1][i],
                          cos_theta=axes[2][i], phi=axes[3][i]) for i in range(n)]
    return header, pts


def score_task(task: dict, defaults: dict, task_dir: Path) -> dict:
    gt = task["ground_truth"]
    problems = []
    out_file = task_dir / "outcome.json"
    if not out_file.exists():
        return {"id": task["id"], "class": task["class"], "passed": False,
                "problems": ["no outcome.json"]}
    outcome = json.loads(out_file.read_text())
    action = outcome.get("action", "")
    expected = gt["expected_action"]

    # 1. direction
    want_proceed = expected in PROCEED
    did_proceed = action in PROCEED
    if want_proceed != did_proceed:
        problems.append(f"direction: expected {expected}, agent chose {action or '??'}")

    ch = get_channel(task["channel"])
    v = gt.get("verify", {})
    beam = v.get("beam_gev", defaults[task["channel"]]["beam_gev"])
    vcut = v.get("vcut", defaults[task["channel"]]["vcut"])

    all_points = []
    if did_proceed:
        files = [task_dir / f for f in outcome.get("input_files", [])]
        if not files:
            problems.append("proceeded but wrote no input files")
        for f in files:
            if not f.exists():
                problems.append(f"missing declared file {f.name}")
                continue
            try:
                header, pts = parse_input_file(f)
            except Exception as exc:
                problems.append(f"{f.name}: unparseable ({exc})")
                continue
            if len(pts) > 10:
                problems.append(f"{f.name}: {len(pts)} points exceeds reader limit")
            if int(header[0]) != ch.model or int(header[5]) != ch.ivec_detected_hadron:
                problems.append(f"{f.name}: header model/ivec wrong for {ch.key}")
            all_points.extend(pts)

        # 2. validity through the same preflight the server uses
        if all_points:
            report = preflight(all_points, ch, beam, vcut)
            allowed_warn = None
            if expected == "generate_with_warning":
                allowed_warn = {"fx-02": "w_threshold", "fx-04": "vcut"}.get(task["id"])
            for prep in report["points"]:
                for c in prep["checks"]:
                    if c["check"] in ("all", *IGNORABLE_CHECKS) or c["level"] == "PASS":
                        continue
                    if c["level"] == "WARN" and c["check"] == allowed_warn:
                        continue
                    problems.append(
                        f"point {prep['index']}: {c['check']} {c['level']}")
            for g in report["global_checks"]:
                if g["level"] != "PASS" and g["check"] != allowed_warn:
                    problems.append(f"global: {g['check']} {g['level']}")

        # 3a. count + fix specifics
        if "n_points" in gt and len(all_points) != gt["n_points"]:
            problems.append(f"{len(all_points)} points written, expected {gt['n_points']}")
        if "n_files_expected" in gt and len(files) != gt["n_files_expected"]:
            problems.append(f"{len(files)} files, expected {gt['n_files_expected']}")
        if gt.get("required_fix") == "cos_clamped":
            if any(abs(p.cos_theta) >= 1.0 for p in all_points):
                problems.append("cos endpoints not clamped")
            if not any(abs(abs(p.cos_theta) - 0.999) < 1e-9 for p in all_points):
                problems.append("expected clamped +/-0.999 endpoints")
        if gt.get("required_fix") == "phi_mapped":
            if any(not (0.0 <= p.phi <= 360.0) for p in all_points):
                problems.append("phi not mapped into [0, 360]")
        if gt.get("required_flag") and gt["required_flag"] not in outcome.get("flags", []):
            problems.append(f"required flag '{gt['required_flag']}' not raised")

    else:  # refused
        if outcome.get("input_files"):
            problems.append("refused but still wrote input files")

    # 3b. must-mention facts — checked whenever the direction was right:
    # refusals must state the physics reason; flagged fixes must explain them
    mention = gt.get("must_mention_any")
    if mention and want_proceed == did_proceed:
        text = (outcome.get("explanation") or "").lower()
        if not any(m.lower() in text for m in mention):
            problems.append(f"explanation mentions none of {mention}")

    return {"id": task["id"], "class": task["class"],
            "passed": not problems, "problems": problems}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--suite", required=True)
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--json", help="write full results here")
    args = ap.parse_args()
    suite = json.loads(Path(args.suite).read_text())
    run_dir = Path(args.run_dir)

    rows = [score_task(t, suite["defaults"], run_dir / t["id"])
            for t in suite["tasks"]]
    by_class: dict[str, list] = {}
    for r in rows:
        by_class.setdefault(r["class"], []).append(r["passed"])
    summary = {
        "suite_version": suite["suite_version"],
        "n_tasks": len(rows),
        "passed": sum(r["passed"] for r in rows),
        "by_class": {k: f"{sum(v)}/{len(v)}" for k, v in sorted(by_class.items())},
        "tasks": rows,
    }
    if args.json:
        Path(args.json).write_text(json.dumps(summary, indent=2))
    for r in rows:
        mark = "PASS" if r["passed"] else "FAIL"
        print(f"{r['id']} [{r['class']:>10}] {mark}"
              + ("" if r["passed"] else f"  <- {'; '.join(r['problems'])}"))
    print(json.dumps({k: summary[k] for k in ("n_tasks", "passed", "by_class")}))
    sys.exit(0 if summary["passed"] == summary["n_tasks"] else 2)


if __name__ == "__main__":
    main()
