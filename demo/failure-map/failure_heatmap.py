"""map_failures coverage map -> plotwright heatmap, for the October eta grid."""
import csv
import json
import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[2] / "src"))
from exclurad_mcp.outputs import coverage_map

from plotwright import load, render, suggest_figures

SC = "."  # directory holding oct2025_radtot_full.csv (tidy radtot table via parse_output)
OUT = str(__import__("pathlib").Path(__file__).resolve().parent)

# Reuse the deduplicated 264,897-point table built earlier this session.
rows = [
    {"w": float(r["w"]), "q2": float(r["q2"]),
     "cos_theta": float(r["cos_theta"]), "phi_deg": float(r["phi_deg"])}
    for r in csv.DictReader(open(f"{SC}/oct2025_radtot_full.csv"))
]
# The run design was 30 cos x 30 phi per (W, Q2) cell (grid dir name n30x30x30x30).
cov = coverage_map(rows, expected_per_cell=900)
print(json.dumps({k: v for k, v in cov.items() if k != "cells"}, indent=1))

worst = sorted(cov["cells"], key=lambda c: -c["n_missing"])[:8]
for c in worst:
    print(f"  W={c['w']:<7} Q2={c['q2']:<7} missing {c['n_missing']:>3} ({c['completeness_pct']}% complete)")

cells_csv = f"{OUT}/wq2_coverage_cells.csv"
with open(cells_csv, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["w", "q2", "n_present", "n_missing", "completeness_pct"])
    w.writeheader()
    w.writerows(cov["cells"])

ds = load(cells_csv)
# The suggester has no matrix-shaped candidate for this table, so construct
# the heatmap spec explicitly and let parse_spec validate it before render.
from plotwright import parse_spec
best = {
    "spec_version": 1,
    "output": "figure",
    "data": {"table": "wq2_coverage_cells"},
    "figure": {
        "plot_type": "heatmap",
        "encodings": {
            "x": {"field": "w", "label": "W [GeV]"},
            "y": {"field": "q2", "label": "Q² [GeV²]"},
            "value": {"field": "n_missing", "label": "missing points"},
        },
    },
    "title": ("Missing kinematic points per (W, Q²) cell — CLAS12 η grid, "
              "Oct 2025 (expected 900 = 30 cosθ* × 30 φ*)"),
}
parse_spec(best)  # schema check before rendering
result = render(ds, best, out_dir=OUT)
print("files:", [str(f) for f in result.files])
print("alt:", result.alt_text[:300])
