"""Two more slide figures from the combined report.

    python3 benchmarks/figure_slides.py <combined-report-dir>

Writes into <dir>/leg_d/figure_pooled_bars.{pdf,png,csv} (pooled pass rate by
scope, both conditions, Wilson 95% CIs) and <dir>/leg_e/figure_leg_e.{pdf,png,csv}
(per model: baseline, with-server on v0.1.1, with-server on v0.1.2). Headline
cells are selected exactly as report_leg_d_combined.py does: newest server
version per (harness, model, condition). Codex is shown as its own row and is
not inside any pooled row.
"""
from __future__ import annotations

import csv
import math
import sys
from collections import defaultdict
from pathlib import Path

FRONTIER = ("claude-sonnet-5", "claude-haiku-4-5", "gpt-5.4", "gpt-5.6-luna", "gpt-5.6-terra", "gpt-5.6-sol")
DELIVERY_BROKEN = ("Lightning", "Muse-Glimmer")
BLUE, ORANGE, INK = "#0072B2", "#E69F00", "#333333"


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - h) / d, (c + h) / d)


def version_key(v: str) -> tuple:
    return tuple(int(x) if x.isdigit() else 0 for x in v.split("."))


def headline(rows: list[dict]) -> list[dict]:
    newest: dict[tuple, str] = {}
    for r in rows:
        k = (r["harness"], r["model"], r["condition"])
        if k not in newest or version_key(r["server"]) > version_key(newest[k]):
            newest[k] = r["server"]
    return [r for r in rows if r["server"] == newest[(r["harness"], r["model"], r["condition"])]]


def is_frontier(model: str) -> bool:
    return any(f in model for f in FRONTIER)


