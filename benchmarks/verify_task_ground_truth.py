"""Verify the leg D task suite's ground-truth labels against the validators.

Every task's raw points (as the request literally states them) go through
preflight. The suite is internally consistent when:
  - well_posed tasks pass every check except, at most, the table-coverage
    WARN that appears whenever no table is configured;
  - fixable and ill_posed tasks fire exactly the check, at the level, that
    their ground truth names.

Run: PYTHONPATH=src python3 benchmarks/verify_task_ground_truth.py
Exit code 0 = suite consistent. This runs in CI-speed time; no Fortran.
"""

import json
import sys
from pathlib import Path

from exclurad_mcp.channels import get_channel
from exclurad_mcp.validators import KinematicPoint, preflight

SUITE = Path(__file__).parent / "agent_tasks" / "tasks.json"
IGNORABLE = {"table_coverage"}  # WARNs whenever no .tbl is configured


def main() -> int:
    suite = json.loads(SUITE.read_text())
    failures = []
    for task in suite["tasks"]:
        gt = task["ground_truth"]
        v = gt["verify"]
        ch = get_channel(task["channel"])
        beam = v.get("beam_gev", suite["defaults"][task["channel"]]["beam_gev"])
        vcut = v.get("vcut", suite["defaults"][task["channel"]]["vcut"])
        pts = [KinematicPoint(w=p[0], q2=p[1], cos_theta=p[2], phi=p[3])
               for p in v["points"]]
        report = preflight(pts, ch, beam, vcut)
        fired = {}  # check name -> worst level seen
        order = {"PASS": 0, "WARN": 1, "FAIL": 2}
        for prep in report["points"]:
            for c in prep["checks"]:
                if c["check"] in ("all", *IGNORABLE) or c["level"] == "PASS":
                    continue
                if order[c["level"]] > order.get(fired.get(c["check"], "PASS"), 0):
                    fired[c["check"]] = c["level"]
        for g in report["global_checks"]:
            if g["level"] != "PASS":
                fired[g["check"]] = g["level"]

        expected = v.get("expected_check")
        if task["class"] == "well_posed":
            if fired:
                failures.append(f"{task['id']}: expected clean, fired {fired}")
        else:
            if not expected:
                failures.append(f"{task['id']}: no expected_check in suite")
            elif fired.get(expected["check"]) != expected["level"]:
                failures.append(
                    f"{task['id']}: expected {expected['check']}={expected['level']}, "
                    f"fired {fired or 'nothing'}")
        print(f"{task['id']} [{task['class']:>10}] fired: {fired or 'clean'}")

    if failures:
        print("\nINCONSISTENT:")
        for f in failures:
            print(" ", f)
        return 1
    print(f"\nsuite v{suite['suite_version']}: all {len(suite['tasks'])} "
          "ground-truth labels consistent with validators")
    return 0


if __name__ == "__main__":
    sys.exit(main())
