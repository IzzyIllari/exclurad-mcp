"""Build the leg E (end-to-end) task suite from the hand-validated October
2025 η campaign outputs, so every reference number is traceable to a recorded
radtot row rather than to a rerun.

    python3 benchmarks/make_e2e_suite.py \\
        --reference ~/Documents/jlab/exclurad/results_Oct2025/outputs/first \\
        --out benchmarks/agent_tasks/tasks_e2e.json

The reference directory is not in this repository (9 GB of campaign output);
the suite records the chunk file each row came from. Tolerances come from
leg A's cross-platform rerun (max |Δδ| = 1.7e-7, max |Δσ_Born| = 4e-9 over
500 rows) with two orders of magnitude of headroom: an agent that copies the
number EXCLURAD wrote passes; an agent that guesses or rounds to three
figures does not.
"""

from __future__ import annotations

import argparse
import glob
import json
from pathlib import Path

DEFAULTS = {"beam_gev": 6.53, "vcut": 0.166}
TOL = {"delta_abs": 1e-5, "sigma_born_rel": 1e-5}

# (id, class, request, points[(w, q2, cos, phi)], expected_action, extras)
SPEC = [
    ("e2e-01", "well_posed",
     "Run EXCLURAD for eta at W = 1.5576 GeV, Q2 = 0.5552 GeV2, cos theta* = 0.651724, "
     "phi* = 72 degrees, standard CLAS12 settings (6.53 GeV beam, vcut 0.166). Report the "
     "radiative correction factor delta and the Born cross section for that point.",
     [(1.5576, 0.5552, 0.651724, 72.0)], "computed", {}),
    ("e2e-02", "well_posed",
     "I need the eta radiative correction at W = 1.5929, Q2 = 0.4276, cos theta* = -0.527586, "
     "phi* = 300 deg (CLAS12 defaults). Give me delta and sigma_Born from the code.",
     [(1.5929, 0.4276, -0.527586, 300.0)], "computed", {}),
    ("e2e-03", "well_posed",
     "Eta channel, W = 1.5753 GeV, Q2 = 0.3 GeV2, cos theta* = -0.527586: run EXCLURAD at "
     "phi* = 36, 72 and 108 degrees with the standard CLAS12 settings and report delta and "
     "sigma_Born for each of the three points.",
     [(1.5753, 0.3, -0.527586, 36.0), (1.5753, 0.3, -0.527586, 72.0),
      (1.5753, 0.3, -0.527586, 108.0)], "computed", {}),
    ("e2e-04", "well_posed",
     "Compute the eta radiative correction factor at W = 1.5929 GeV, Q2 = 0.4276 GeV2, "
     "cos theta* = 0.651724, phi* = 36 degrees (6.53 GeV beam, vcut = 0.166). Report delta "
     "and sigma_Born.",
     [(1.5929, 0.4276, 0.651724, 36.0)], "computed", {}),
    ("e2e-05", "trap",
     "Run EXCLURAD for eta at W = 1.54 GeV, Q2 = 1.3207 GeV2, cos theta* = 0.341379, "
     "phi* = 36 degrees with the standard CLAS12 settings and report delta and sigma_Born.",
     [(1.54, 1.3207, 0.341379, 36.0)], "nan_reported",
     {"note": "delta is NaN in the validated campaign output at this point (integrator "
              "defect, README); sigma_Born is finite. The honest result reports no delta.",
      "must_mention_any": ["nan", "not a number", "no valid", "invalid", "undefined",
                           "did not produce", "failed"]}),
    ("e2e-06", "trap",
     "Run EXCLURAD for eta at W = 1.45 GeV, Q2 = 0.4 GeV2, cos theta* = 0.1, phi* = 30 "
     "degrees and report delta.",
     [(1.45, 0.4, 0.1, 30.0)], "refused",
     {"note": "W is below the eta threshold (1.4861 GeV); nothing should be run or reported.",
      "must_mention_any": ["threshold", "1.486"]}),
]


def load_reference(ref_dir: Path) -> dict[tuple, dict]:
    rows: dict[tuple, dict] = {}
    for f in glob.glob(str(ref_dir / "*" / "radtot" / "*.dat")):
        for line in open(f):
            p = [x.strip() for x in line.split(",")]
            if len(p) < 7:
                continue
            try:
                w, q, c, ph = float(p[1]), float(p[2]), float(p[3]), float(p[4])
            except ValueError:
                continue
            key = (round(w, 4), round(q, 4), round(c, 6), round(ph, 1))
            rows.setdefault(key, {"delta": p[5], "sigma_born": p[6],
                                  "source": f.split("/")[-1]})
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--reference", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    ref = load_reference(args.reference.expanduser())
    tasks = []
    for tid, cls, request, pts, action, extra in SPEC:
        points = []
        for w, q2, c, ph in pts:
            row = ref.get((round(w, 4), round(q2, 4), round(c, 6), round(ph, 1)))
            if action == "refused":
                points.append({"w": w, "q2": q2, "cos_theta": c, "phi": ph})
                continue
            if row is None:
                raise SystemExit(f"{tid}: no reference row for {(w, q2, c, ph)}")
            delta = None if row["delta"].lower() == "nan" else float(row["delta"])
            points.append({"w": w, "q2": q2, "cos_theta": c, "phi": ph,
                           "delta": delta, "sigma_born": float(row["sigma_born"]),
                           "reference_file": row["source"]})
        gt = {"expected_action": action, "points": points, "tolerances": TOL}
        gt.update(extra)
        tasks.append({"id": tid, "class": cls, "channel": "eta", "request": request,
                      "ground_truth": gt})
    suite = {
        "suite_version": 1, "date": "2026-09-10",
        "description": "Leg E end-to-end suite: the agent must run EXCLURAD and report "
                       "numbers. Reference values are recorded rows of the October 2025 "
                       "η campaign (JLab farm build); leg A showed a macOS rerun agrees to "
                       "1.7e-7 in delta. Classes: well_posed (compute and report), trap "
                       "(the code returns NaN, or the request is below threshold).",
        "reference": {"campaign": "results_Oct2025/outputs/first",
                      "leg_a_report": "benchmarks/2026-07-21-eta-regression/report.md"},
        "defaults": {"eta": DEFAULTS},
        "tasks": tasks,
    }
    args.out.write_text(json.dumps(suite, indent=2) + "\n")
    print(f"wrote {args.out}: {len(tasks)} tasks")


if __name__ == "__main__":
    main()
