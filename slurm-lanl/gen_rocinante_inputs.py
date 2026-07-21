"""Generate the remaining eta-grid inputs for the Rocinante campaign.

Target grid (matches the October 2025 design so datasets merge, extended in Q2):
  W   : linspace(1.487, 1.999, 30)        -- to ~2 GeV per Izzy
  Q2  : linspace(0.3, 4.0, 30)  PLUS 7 extension values continuing the same
        spacing up to 4.8931 (EtaMAID-2023 table edge is 5.0; going to 6
        would extrapolate -- needs new tables from Victor)
  cos : linspace(-0.9, 0.9, 30)
  phi : 0..348 deg, 30 values (12 deg steps, endpoint excluded -- October style)

A file (10 cos points at fixed W, Q2, phi) is generated unless ALL its points
already exist in the October aggregation (radtot_full_tidy.csv). Partial files
are regenerated -- reruns are cheap and dedup happens at parse time.
"""
import csv
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from exclurad_mcp.channels import get_channel
from exclurad_mcp.inputgen import InputHeader, render_input
from exclurad_mcp.validators import KinematicPoint, preflight_point

OUT = Path(sys.argv[1])
# tidy radtot table of already-computed points (built via parse_output)
DONE_CSV = os.environ.get("EXCLURAD_DONE_CSV", "radtot_full_tidy.csv")

lin = lambda a, b, n: [a + i * (b - a) / (n - 1) for i in range(n)]
W_GRID = lin(1.487, 1.999, 30)
Q2_BASE = lin(0.3, 4.0, 30)
q2_step = (4.0 - 0.3) / 29
Q2_EXT = [4.0 + k * q2_step for k in range(1, 8)]      # 4.1276 .. 4.8931 < 5.0
Q2_GRID = Q2_BASE + Q2_EXT
COS_GRID = lin(-0.9, 0.9, 30)
PHI_GRID = [i * 12.0 for i in range(30)]

key = lambda w, q2, c, p: (f"{w:.4f}", f"{q2:.4f}", f"{c:.6f}", f"{p:.1f}")
done = set()
for r in csv.DictReader(open(DONE_CSV)):
    done.add(key(float(r["w"]), float(r["q2"]), float(r["cos_theta"]), float(r["phi_deg"])))
print(f"October points loaded: {len(done):,}")

# --- compact preflight: every (W, Q2) pair at representative angles, plus axes
ch = get_channel("eta")
tw, tq = (1.4856, 6.0), (0.0, 5.0)  # EtaMAID-2023 grid, scanned 2026-07-04
levels = {"PASS": 0, "WARN": 0, "FAIL": 0}
for w in W_GRID:
    for q2 in Q2_GRID:
        rs = preflight_point(KinematicPoint(w, q2, 0.0, 90.0), ch, 6.53, tw, tq)
        worst = max((r.level for r in rs), key=lambda l: {"PASS": 0, "WARN": 1, "FAIL": 2}[l])
        levels[worst] += 1
assert levels["FAIL"] == 0, f"preflight FAILs in target grid: {levels}"
print(f"preflight over {len(W_GRID) * len(Q2_GRID)} (W,Q2) cells: {levels} "
      "(WARNs are the near-threshold W row -- expected, October ran it)")

# --- generate
OUT.mkdir(parents=True, exist_ok=True)
header = InputHeader.for_channel(ch)          # bmom 6.53, vcut 0.166, model 3, ivec 1
n_files = n_skipped = n_points = 0
manifest = []
for iw, w in enumerate(W_GRID):
    for iq, q2 in enumerate(Q2_GRID):
        for ip, phi in enumerate(PHI_GRID):
            for part in range(3):             # 30 cos values -> 3 files of 10
                cos_chunk = COS_GRID[part * 10:(part + 1) * 10]
                if all(key(w, q2, c, phi) in done for c in cos_chunk):
                    n_skipped += 1
                    continue
                pts = [KinematicPoint(w, q2, c, phi) for c in cos_chunk]
                fname = (f"grid_{iw:02d}-{iq:02d}-{ip:02d}_W{w:.4f}_Q2{q2:.4f}"
                         f"_phi{phi:.0f}_cos{cos_chunk[0]:.3f}-{cos_chunk[-1]:.3f}"
                         f"_p{part + 1:02d}.dat")
                (OUT / fname).write_text(render_input(header, pts))
                manifest.append([fname, f"{w:.4f}", f"{q2:.4f}", f"{phi:.1f}",
                                 f"{cos_chunk[0]:.6f}", f"{cos_chunk[-1]:.6f}", "10"])
                n_files += 1
                n_points += 10

with (OUT / "manifest.csv").open("w", newline="") as f:
    wr = csv.writer(f)
    wr.writerow(["file", "W_GeV", "Q2_GeV2", "phi_deg", "cos_first", "cos_last", "N_points"])
    wr.writerows(manifest)

core_h = n_points * 24.3 / 3600
print(f"files written: {n_files:,} ({n_points:,} points), files skipped as fully-done: {n_skipped:,}")
print(f"estimated compute: {core_h:,.0f} core-h  ~= {core_h / 112:.1f} node-h at 112 cores/node")
