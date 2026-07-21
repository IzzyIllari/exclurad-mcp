# Chain test: exclurad-mcp → plotwright (2026-07-04)

First full hands-off pass of the pipeline the DNP talk describes:

**EXCLURAD chunk outputs → `parse_output`/`collect_results` (this package) →
tidy CSV → plotwright (profile → `suggest_figures` → `render`) → figure.**

Both tools share the same thesis: the model orchestrates, a deterministic
layer holds the correctness/quality floor.

## Inputs

`results_Oct2025/outputs/{first,second,third}` on Izzy's Mac — the CLAS12 η
30×30×30×30 grid chunks (26,500 radtot files). Aggregated + deduplicated on
(W, Q², cos θ*, φ) → 264,897 unique points, written to
`results_Oct2025/radtot_full_tidy.csv` (42 MB, not in this repo).

## Files here

- `plotwright_line.png` — δ = σ_obs/σ₀ vs W for Q² ∈ {0.3, 1.32, 2.72, 4.0}
  GeV² at cos θ* = −0.031, φ* = 96°. δ rises from ~0.61 near the η threshold
  to >1 above W ≈ 1.61 GeV — consistent with the ~30% variation reported in
  arXiv:2604.22943.
- `plotwright_line_regen.py` — plotwright's standalone regeneration script.
- `delta_vs_w_slice.csv` — the 39-row slice behind the figure.
- `render_chain.py` — the driver: took plotwright's top *suggested* spec
  (schema-valid by construction), changed only plot_type scatter→line and
  labels. No hand-written spec.

## Findings the chain surfaced (data quality, not tooling)

1. **W coverage stops at 1.6459 GeV** in first/second/third — the upper
   two-thirds of the planned 1.487–1.999 range isn't in these groups
   (unfinished? elsewhere?). Track down before making paper-grade figures.
2. **Grid holes**: the expected 11×4 slice has 39/44 points (e.g. Q²=4.0
   missing its highest-W point) — exactly what `map_failures` exists to map.
3. **`asym_rc_pct` is garbage at φ = 0/180/360**: BSA ∝ sin φ → A_Born ≈ 0,
   so the relative correction blows up (±8000%, one literal Fortran
   `****************` overflow — the parser skips it and reports it as an
   unparsed line rather than swallowing it).
4. **cos grids differ between groups** (33 distinct values, not 30): `third`
   used cos = 0.0 exactly while the main grid uses ±0.031. Dedup keyed on
   exact kinematics handles it, but slicing must pick values that exist.
5. `wq2_runs/` contains inputs+logs but **zero outputs** — an aborted run.

## Reproduce

```bash
conda activate plotwright   # env created 2026-07-04; plotwright installed editable
python demo/plotwright-chain/render_chain.py   # after regenerating the slice CSV
# or just: python demo/plotwright-chain/plotwright_line_regen.py
```
