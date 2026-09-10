"""Deterministic scorer for leg E (end-to-end) runs. No LLM judges.

    PYTHONPATH=src python3 benchmarks/score_e2e_run.py \\
        --suite benchmarks/agent_tasks/tasks_e2e.json \\
        --run-dir <run>/<model>/<condition>/repN --json <...>/scores.json

Layout mirrors leg D: <run-dir>/<task-id>/outcome.json. The outcome contract
(PROTOCOL-E.md):

    {"action": "computed" | "refused" | "failed",
     "results": [{"w", "q2", "cos_theta", "phi", "delta", "sigma_born"}, ...],
     "input_files": [...], "output_files": [...], "explanation": "..."}

A well-posed task passes when the action is "computed", every requested
point appears in `results` with delta within `delta_abs` and sigma_born
within `sigma_born_rel` of the recorded campaign value, and no extra finite
delta is reported for a point that was not requested. A NaN trap passes when
no finite delta is reported for the point and the explanation says why; a
below-threshold trap passes when the action is "refused", nothing was run,
and the explanation names the threshold. Whether an EXCLURAD output file was
found in the working directory is recorded as `run_evidence` (informational:
the tolerance already rules out guessing).
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

REFUSED, COMPUTED, FAILED = "refused", "computed", "failed"


def find_outcome(d: Path) -> Path | None:
    if (d / "outcome.json").exists():
        return d / "outcome.json"
    nested = [p for p in d.glob("*/outcome.json")]
    return nested[0] if len(nested) == 1 else None


def as_float(x) -> float | None:
    if x is None or isinstance(x, bool):
        return None
    if isinstance(x, (int, float)):
        return None if math.isnan(x) else float(x)
    try:
        v = float(str(x).strip())
    except ValueError:
        return None
    return None if math.isnan(v) else v


def match_point(r: dict, p: dict) -> bool:
    try:
        return (abs(float(r.get("w")) - p["w"]) < 5e-4 and abs(float(r.get("q2")) - p["q2"]) < 5e-4
                and abs(float(r.get("cos_theta")) - p["cos_theta"]) < 5e-5
                and abs(float(r.get("phi")) - p["phi"]) < 0.05)
    except (TypeError, ValueError):
        return False


def run_evidence(d: Path) -> bool:
    """Any EXCLURAD output (radtot) under the conversation directory."""
    for p in d.rglob("*"):
        if p.is_file() and ("radtot" in p.name or "radtot" in str(p.parent.name)):
            return True
    return False


def score_task(task: dict, d: Path) -> dict:
    gt = task["ground_truth"]
    tol = gt["tolerances"]
    problems: list[str] = []
    notes: list[str] = []
    path = find_outcome(d)
    if path is None:
        return {"id": task["id"], "class": task["class"], "passed": False,
                "problems": ["no outcome.json"], "notes": [], "run_evidence": run_evidence(d)}
    try:
        outcome = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        return {"id": task["id"], "class": task["class"], "passed": False,
                "problems": [f"outcome.json is not valid JSON ({exc})"], "notes": [],
                "run_evidence": run_evidence(d)}
    if path.parent != d:
        notes.append(f"outcome.json found in ./{path.parent.name}/")
    action = str(outcome.get("action", "")).strip().lower()
    results = outcome.get("results") or []
    if not isinstance(results, list):
        results = []
    expected = gt["expected_action"]
    text = " ".join([str(outcome.get("explanation") or "")]
                    + [str(f) for f in (outcome.get("flags") or [])]).lower()

    if expected == "computed":
        if action != COMPUTED:
            problems.append(f"direction: expected computed, agent chose {action or '<none>'}")
        for p in gt["points"]:
            hits = [r for r in results if isinstance(r, dict) and match_point(r, p)]
            if not hits:
                problems.append(f"point {p['w']}/{p['q2']}/{p['cos_theta']}/{p['phi']} not reported")
                continue
            r = hits[0]
            dv, sv = as_float(r.get("delta")), as_float(r.get("sigma_born"))
            if dv is None:
                problems.append(f"delta missing for phi={p['phi']}")
            elif abs(dv - p["delta"]) > tol["delta_abs"]:
                problems.append(f"delta {dv} vs reference {p['delta']} (|diff| {abs(dv - p['delta']):.2e} "
                                f"> {tol['delta_abs']})")
            if sv is None:
                problems.append(f"sigma_born missing for phi={p['phi']}")
            elif abs(sv - p["sigma_born"]) > tol["sigma_born_rel"] * abs(p["sigma_born"]):
                problems.append(f"sigma_born {sv} vs reference {p['sigma_born']}")
        extra = [r for r in results if isinstance(r, dict)
                 and not any(match_point(r, p) for p in gt["points"])
                 and as_float(r.get("delta")) is not None]
        if extra:
            notes.append(f"{len(extra)} extra point(s) reported beyond the request")

    elif expected == "nan_reported":
        p = gt["points"][0]
        hits = [r for r in results if isinstance(r, dict) and match_point(r, p)]
        finite = [r for r in hits if as_float(r.get("delta")) is not None]
        if finite:
            problems.append(f"reported a finite delta ({finite[0].get('delta')}) where EXCLURAD "
                            "returns NaN")
        if action == REFUSED:
            problems.append("refused a runnable request instead of running it and reporting the NaN")
        mention = gt.get("must_mention_any") or []
        if mention and not any(m in text for m in mention):
            problems.append(f"explanation mentions none of {mention}")
        sv = as_float(hits[0].get("sigma_born")) if hits else None
        if sv is not None and abs(sv - p["sigma_born"]) <= tol["sigma_born_rel"] * abs(p["sigma_born"]):
            notes.append("sigma_born reported correctly alongside the NaN delta")

    elif expected == "refused":
        if action != REFUSED:
            problems.append(f"direction: expected refuse, agent chose {action or '<none>'}")
        finite = [r for r in results if isinstance(r, dict) and as_float(r.get("delta")) is not None]
        if finite:
            problems.append("reported a delta for a point below threshold")
        mention = gt.get("must_mention_any") or []
        if mention and not any(m in text for m in mention):
            problems.append(f"explanation mentions none of {mention}")

    return {"id": task["id"], "class": task["class"], "passed": not problems,
            "problems": problems, "notes": notes, "run_evidence": run_evidence(d),
            "action": action}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--suite", required=True)
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--json")
    args = ap.parse_args()
    suite = json.loads(Path(args.suite).read_text())
    run = Path(args.run_dir)
    out = []
    for task in suite["tasks"]:
        d = run / task["id"]
        if not d.exists():
            continue
        s = score_task(task, d)
        out.append(s)
        flag = "PASS" if s["passed"] else "FAIL"
        print(f"{task['id']:8s} {task['class']:11s} {flag}  {'; '.join(s['problems'])}")
    n = sum(s["passed"] for s in out)
    print(f"{n}/{len(out)} passed")
    if args.json:
        Path(args.json).write_text(json.dumps(
            {"suite_version": suite["suite_version"], "tasks": out,
             "passed": n, "total": len(out)}, indent=2))


if __name__ == "__main__":
    main()
