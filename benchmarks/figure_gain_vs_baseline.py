"""Slide figure for leg D: the server's gain against the model's baseline
pass rate, one point per harness × model cell.

    python3 benchmarks/figure_gain_vs_baseline.py <combined-report-dir>

Reads <dir>/leg_d/figure_combined.csv (written by report_leg_d_combined.py)
and writes <dir>/leg_d/figure_gain_vs_baseline.{png,pdf,csv}. Codex cells are
drawn hollow: per PROTOCOL.md they are a labelled replication with a
different tool surface and are never pooled with the other harnesses. Models
whose with-server failures are delivery failures (outcome JSON printed as chat
text, or unparseable) are drawn as grey crosses and named in the caption; the
figure is about physics accuracy, and for those two models the score measures
something else (see LEG_D_RESULTS.md).
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

DELIVERY_BROKEN = {"Nemotron 3.5 Lightning 30B", "Muse Glimmer 30B"}
FRONTIER = {"claude-sonnet-5", "claude-haiku-4.5", "gpt-5.4", "gpt-5.6-luna", "gpt-5.6-terra", "gpt-5.6-sol"}
DISPLAY = {
    "NVIDIA-Nemotron-3-Super-120B-A12B-FP8": "Nemotron 3 Super 120B",
    "NVIDIA-Nemotron-3-Nano-30B-A3B-BF16": "Nemotron 3 Nano 30B",
    "NVIDIA-Nemotron-3.5-Lightning-30B-A3B-NVFP4": "Nemotron 3.5 Lightning 30B",
    "Inkling-Small-NVFP4": "Inkling Small",
    "Laguna-S-2.1-NVFP4": "Laguna S 2.1",
    "Mistral-Medium-3.5-128B": "Mistral Medium 3.5 128B",
    "Muse-Glimmer-30B": "Muse Glimmer 30B",
}


def main() -> None:
    d = Path(sys.argv[1]) / "leg_d"
    draw(d, slide=False)
    draw(d, slide=True)


def draw(d: Path, slide: bool) -> None:
    """slide=True: half-slide physical size with type that stays legible when
    the PDF is placed at ~80 mm width in a 16:9 Beamer frame."""
    rows = list(csv.DictReader(open(d / "figure_combined.csv")))
    cells: dict[tuple, dict] = {}
    for r in rows:
        key = (r["harness"], r["model"])
        cells.setdefault(key, {})[r["condition"]] = r
    pts = []
    for (h, m), c in cells.items():
        w, b = c["with-server"], c["baseline"]
        name = DISPLAY.get(m, m)
        pts.append({"harness": h, "model": name,
                    "frontier": m in FRONTIER,
                    "baseline_pct": float(b["pass_rate_pct"]), "with_server_pct": float(w["pass_rate_pct"]),
                    "gain_pp": round(float(w["pass_rate_pct"]) - float(b["pass_rate_pct"]), 1),
                    "baseline_n": b["n"], "with_server_n": w["n"],
                    "delivery_broken": name in DELIVERY_BROKEN})
    pts.sort(key=lambda p: p["baseline_pct"])
    with open(d / "figure_gain_vs_baseline.csv", "w", newline="") as f:
        wri = csv.DictWriter(f, fieldnames=list(pts[0]))
        wri.writeheader()
        wri.writerows(pts)

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D

    # Okabe–Ito: open-weight models orange, frontier models blue; shape = harness.
    col = {True: "#0072B2", False: "#E69F00"}
    marker = {"OpenCode": "o", "Claude Code": "s", "Codex": "D"}
    fs = 9 if slide else 7.5
    fig, ax = plt.subplots(figsize=(3.6, 3.7) if slide else (6.4, 4.9))
    ax.axhline(0, color="#999999", linewidth=0.8)
    for p in pts:
        if p["delivery_broken"]:
            ax.scatter(p["baseline_pct"], p["gain_pp"], marker="x", s=70 if slide else 55, color="#777777", linewidths=1.4, zorder=3)
            continue
        hollow = p["harness"] == "Codex"
        ax.scatter(p["baseline_pct"], p["gain_pp"], marker=marker[p["harness"]], s=80 if slide else 64,
                   facecolor="white" if hollow else col[p["frontier"]], edgecolor=col[p["frontier"]],
                   linewidths=1.6, zorder=3)
    # direct labels on the open models (the story) and one frontier anchor
    label = {"Nemotron 3 Super 120B": (5, -12), "Nemotron 3 Nano 30B": (-5, 6), "gpt-oss-120b": (5, 4),
             "Mistral Medium 3.5 128B": (5, 4), "Laguna S 2.1": (-5, 6), "gemma-4-31B-it": (-5, -13),
             "Inkling Small": (5, 5)}
    if slide:
        label = {"Nemotron 3 Super 120B": (5, -13), "Nemotron 3 Nano 30B": (-5, 7), "gpt-oss-120b": (5, 5),
                 "Mistral Medium 3.5 128B": (5, 5)}
        label_text = {"Nemotron 3 Super 120B": "Nemotron 3\nSuper 120B", "Nemotron 3 Nano 30B": "Nemotron 3 Nano 30B",
                      "gpt-oss-120b": "gpt-oss-120b", "Mistral Medium 3.5 128B": "Mistral Medium 3.5"}
    else:
        label_text = {k: k for k in label}
    for p in pts:
        if p["model"] in label and p["harness"] == "OpenCode":
            dx, dy = label[p["model"]]
            ax.annotate(label_text[p["model"]], (p["baseline_pct"], p["gain_pp"]), xytext=(dx, dy),
                        textcoords="offset points", fontsize=fs - 1, color="#333333",
                        ha="left" if dx > 0 else "right", va="top" if dy < 0 else "bottom")
    ax.set_xlabel("pass rate without the server (%)" if slide else "pass rate without the server (%), 15 tasks × 3 reps", fontsize=fs)
    ax.set_ylabel("gain with the server (points)" if slide else "gain with the server (percentage points)", fontsize=fs)
    ax.tick_params(labelsize=fs)
    ax.set_xlim(0, 100)
    ax.set_ylim(-10, 65)
    ax.grid(color="#e5e5e5", linewidth=0.6)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    if slide:
        handles = [
            Line2D([], [], marker="o", linestyle="", color=col[False], markersize=7, label="open-weight (OpenCode)"),
            Line2D([], [], marker="o", linestyle="", color=col[True], markersize=7, label="frontier (OpenCode)"),
            Line2D([], [], marker="s", linestyle="", color=col[True], markersize=7, label="frontier (Claude Code)"),
            Line2D([], [], marker="D", linestyle="", markerfacecolor="white", markeredgecolor=col[True],
                   markeredgewidth=1.6, markersize=6, label="frontier (Codex, shell kept)"),
            Line2D([], [], marker="x", linestyle="", color="#777777", markersize=7, markeredgewidth=1.4,
                   label="delivery failures dominate"),
        ]
        ax.legend(handles=handles, fontsize=fs - 1.5, frameon=False, loc="upper center",
                  bbox_to_anchor=(0.42, -0.2), ncol=2, handletextpad=0.3, columnspacing=0.8)
        ax.set_title("One point per harness × model", fontsize=fs, loc="left")
    else:
        handles = [
            Line2D([], [], marker="o", linestyle="", color=col[False], markersize=7, label="open-weight model (OpenCode)"),
            Line2D([], [], marker="o", linestyle="", color=col[True], markersize=7, label="frontier model (OpenCode)"),
            Line2D([], [], marker="s", linestyle="", color=col[True], markersize=7, label="frontier model (Claude Code)"),
            Line2D([], [], marker="D", linestyle="", markerfacecolor="white", markeredgecolor=col[True],
                   markeredgewidth=1.6, markersize=6, label="frontier model (Codex, shell kept)"),
            Line2D([], [], marker="x", linestyle="", color="#777777", markersize=7, markeredgewidth=1.4,
                   label="score dominated by delivery failures"),
        ]
        ax.legend(handles=handles, fontsize=7.5, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.17), ncol=2)
        ax.set_title("The weaker the model, the more the server adds", fontsize=10, loc="left")
    fig.tight_layout()
    stem = "figure_gain_vs_baseline_slide" if slide else "figure_gain_vs_baseline"
    fig.savefig(d / f"{stem}.png", dpi=200)
    fig.savefig(d / f"{stem}.pdf")
    print(f"wrote {d}/{stem}.{{png,pdf}}: {len(pts)} cells")


if __name__ == "__main__":
    main()