def pooled_bars(d: Path, compact: bool = False) -> None:
    rows = headline(list(csv.DictReader(open(d / "leg_d" / "combined_results.csv"))))
    # Rows never pool across harnesses (PROTOCOL.md): OpenCode is the primary
    # cross-vendor comparison, Claude Code and Codex are shown as their own rows.
    scopes = [
        ("OpenCode, 13 models", lambda r: r["harness"] == "opencode"),
        ("  frontier, 4 models", lambda r: r["harness"] == "opencode" and is_frontier(r["model"])),
        ("  open-weight, 9 models", lambda r: r["harness"] == "opencode" and not is_frontier(r["model"])),
        ("  open-weight without the two\n  delivery-broken models, 7",
         lambda r: r["harness"] == "opencode" and not is_frontier(r["model"])
         and not any(b in r["model"] for b in DELIVERY_BROKEN)),
        ("Claude Code, 2 models", lambda r: r["harness"] == "claude"),
        ("Codex, 3 models\n(replication, shell kept)", lambda r: r["harness"] == "codex"),
    ]
    if compact:
        scopes = [("OpenCode\n13 models", scopes[0][1]), ("  frontier, 4", scopes[1][1]),
                  ("  open-weight, 9", scopes[2][1]),
                  ("Claude Code\n2 models", scopes[4][1]), ("Codex, 3\n(shell kept)", scopes[5][1])]
    fs = 9 if compact else 7.5
    stem = "figure_pooled_bars_slide" if compact else "figure_pooled_bars"
    out = []
    for name, sel in scopes:
        for cond in ("with-server", "baseline"):
            sub = [r for r in rows if r["condition"] == cond and sel(r)]
            k, n = sum(r["passed"] == "1" for r in sub), len(sub)
            lo, hi = wilson(k, n)
            out.append({"scope": name.replace("\n", " "), "condition": cond, "passed": k, "n": n,
                        "pass_rate_pct": round(100 * k / n, 1), "ci_lo_pct": round(100 * lo, 1),
                        "ci_hi_pct": round(100 * hi, 1)})
    with open(d / "leg_d" / f"{stem}.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(3.6, 3.9) if compact else (5.6, 3.7))
    ys = list(range(len(scopes)))[::-1]
    off = {"with-server": +0.19, "baseline": -0.19}
    col = {"with-server": ORANGE, "baseline": BLUE}
    for i, (name, _) in enumerate(scopes):
        for cond in ("with-server", "baseline"):
            r = next(o for o in out if o["scope"] == name.replace("\n", " ") and o["condition"] == cond)
            y = ys[i] + off[cond]
            p, lo, hi = r["pass_rate_pct"], r["ci_lo_pct"], r["ci_hi_pct"]
            ax.barh(y, p, height=0.34, color=col[cond], hatch="//" if cond == "with-server" else None,
                    edgecolor="white", linewidth=0.8,
                    label=("with the server" if cond == "with-server" else "Fortran source only") if i == 0 else None)
            ax.errorbar(p, y, xerr=[[p - lo], [hi - p]], fmt="none", ecolor=INK, elinewidth=1, capsize=2)
            txt = f"{p:.0f}%" if compact else f"{p:.0f}%  ({r['passed']}/{r['n']})"
            if hi < (70 if compact else 82):
                ax.text(hi + 1.2, y, txt, va="center", ha="left", fontsize=fs - 1, color=INK)
            else:
                ax.text(2, y, txt, va="center", ha="left", fontsize=fs - 1, color="white", fontweight="bold")
    ax.set_yticks(ys)
    ax.set_yticklabels([s[0] for s in scopes], fontsize=fs - 0.5)
    ax.set_xlim(0, 100)
    ax.set_xlabel("pass rate (%), Wilson 95% CI" if compact else "pass rate (%), 15 tasks × 3 repeats per cell, Wilson 95% CI", fontsize=fs)
    ax.tick_params(axis="x", labelsize=fs)
    ax.grid(axis="x", color="#e5e5e5", linewidth=0.6)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.legend(fontsize=fs - 1, frameon=False, loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=1 if compact else 2)
    if compact:
        pass
    fig.tight_layout()
    fig.savefig(d / "leg_d" / f"{stem}.pdf")
    fig.savefig(d / "leg_d" / f"{stem}.png", dpi=200)
    print("wrote", d / "leg_d" / f"{stem}.*")


def leg_e(d: Path) -> None:
    rows = list(csv.DictReader(open(d / "leg_e" / "lege_results.csv")))
    cells: dict[tuple, dict[str, list[int]]] = defaultdict(lambda: defaultdict(list))
    for r in rows:
        key = (r["harness"], r["model_short"])
        tag = "baseline" if r["condition"] == "baseline" else f"with-server v{r['server']}"
        cells[key][tag].append(int(r["passed"] in ("1", "True")))
    order = [("claude", "claude-sonnet-5"), ("claude", "claude-haiku-4.5"),
             ("codex", "gpt-5.6-sol"), ("codex", "gpt-5.6-terra"), ("codex", "gpt-5.6-luna")]
    label = {"claude": "Claude Code", "codex": "Codex"}
    out = []
    for h, m in order:
        for tag, v in cells[(h, m)].items():
            out.append({"harness": label[h], "model": m, "series": tag, "passed": sum(v), "n": len(v),
                        "pass_rate_pct": round(100 * sum(v) / len(v), 1)})
    with open(d / "leg_e" / "figure_leg_e.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D

    fig, ax = plt.subplots(figsize=(5.6, 3.5))
    ys = list(range(len(order)))[::-1]
    for i, (h, m) in enumerate(order):
        c = cells[(h, m)]
        y = ys[i]
        b = 100 * sum(c["baseline"]) / len(c["baseline"])
        w1 = 100 * sum(c["with-server v0.1.1"]) / len(c["with-server v0.1.1"])
        w2 = 100 * sum(c["with-server v0.1.2"]) / len(c["with-server v0.1.2"])
        if abs(w1 - w2) > 0.1:
            ax.annotate("", xy=(w2, y + 0.16), xytext=(w1, y + 0.16),
                        arrowprops=dict(arrowstyle="-|>", color=ORANGE, lw=1.4, shrinkA=4, shrinkB=4))
        ax.scatter(w1, y + 0.16, marker="o", s=60, facecolor="white", edgecolor=ORANGE, linewidths=1.6, zorder=3)
        ax.scatter(w2, y + 0.16, marker="o", s=60, color=ORANGE, zorder=4)
        ax.scatter(b, y - 0.16, marker="o", s=60, color=BLUE, zorder=3)
        ax.text(101, y + 0.16, f"{sum(c['with-server v0.1.1'])}/18 → {sum(c['with-server v0.1.2'])}/18",
                va="center", fontsize=7, color=INK)
        ax.text(101, y - 0.16, f"{sum(c['baseline'])}/18", va="center", fontsize=7, color=INK)
    ax.set_yticks(ys)
    ax.set_yticklabels([f"{m}  ({label[h]})" for h, m in order], fontsize=7.5)
    ax.set_xlim(60, 100)
    ax.set_xlabel("pass rate (%), 6 tasks × 3 repeats", fontsize=8)
    ax.tick_params(axis="x", labelsize=8)
    ax.grid(axis="x", color="#e5e5e5", linewidth=0.6)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    handles = [
        Line2D([], [], marker="o", linestyle="", color=BLUE, markersize=7, label="Fortran source + shell, no server"),
        Line2D([], [], marker="o", linestyle="", markerfacecolor="white", markeredgecolor=ORANGE,
               markeredgewidth=1.6, markersize=7, label="with the server, v0.1.1"),
        Line2D([], [], marker="o", linestyle="", color=ORANGE, markersize=7, label="with the server, v0.1.2"),
    ]
    ax.legend(handles=handles, fontsize=7, frameon=False, loc="upper center", bbox_to_anchor=(0.45, -0.22), ncol=2)
    fig.tight_layout()
    fig.savefig(d / "leg_e" / "figure_leg_e.pdf")
    fig.savefig(d / "leg_e" / "figure_leg_e.png", dpi=200)
    print("wrote", d / "leg_e" / "figure_leg_e.*")


if __name__ == "__main__":
    d = Path(sys.argv[1])
    pooled_bars(d)
    pooled_bars(d, compact=True)
    leg_e(d)
