"""Final stage of the exclurad-mcp -> plotwright chain test."""
import json

from plotwright import load, render, suggest_figures

SC = "."  # directory holding the intermediate CSVs

ds = load(f"{SC}/delta_vs_w_slice.csv")

# Take the top suggested (schema-valid) spec and adjust minimally:
# scatter -> line, plus physics labels.
spec = suggest_figures(
    ds, goal="radiative correction factor delta versus W, one series per Q2"
)[0].spec
spec["figure"]["plot_type"] = "line"
spec["figure"]["encodings"]["x"]["label"] = "W [GeV]"
spec["figure"]["encodings"]["y"]["label"] = "δ = σ_obs / σ_0"
spec["figure"]["encodings"]["series"]["label"] = "Q²"
spec["title"] = (
    "EXCLURAD radiative correction factor, ep → e'pη at 6.535 GeV "
    "(cos θ* = −0.03, φ* = 96°)"
)

result = render(ds, spec, out_dir=f"{SC}/plotwright_out")
print("files:", result.files)
print("alt_text:", result.alt_text)
print("regen_script:", bool(result.regen_script))
