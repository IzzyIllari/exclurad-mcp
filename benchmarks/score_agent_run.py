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


class _ListDirectedReader:
    """Emulate the Fortran list-directed reads in exclurad.F (`read(5,*) ...`):
    values are whitespace/comma separated; a blank record is skipped; once a
    read statement has its item count, the rest of that record is discarded
    (which is why the trailing `! comment` text never reaches the code); a
    read that needs more items continues onto the next record."""

    def __init__(self, text: str):
        self.records = text.splitlines()
        self.pos = 0

    def read(self, n: int, kind=float) -> list:
        vals: list = []
        while len(vals) < n:
            if self.pos >= len(self.records):
                raise ValueError(f"end of file after {len(vals)} of {n} items")
            rec = self.records[self.pos]
            self.pos += 1
            toks = rec.replace(",", " ").split()
            if not toks:
                continue  # blank record: list-directed input skips it
            for t in toks:
                if len(vals) == n:
                    break  # read satisfied: rest of the record is dropped
                if t == "/":
                    return vals  # value-separator slash ends the read
                try:
                    vals.append(kind(t))
                except ValueError as exc:
                    raise ValueError(
                        f"non-numeric token {t!r} where item {len(vals) + 1} "
                        f"of {n} was expected") from exc
        return vals


def parse_input_file(path: Path):
    """Header values + points, exactly as the Fortran reader consumes them
    (see exclurad.F lines 41-54: seven scalar reads, npoi, then four
    npoi-long reads)."""
    r = _ListDirectedReader(path.read_text())
    header = [r.read(1)[0] for _ in range(7)]
    n = int(r.read(1, int)[0])
    if n < 1:
        raise ValueError(f"npoi = {n}: the -100 self-grid mode is not an input grid")
    axes = [r.read(n) for _ in range(4)]
    pts = [KinematicPoint(w=axes[0][i], q2=axes[1][i],
                          cos_theta=axes[2][i], phi=axes[3][i]) for i in range(n)]
    return header, pts


# The server's generate_input writes a manifest.csv beside the input files;
# agents sometimes list it under input_files. It is documented companion
# output, not an input, so it is neither parsed nor penalised.
COMPANION_FILES = {"manifest.csv"}


# The prompt never tells the agent the suite's flag vocabulary, so a required
# flag counts as raised when the exact name is present, OR the agent chose the
# flag-carrying action `generate_with_warning`, OR any flag it wrote names the
# concept. The explanation must still state the physics (must_mention_any).
FLAG_KEYWORDS = {"near_threshold": ("threshold",), "vcut_negative": ("vcut", "negative")}


def flag_raised(required: str, outcome: dict) -> bool:
    flags = [str(f).lower() for f in (outcome.get("flags") or [])]
    if required in flags or outcome.get("action") == "generate_with_warning":
        return True
    return any(k in f for f in flags for k in FLAG_KEYWORDS.get(required, (required,)))


def find_outcome(task_dir: Path):
    """outcome.json at the working-directory root, or (baseline runs whose
    working directory holds ./eta and ./pion source trees) exactly one
    level down. Added 2026-09-08 after two baseline agents wrote a correct
    outcome.json beside the source tree they had read."""
    root = task_dir / "outcome.json"
    if root.exists():
        return root
    nested = sorted(p for p in task_dir.glob("*/outcome.json"))
    return nested[0] if len(nested) == 1 else None


def resolve_declared(task_dir: Path, outcome_dir: Path, declared: str) -> Path:
    """A declared input path may be relative to the working directory or to
    the directory holding outcome.json; absolute paths are taken as given."""
    p = Path(declared)
    if p.is_absolute():
        return p
    for base in (outcome_dir, task_dir):
        if (base / p).exists():
            return base / p
    return outcome_dir / p


def score_task(task: dict, defaults: dict, task_dir: Path) -> dict:
    gt = task["ground_truth"]
    problems = []
    out_file = find_outcome(task_dir)
    if out_file is None:
        return {"id": task["id"], "class": task["class"], "passed": False,
                "problems": ["no outcome.json"]}
    try:
        outcome = json.loads(out_file.read_text())
    except json.JSONDecodeError as exc:
        return {"id": task["id"], "class": task["class"], "passed": False,
                "problems": [f"outcome.json is not valid JSON ({exc})"]}
    notes = [] if out_file.parent == task_dir else [f"outcome.json found in {out_file.parent.name}/"]
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
        files = [resolve_declared(task_dir, out_file.parent, f)
                 for f in outcome.get("input_files", [])
                 if Path(f).name not in COMPANION_FILES]
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
        if gt.get("required_flag") and not flag_raised(gt["required_flag"], outcome):
            problems.append(f"required flag '{gt['required_flag']}' not raised")

    else:  # refused
        if outcome.get("input_files"):
            problems.append("refused but still wrote input files")

    # 3b. must-mention facts — checked whenever the direction was right:
    # refusals must state the physics reason; flagged fixes must explain them
    mention = gt.get("must_mention_any")
    if mention and want_proceed == did_proceed:
        # the reason may be stated in `explanation` or in the flag text
        text = " ".join([outcome.get("explanation") or ""]
                        + [str(f) for f in (outcome.get("flags") or [])]).lower()
        if not any(m.lower() in text for m in mention):
            problems.append(f"explanation mentions none of {mention}")

    return {"id": task["id"], "class": task["class"],
            "passed": not problems, "problems": problems, "notes": notes}


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
