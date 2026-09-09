"""Combine several leg D run directories (different harnesses, models, server
versions) into one cross-harness report.

    python3 benchmarks/report_leg_d_combined.py --out <dir> <run-dir> [<run-dir> ...]

Each run dir is one `run_leg_d.py` output (results.csv, provenance.json,
per-conversation dirs). Rows are re-read from the conversation dirs via
`report_leg_d.load_rows`, then tagged with the harness, the server version the
cell ran on (from provenance `server_installed`, or inferred as 0.1.0 for runs
that predate that field), and the run dir.

Outputs in --out:
  combined_results.csv   every conversation, one row, with harness/server/run
  combined_summary.csv   one row per (harness, model, server, condition)
  tables.md              markdown tables for the report
  figure_combined.png/.csv   pass rate per (harness, model) cell, both
                             conditions, Wilson 95% CIs, grouped by harness
  taxonomy.csv           failure modes, with the "outcome emitted as chat text"
                         bucket split out of "no outcome.json"

Cells that exist on more than one server version (the Claude Code with-server
cells were rerun on v0.1.1) are all kept in combined_results.csv; the headline
tables use the newest server version per cell and a separate before/after
table shows the rest.
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from report_leg_d import (CLASSES, REFUSE, failure_taxonomy, fmt_ci,  # noqa: E402
                          load_rows, summarise, wilson, write_csv)

HARNESS_LABEL = {"claude": "Claude Code", "opencode": "OpenCode", "codex": "Codex"}
CONDITIONS = ("with-server", "baseline")


def short_model(model: str) -> str:
    m = model.split("/")[-1]
    for pre in ("aws-gov.", "aws.", "darwin."):
        if m.startswith(pre):
            m = m[len(pre):]
    m = m.replace("claude-haiku-4-5-20251001", "claude-haiku-4.5")
    return m


def server_version(prov: dict) -> str:
    inst = prov.get("server_installed") or {}
    if inst.get("version"):
        return inst["version"]
    return "0.1.0"  # runs before 590457d recorded no server version


def version_key(v: str) -> tuple:
    return tuple(int(x) if x.isdigit() else 0 for x in v.split("."))


def chat_text_outcome(task_dir: Path) -> bool:
    """No outcome.json, but the final assistant text carries the outcome JSON
    (gpt-oss-120b did this in 40% of its conversations)."""
    if (task_dir / "outcome.json").exists():
        return False
    res = task_dir / "result.json"
    if not res.exists():
        return False
    try:
        text = json.loads(res.read_text()).get("final_text") or ""
    except (json.JSONDecodeError, OSError):
        return False
    return '"action"' in text and ('"explanation"' in text or '"input_files"' in text)


def load_run(run: Path) -> list[dict]:
    prov = json.loads((run / "provenance.json").read_text())
    harness = prov.get("harness", "claude")
    server = server_version(prov)
    models = [m for m in prov["models"] if (run / m).exists()]
    conditions = [c for c in prov["conditions"] if any((run / m / c).exists() for m in models)]
    rows = load_rows(run, models, conditions)
    for r in rows:
        r["harness"] = harness
        r["server"] = server
        r["run"] = run.name
        r["model_short"] = short_model(r["model"])
        d = run / r["model"] / r["condition"] / f"rep{r['rep']}" / r["task"]
        r["chat_text_outcome"] = int(chat_text_outcome(d))
    return rows


def newest_server_per_cell(rows: list[dict]) -> tuple[list[dict], list[dict]]:
    """Split rows into (headline, superseded): for each (harness, model,
    condition) keep the newest server version as headline."""
    newest: dict[tuple, str] = {}
    for r in rows:
        key = (r["harness"], r["model"], r["condition"])
        if key not in newest or version_key(r["server"]) > version_key(newest[key]):
            newest[key] = r["server"]
    head = [r for r in rows if r["server"] == newest[(r["harness"], r["model"], r["condition"])]]
    old = [r for r in rows if r not in head]
    return head, old


def cell_summary(rows: list[dict]) -> list[dict]:
    out = []
    cells = sorted({(r["harness"], r["model"], r["server"]) for r in rows},
                   key=lambda k: (list(HARNESS_LABEL).index(k[0]), k[1], k[2]))
    for h, m, s in cells:
        sub_all = [r for r in rows if r["harness"] == h and r["model"] == m and r["server"] == s]
        for row in summarise(sub_all, [m], list(CONDITIONS)):
            sub = [r for r in sub_all if r["condition"] == row["condition"]]
            walls = [r["wall_s"] for r in sub if r["wall_s"] is not None]
            row.update({
                "harness": h, "harness_label": HARNESS_LABEL[h], "server": s,
                "model_short": short_model(m),
                "wall_median_s": round(statistics.median(walls), 1) if walls else None,
                "chat_text_outcome": sum(r["chat_text_outcome"] for r in sub),
                "run": sorted({r["run"] for r in sub})[0],
            })
            out.append(row)
    return out


def pct(k, n):
    return f"{100 * k / n:.0f}%" if n else "-"


def main_table(summary: list[dict]) -> str:
    by = {(s["harness"], s["model"], s["server"], s["condition"]): s for s in summary}
    cells = sorted({(s["harness"], s["model"], s["server"]) for s in summary},
                   key=lambda k: (list(HARNESS_LABEL).index(k[0]),
                                  -by.get((k[0], k[1], k[2], "with-server"), {}).get("pass_rate", 0)))
    lines = ["| harness | model | server | with-server | baseline | Δ | pass^k with / base | "
             "ill-posed catch with / base | false refusal with / base | median wall with / base |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for h, m, s in cells:
        w, b = by.get((h, m, s, "with-server")), by.get((h, m, s, "baseline"))
        if not (w and b):
            continue
        delta = 100 * (w["pass_rate"] - b["pass_rate"])
        lines.append(
            f"| {HARNESS_LABEL[h]} | {short_model(m)} | v{s} "
            f"| {fmt_ci(w['passed'], w['n'])} | {fmt_ci(b['passed'], b['n'])} | {delta:+.0f} pp "
            f"| {pct(w['pass_all_k_n'], w['n_tasks'])} / {pct(b['pass_all_k_n'], b['n_tasks'])} "
            f"| {w['ill_posed_catch']}/{w['ill_posed_n']} / {b['ill_posed_catch']}/{b['ill_posed_n']} "
            f"| {w['false_refusal']}/{w['well_posed_n']} / {b['false_refusal']}/{b['well_posed_n']} "
            f"| {w['wall_median_s']} s / {b['wall_median_s']} s |")
    return "\n".join(lines)


def class_table(rows: list[dict]) -> str:
    lines = ["| harness | model | server | condition | well-posed | fixable | ill-posed |",
             "|---|---|---|---|---|---|---|"]
    cells = sorted({(r["harness"], r["model"], r["server"]) for r in rows},
                   key=lambda k: (list(HARNESS_LABEL).index(k[0]), k[1]))
    for h, m, s in cells:
        for c in CONDITIONS:
            sub = [r for r in rows if (r["harness"], r["model"], r["server"], r["condition"]) == (h, m, s, c)]
            if not sub:
                continue
            parts = []
            for cls in CLASSES:
                cs = [r for r in sub if r["class"] == cls]
                parts.append(f"{sum(r['passed'] for r in cs)}/{len(cs)}")
            lines.append(f"| {HARNESS_LABEL[h]} | {short_model(m)} | v{s} | {c} | " + " | ".join(parts) + " |")
    return "\n".join(lines)


def pooled_table(rows: list[dict]) -> str:
    """Pooled over models within a harness, and over everything."""
    lines = ["| scope | condition | n | pass rate | ill-posed catch | false refusal |",
             "|---|---|---|---|---|---|"]
    scopes = [(HARNESS_LABEL[h], [r for r in rows if r["harness"] == h]) for h in HARNESS_LABEL
              if any(r["harness"] == h for r in rows)]
    scopes.append(("all harnesses, all models", rows))
    for name, sub_all in scopes:
        for c in CONDITIONS:
            sub = [r for r in sub_all if r["condition"] == c]
            if not sub:
                continue
            k, n = sum(r["passed"] for r in sub), len(sub)
            ill = [r for r in sub if r["class"] == "ill_posed"]
            wp = [r for r in sub if r["class"] == "well_posed"]
            lines.append(f"| {name} | {c} | {n} | {fmt_ci(k, n)} "
                         f"| {sum(r['passed'] for r in ill)}/{len(ill)} "
                         f"| {sum(r['action'] == REFUSE for r in wp)}/{len(wp)} |")
    return "\n".join(lines)


def before_after_table(head: list[dict], old: list[dict]) -> str:
    if not old:
        return "_No cell was run on more than one server version._"
    lines = ["| harness | model | condition | server | pass rate | ip-02 | ip-06 |",
             "|---|---|---|---|---|---|---|"]
    keys = sorted({(r["harness"], r["model"], r["condition"]) for r in old})
    for h, m, c in keys:
        for src in (old, head):
            sub = [r for r in src if (r["harness"], r["model"], r["condition"]) == (h, m, c)]
            if not sub:
                continue
            s = sub[0]["server"]
            k, n = sum(r["passed"] for r in sub), len(sub)
            def tk(t):
                ts = [r for r in sub if r["task"] == t]
                return f"{sum(r['passed'] for r in ts)}/{len(ts)}"
            lines.append(f"| {HARNESS_LABEL[h]} | {short_model(m)} | {c} | v{s} "
                         f"| {fmt_ci(k, n)} | {tk('ip-02')} | {tk('ip-06')} |")
    return "\n".join(lines)


def harness_effect_table(head: list[dict]) -> str:
    """Same model under two harnesses."""
    by_model = defaultdict(set)
    for r in head:
        by_model[r["model_short"]].add(r["harness"])
    shared = sorted(m for m, hs in by_model.items() if len(hs) > 1)
    if not shared:
        return "_No model ran under more than one harness._"
    lines = ["| model | harness | with-server | baseline | median wall with / base |",
             "|---|---|---|---|---|"]
    for m in shared:
        for h in HARNESS_LABEL:
            sub = [r for r in head if r["model_short"] == m and r["harness"] == h]
            if not sub:
                continue
            cells = []
            walls = []
            for c in CONDITIONS:
                cs = [r for r in sub if r["condition"] == c]
                cells.append(fmt_ci(sum(r["passed"] for r in cs), len(cs)) if cs else "-")
                ws = [r["wall_s"] for r in cs if r["wall_s"] is not None]
                walls.append(f"{statistics.median(ws):.0f} s" if ws else "-")
            lines.append(f"| {m} | {HARNESS_LABEL[h]} | {cells[0]} | {cells[1]} | {walls[0]} / {walls[1]} |")
    return "\n".join(lines)


NO_OUTCOME = "no outcome.json written (timeout/turn cap/format)"
IMPOSSIBLE = "proceeded on an impossible request"


def taxonomy_rows(rows: list[dict]) -> list[dict]:
    """report_leg_d.failure_taxonomy, then three refinements the cross-vendor
    runs needed: the chat-text delivery failure split out of "no outcome",
    the runner's terminal_reason label attached to "no outcome" rows that
    carry one, and ip-04's sign-convention reinterpretation split out of
    "proceeded on an impossible request" (luna with-server and gpt-5.6-sol
    both read Q2 = -0.5 as signed q^2 and generated at +0.5)."""
    tax = failure_taxonomy(rows)
    split: Counter = Counter()
    for (cond, cls, mode), n in tax.items():
        split[(cond, cls, mode)] = n

    def move(r: dict, src: str, dst: str) -> None:
        key = (r["condition"], r["class"], src)
        if split[key] > 0:
            split[key] -= 1
            split[(r["condition"], r["class"], dst)] += 1

    for r in rows:
        if r["passed"]:
            continue
        probs = r["problems"]
        if "no outcome.json" in probs:
            if r["chat_text_outcome"]:
                move(r, NO_OUTCOME, "outcome emitted as chat text, not written to disk")
            elif r.get("terminal_reason") and r["terminal_reason"] not in ("completed", "success"):
                move(r, NO_OUTCOME, f"no outcome.json: {r['terminal_reason']}")
        elif r["task"] == "ip-04" and probs.startswith("direction:"):
            move(r, IMPOSSIBLE, "reinterpreted Q2 < 0 as a sign convention and proceeded")
    out = [{"condition": c, "class": k, "mode": m, "n": n}
           for (c, k, m), n in split.items() if n > 0]
    out.sort(key=lambda x: (x["condition"], -x["n"], x["class"]))
    return out


def taxonomy_table(tax: list[dict]) -> str:
    lines = ["| condition | class | failure mode | n |", "|---|---|---|---|"]
    for t in tax:
        lines.append(f"| {t['condition']} | {t['class']} | {t['mode']} | {t['n']} |")
    return "\n".join(lines)


def make_figure(summary: list[dict], out_png: Path, out_csv: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    by = {(s["harness"], s["model"], s["server"], s["condition"]): s for s in summary}
    cells = sorted({(s["harness"], s["model"], s["server"]) for s in summary
                    if (s["harness"], s["model"], s["server"], "with-server") in by
                    and (s["harness"], s["model"], s["server"], "baseline") in by},
                   key=lambda k: (list(HARNESS_LABEL).index(k[0]),
                                  by[(k[0], k[1], k[2], "with-server")]["pass_rate"],
                                  by[(k[0], k[1], k[2], "baseline")]["pass_rate"]))
    fig_rows = []
    labels, y = [], []
    fig_h = max(3.0, 0.42 * len(cells) + 1.6)
    fig, ax = plt.subplots(figsize=(7.2, fig_h))
    colour = {"baseline": "#0072B2", "with-server": "#E69F00"}
    off = {"baseline": -0.18, "with-server": +0.18}
    ypos = 0
    last_h = None
    for h, m, s in cells:
        if last_h is not None and h != last_h:
            ypos += 0.6
        last_h = h
        for c in CONDITIONS:
            r = by[(h, m, s, c)]
            p, lo, hi = r["pass_rate"], r["ci_lo"], r["ci_hi"]
            ax.barh(ypos + off[c], 100 * p, height=0.34, color=colour[c],
                    hatch="//" if c == "with-server" else None, edgecolor="white", linewidth=0.8,
                    label=c if (h, m, s) == cells[0] else None)
            ax.errorbar(100 * p, ypos + off[c], xerr=[[100 * (p - lo)], [100 * (hi - p)]],
                        fmt="none", ecolor="#333333", elinewidth=1, capsize=2)
            fig_rows.append({"harness": HARNESS_LABEL[h], "model": short_model(m), "server": s,
                             "condition": c, "n": r["n"], "passed": r["passed"],
                             "pass_rate_pct": round(100 * p, 1),
                             "ci_lo_pct": round(100 * lo, 1), "ci_hi_pct": round(100 * hi, 1)})
        labels.append(f"{short_model(m)}  ({HARNESS_LABEL[h]})")
        y.append(ypos)
        ypos += 1
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=8)
    ax.set_xlim(0, 100)
    ax.set_xlabel("pass rate (%), 15 tasks × k reps, Wilson 95% CI")
    ax.grid(axis="x", color="#dddddd", linewidth=0.6)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=2, fontsize=8, frameon=False)
    ax.set_title("Agent accuracy with and without the EXCLURAD MCP server", fontsize=10)
    fig.tight_layout()
    fig.savefig(out_png, dpi=200)
    write_csv(out_csv, fig_rows)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("runs", nargs="+", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--no-figure", action="store_true")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    rows: list[dict] = []
    for run in args.runs:
        if not (run / "provenance.json").exists():
            sys.exit(f"{run}: no provenance.json")
        rows.extend(load_run(run))
    head, old = newest_server_per_cell(rows)
    write_csv(args.out / "combined_results.csv", rows)
    summary = cell_summary(head)
    write_csv(args.out / "combined_summary.csv", summary)
    tax = taxonomy_rows(head)
    write_csv(args.out / "taxonomy.csv", tax)

    n_cells = len({(r["harness"], r["model"]) for r in head})
    md = [
        "# Leg D combined tables (generated by report_leg_d_combined.py)", "",
        f"Runs: {', '.join(r.name for r in args.runs)}  ",
        f"Conversations: {len(rows)} total, {len(head)} in headline cells "
        f"({n_cells} harness×model cells), {len(old)} superseded by a newer server version.", "",
        "## Headline: per harness × model (newest server version per cell)", "", main_table(summary), "",
        "## Pooled", "", pooled_table(head), "",
        "## By task class", "", class_table(head), "",
        "## Same model, different harness", "", harness_effect_table(head), "",
        "## Server v0.1.0 → v0.1.1 (cells run on both)", "", before_after_table(head, old), "",
        "## Failure taxonomy (headline cells)", "", taxonomy_table(tax), "",
    ]
    (args.out / "tables.md").write_text("\n".join(md))
    if not args.no_figure:
        make_figure(summary, args.out / "figure_combined.png", args.out / "figure_combined.csv")
    print(f"wrote {args.out}: {len(rows)} rows, {len(summary)} summary rows, {len(tax)} taxonomy rows")


if __name__ == "__main__":
    main()
