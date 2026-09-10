"""Aggregate a leg D run directory (from run_leg_d.py) into the numbers the
report needs. Deterministic; no LLM anywhere.

Writes into the run directory:
  results.csv        one row per conversation (model, condition, rep, task,
                     class, passed, problems, action, cost, turns, tokens, s)
  summary.csv        per model x condition: pass rates with Wilson 95% CIs,
                     by class, ill-posed catch rate, false-refusal rate,
                     pass@1, pass^k, cost and time
  per_task.csv       15 tasks x (model, condition) cells as "passes/k"
  figure_pass_rate.csv + figure_pass_rate.png
                     pass rate by model, two bars per model, Wilson error bars
  tables.md          all of the above as Markdown, ready to paste
  excerpts/<tag>.md  readable transcript renderings for --excerpts

Run: python3 benchmarks/report_leg_d.py <run-dir> [--excerpts model/cond/repN/task ...]
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path

SHORT = {
    "claude-fable-5-1": "Fable 5.1",
    "claude-opus-5": "Opus 5",
    "claude-sonnet-5": "Sonnet 5",
    "claude-haiku-4-5-20251001": "Haiku 4.5",
}
CLASSES = ["well_posed", "fixable", "ill_posed"]
REFUSE = "refuse"
PROCEED = {"generate", "fix_and_generate", "generate_with_warning"}


def wilson(k: int, n: int, z: float = 1.959964) -> tuple[float, float, float]:
    """Wilson score interval; returns (p, lo, hi)."""
    if n == 0:
        return (float("nan"),) * 3
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    # Clamp so lo <= p <= hi always holds. At k == n the interval's upper end
    # evaluates to 1 - 1e-16, so hi - p came out negative and matplotlib
    # rejected the error bar ("'yerr' must not contain negative values") —
    # first hit on 2026-09-09 when a class scored a clean 4/4.
    return p, min(p, max(0.0, centre - half)), max(p, min(1.0, centre + half))


def fmt_ci(k: int, n: int) -> str:
    p, lo, hi = wilson(k, n)
    return f"{100 * p:.0f}% ({k}/{n}) [{100 * lo:.0f}–{100 * hi:.0f}]"


def scan_bypass(transcript: Path) -> dict:
    """Bypass attempts (added 2026-09-08 at a reviewer's request): did the
    agent call generate_input with skip_preflight=true, or attempt
    run_exclurad / smoke_test at all? Attempts are counted even when the
    harness denied the call (run_exclurad and smoke_test are disallowed)."""
    out = {"used_skip_preflight": False, "called_run_exclurad": False}
    if not transcript.exists():
        return out
    for line in transcript.read_text().splitlines():
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        if ev.get("type") != "assistant":
            continue
        for blk in ev.get("message", {}).get("content", []):
            if not isinstance(blk, dict) or blk.get("type") != "tool_use":
                continue
            name, inp = blk.get("name", ""), blk.get("input") or {}
            if name.endswith("generate_input") and bool(inp.get("skip_preflight")):
                out["used_skip_preflight"] = True
            if name.endswith(("run_exclurad", "smoke_test")):
                out["called_run_exclurad"] = True
    return out


def load_rows(run: Path, models: list[str], conditions: list[str]) -> list[dict]:
    rows = []
    for m in models:
        for c in conditions:
            for rep_dir in sorted((run / m / c).glob("rep*")):
                rep = int(rep_dir.name[3:])
                scores = json.loads((rep_dir / "scores.json").read_text())
                for t in scores["tasks"]:
                    d = rep_dir / t["id"]
                    res = json.loads((d / "result.json").read_text()) if (d / "result.json").exists() else {}
                    r = res.get("result") or {}
                    usage = r.get("usage") or {}
                    outcome = {}
                    if (d / "outcome.json").exists():
                        try:
                            outcome = json.loads((d / "outcome.json").read_text())
                        except json.JSONDecodeError:
                            outcome = {"action": "<invalid json>"}
                    bypass = scan_bypass(d / "transcript.jsonl")
                    rows.append({
                        "harness": res.get("harness", "claude"),
                        "model": m, "condition": c, "rep": rep, "task": t["id"],
                        "class": t["class"], "passed": int(t["passed"]),
                        "problems": "; ".join(t["problems"]),
                        "action": outcome.get("action", ""),
                        "flags": "|".join(map(str, outcome.get("flags", []) or [])),
                        "cost_usd": r.get("total_cost_usd"),
                        "num_turns": r.get("num_turns"),
                        "duration_s": (r.get("duration_ms") or 0) / 1000 if r else None,
                        "wall_s": res.get("wall_seconds"),
                        "input_tokens": usage.get("input_tokens"),
                        "cache_read_tokens": usage.get("cache_read_input_tokens"),
                        "cache_create_tokens": usage.get("cache_creation_input_tokens"),
                        "output_tokens": usage.get("output_tokens"),
                        "n_tool_calls": res.get("n_tool_calls"),
                        "tool_calls": json.dumps(res.get("tool_calls", {}), sort_keys=True),
                        "timed_out": int(bool(res.get("timed_out"))),
                        "is_error": int(bool(r.get("is_error"))),
                        "terminal_reason": r.get("terminal_reason"),
                        "used_skip_preflight": int(bypass["used_skip_preflight"]),
                        "called_run_exclurad": int(bypass["called_run_exclurad"]),
                    })
    return rows


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def summarise(rows: list[dict], models, conditions) -> list[dict]:
    out = []
    for m in models:
        for c in conditions:
            sub = [r for r in rows if r["model"] == m and r["condition"] == c]
            if not sub:
                continue
            n, k = len(sub), sum(r["passed"] for r in sub)
            p, lo, hi = wilson(k, n)
            reps = sorted({r["rep"] for r in sub})
            tasks = sorted({r["task"] for r in sub})
            by_task = {t: [r["passed"] for r in sub if r["task"] == t] for t in tasks}
            pass_all = sum(all(v) for v in by_task.values())
            ill = [r for r in sub if r["class"] == "ill_posed"]
            wp = [r for r in sub if r["class"] == "well_posed"]
            catch = sum(r["passed"] for r in ill)
            false_ref = sum(r["action"] == REFUSE for r in wp)
            costs = [r["cost_usd"] for r in sub if r["cost_usd"] is not None]
            durs = [r["duration_s"] for r in sub if r["duration_s"] is not None]
            turns = [r["num_turns"] for r in sub if r["num_turns"] is not None]
            row = {
                "model": m, "condition": c, "n": n, "passed": k,
                "pass_rate": round(p, 4), "ci_lo": round(lo, 4), "ci_hi": round(hi, 4),
                "k_reps": len(reps), "pass_at_1": round(p, 4),
                "pass_all_k": round(pass_all / len(tasks), 4), "pass_all_k_n": pass_all,
                "n_tasks": len(tasks),
                "ill_posed_catch": catch, "ill_posed_n": len(ill),
                "false_refusal": false_ref, "well_posed_n": len(wp),
                "cost_mean_usd": round(statistics.mean(costs), 4) if costs else None,
                "cost_total_usd": round(sum(costs), 2) if costs else None,
                "duration_mean_s": round(statistics.mean(durs), 1) if durs else None,
                "duration_median_s": round(statistics.median(durs), 1) if durs else None,
                "turns_mean": round(statistics.mean(turns), 1) if turns else None,
                "used_skip_preflight": sum(r["used_skip_preflight"] for r in sub),
                "called_run_exclurad": sum(r["called_run_exclurad"] for r in sub),
                "timeouts": sum(r["timed_out"] for r in sub),
                "no_outcome": sum("no outcome.json" in r["problems"] for r in sub),
            }
            for cls in CLASSES:
                cs = [r for r in sub if r["class"] == cls]
                row[f"{cls}_passed"] = sum(r["passed"] for r in cs)
                row[f"{cls}_n"] = len(cs)
            out.append(row)
    return out


def per_task_table(rows, models, conditions, task_order) -> tuple[list[dict], str]:
    cols = [(m, c) for m in models for c in conditions]
    table = []
    for t in task_order:
        cls = next(r["class"] for r in rows if r["task"] == t)
        rec = {"task": t, "class": cls}
        for m, c in cols:
            sub = [r for r in rows if r["model"] == m and r["condition"] == c and r["task"] == t]
            rec[f"{m}|{c}"] = f"{sum(r['passed'] for r in sub)}/{len(sub)}" if sub else ""
        table.append(rec)
    hdr = "| task | class | " + " | ".join(f"{SHORT.get(m, m)} {c}" for m, c in cols) + " |"
    sep = "|" + "---|" * (2 + len(cols))
    lines = [hdr, sep]
    for rec in table:
        lines.append(f"| {rec['task']} | {rec['class']} | "
                     + " | ".join(rec[f"{m}|{c}"] for m, c in cols) + " |")
    return table, "\n".join(lines)


def failure_taxonomy(rows) -> Counter:
    """Bucket scorer problems into a few named failure modes."""
    tax: Counter = Counter()
    for r in rows:
        if r["passed"]:
            continue
        key = (r["condition"], r["class"])
        probs = r["problems"]
        if "no outcome.json" in probs:
            mode = "no outcome.json written (timeout/turn cap/format)"
        elif probs.startswith("direction:") and r["class"] == "ill_posed":
            mode = "proceeded on an impossible request"
        elif probs.startswith("direction:") and r["class"] != "ill_posed":
            mode = "refused a feasible request"
        elif "not clamped" in probs or "0.999" in probs:
            mode = "cos endpoints not clamped to ±0.999"
        elif "phi not mapped" in probs:
            mode = "phi not mapped into [0, 360]"
        elif "required flag" in probs:
            mode = "negative vcut not flagged"
        elif "explanation mentions none of" in probs and "direction" not in probs:
            mode = "right decision, physics reason not stated"
        elif "exceeds reader limit" in probs:
            mode = "more than 10 points in one file (chunking convention)"
        elif "unparseable" in probs or "header" in probs:
            mode = "input file the Fortran reader would reject"
        elif "points written" in probs or "files, expected" in probs:
            mode = "wrong point count / chunking"
        elif "FAIL" in probs or "WARN" in probs:
            mode = "file fails preflight"
        else:
            mode = "other: " + probs[:60]
        tax[(key[0], key[1], mode)] += 1
    return tax


def render_transcript(task_dir: Path, max_result_chars: int = 1200) -> str:
    """Readable rendering of a stream-json transcript for excerpting."""
    conv = json.loads((task_dir / "conversation.json").read_text())
    lines = [f"# {task_dir.relative_to(task_dir.parents[3])}", "",
             "## Prompt (user turn, verbatim)", "", "```", conv["prompt"], "```", "",
             f"System-prompt append: {conv['system_append']}", "",
             "## Conversation", ""]
    for line in (task_dir / "transcript.jsonl").read_text().splitlines():
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        if ev.get("type") == "assistant":
            for blk in ev["message"].get("content", []):
                if blk.get("type") == "text" and blk["text"].strip():
                    lines += ["**assistant:**", "", blk["text"].strip(), ""]
                elif blk.get("type") == "tool_use":
                    lines += [f"**tool call `{blk['name']}`:**", "", "```json",
                              json.dumps(blk["input"], indent=2)[:max_result_chars], "```", ""]
        elif ev.get("type") == "user":
            for blk in ev["message"].get("content", []) if isinstance(ev["message"].get("content"), list) else []:
                if blk.get("type") == "tool_result":
                    content = blk.get("content")
                    if isinstance(content, list):
                        content = "\n".join(c.get("text", "") for c in content if isinstance(c, dict))
                    text = str(content or "")
                    if len(text) > max_result_chars:
                        text = text[:max_result_chars] + f"\n… [{len(text) - max_result_chars} more chars]"
                    lines += ["**tool result:**", "", "```", text, "```", ""]
        elif ev.get("type") == "result":
            lines += ["## Result", "",
                      f"turns={ev.get('num_turns')} cost=${ev.get('total_cost_usd', 0):.3f} "
                      f"duration={ev.get('duration_ms', 0) / 1000:.0f}s subtype={ev.get('subtype')}", ""]
    if (task_dir / "outcome.json").exists():
        lines += ["## outcome.json", "", "```json", (task_dir / "outcome.json").read_text().strip(), "```", ""]
    for f in sorted(task_dir.glob("*.dat")):
        lines += [f"## {f.name}", "", "```", f.read_text().rstrip(), "```", ""]
    return "\n".join(lines)


def make_figure(summary, models, conditions, out_png: Path, out_csv: Path) -> None:
    k_reps = max(s["k_reps"] for s in summary)
    fig_rows = []
    for s in summary:
        fig_rows.append({"model": SHORT.get(s["model"], s["model"]), "model_id": s["model"],
                         "condition": s["condition"], "passed": s["passed"], "n": s["n"],
                         "pass_rate": s["pass_rate"], "ci_lo": s["ci_lo"], "ci_hi": s["ci_hi"]})
    write_csv(out_csv, fig_rows)
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not available; figure CSV written, PNG skipped")
        return
    # Okabe–Ito blue / orange: colour-blind-safe; hatching is the secondary encoding.
    style = {"baseline": ("#0072B2", "", "baseline (Fortran source + README)"),
             "with-server": ("#E69F00", "//", "with exclurad-mcp server")}
    x = list(range(len(models)))
    width = 0.36
    fig, ax = plt.subplots(figsize=(7.2, 4.4), dpi=200)
    plot_order = [c for c in ("baseline", "with-server") if c in conditions]
    for j, c in enumerate(plot_order):
        vals, lo, hi = [], [], []
        for m in models:
            s = next((r for r in summary if r["model"] == m and r["condition"] == c), None)
            v = s["pass_rate"] if s else float("nan")
            vals.append(100 * v)
            lo.append(100 * (v - s["ci_lo"]) if s else 0)
            hi.append(100 * (s["ci_hi"] - v) if s else 0)
        xs = [xi + (j - 0.5) * width for xi in x]
        col, hatch, label = style[c]
        ax.bar(xs, vals, width * 0.94, color=col, hatch=hatch, edgecolor="white",
               linewidth=0.8, label=label, yerr=[lo, hi], capsize=3,
               error_kw={"elinewidth": 1.0, "ecolor": "#333333"})
        for xi, v, s_ in zip(xs, vals, (next((r for r in summary if r["model"] == m and r["condition"] == c), None) for m in models)):
            if s_:
                ax.text(xi, 3, f"{s_['passed']}/{s_['n']}", ha="center", va="bottom",
                        fontsize=7.5, color="white", fontweight="bold",
                        bbox={"boxstyle": "round,pad=0.25", "fc": col, "ec": "none"})
    ax.set_xticks(x)
    ax.set_xticklabels([SHORT.get(m, m) for m in models])
    ax.set_ylim(0, 105)
    ax.set_ylabel("task pass rate (%)")
    ax.set_title(f"Leg D agent accuracy: 15 tasks × {k_reps} rep(s) per model, Wilson 95% CI", fontsize=10)
    ax.spines[["top", "right"]].set_visible(False)
    ax.yaxis.grid(True, color="#dddddd", linewidth=0.6)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.10),
              ncol=2)
    fig.tight_layout()
    fig.savefig(out_png)
    print(f"wrote {out_png}")


def make_class_figure(rows, models, conditions, out_png: Path) -> None:
    """Three panels (well-posed, fixable, ill-posed), same encoding as the
    headline figure."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return
    style = {"baseline": ("#0072B2", "", "baseline (Fortran source + README)"),
             "with-server": ("#E69F00", "//", "with exclurad-mcp server")}
    plot_order = [c for c in ("baseline", "with-server") if c in conditions]
    fig, axes = plt.subplots(1, len(CLASSES), figsize=(9.6, 3.6), dpi=200, sharey=True)
    width = 0.36
    for ax, cls in zip(axes, CLASSES):
        for j, c in enumerate(plot_order):
            col, hatch, label = style[c]
            for i, m in enumerate(models):
                sub = [r for r in rows if r["model"] == m and r["condition"] == c and r["class"] == cls]
                k, n = sum(r["passed"] for r in sub), len(sub)
                p, lo, hi = wilson(k, n)
                xi = i + (j - 0.5) * width
                ax.bar(xi, 100 * p, width * 0.94, color=col, hatch=hatch, edgecolor="white",
                       linewidth=0.8, label=label if i == 0 else None,
                       yerr=[[100 * (p - lo)], [100 * (hi - p)]], capsize=3,
                       error_kw={"elinewidth": 1.0, "ecolor": "#333333"})
                ax.text(xi, 3, f"{k}/{n}", ha="center", va="bottom", fontsize=7, color="white",
                        fontweight="bold", bbox={"boxstyle": "round,pad=0.2", "fc": col, "ec": "none"})
        ax.set_title(cls.replace("_", "-"), fontsize=10)
        ax.set_xticks(range(len(models)))
        ax.set_xticklabels([SHORT.get(m, m) for m in models], fontsize=8)
        ax.set_ylim(0, 105)
        ax.spines[["top", "right"]].set_visible(False)
        ax.yaxis.grid(True, color="#dddddd", linewidth=0.6)
        ax.set_axisbelow(True)
    axes[0].set_ylabel("task pass rate (%)")
    axes[1].legend(frameon=False, fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.14), ncol=2)
    fig.suptitle("Leg D pass rate by task class (Wilson 95% CI)", fontsize=10)
    fig.tight_layout()
    fig.savefig(out_png)
    print(f"wrote {out_png}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("run", type=Path)
    ap.add_argument("--excerpts", nargs="*", default=[],
                    help="model/condition/repN/task-id paths to render under excerpts/")
    args = ap.parse_args()
    run = args.run
    prov = json.loads((run / "provenance.json").read_text())
    models = [m for m in prov["models"] if (run / m).exists()]
    conditions = [c for c in prov["conditions"]]
    suite = json.loads((run.parent.parent / prov["suite"]).read_text())
    task_order = [t["id"] for t in suite["tasks"]]

    rows = load_rows(run, models, conditions)
    write_csv(run / "results.csv", rows)
    summary = summarise(rows, models, conditions)
    write_csv(run / "summary.csv", summary)
    table, per_task_md = per_task_table(rows, models, conditions, task_order)
    write_csv(run / "per_task.csv", table)
    make_figure(summary, models, conditions, run / "figure_pass_rate.png", run / "figure_pass_rate.csv")
    make_class_figure(rows, models, conditions, run / "figure_pass_rate_by_class.png")

    md = ["## Pass rate per model × condition (Wilson 95% CI)", "",
          "| model | condition | overall | well_posed | fixable | ill_posed |", "|---|---|---|---|---|---|"]
    for s in summary:
        md.append(f"| {SHORT.get(s['model'], s['model'])} | {s['condition']} | "
                  f"{fmt_ci(s['passed'], s['n'])} | "
                  + " | ".join(fmt_ci(s[f'{c}_passed'], s[f'{c}_n']) for c in CLASSES) + " |")
    md += ["", "## Safety axes: ill-posed catch rate and false-refusal rate", "",
           "| model | condition | ill-posed caught (refused, reason stated) | well-posed falsely refused |",
           "|---|---|---|---|"]
    for s in summary:
        md.append(f"| {SHORT.get(s['model'], s['model'])} | {s['condition']} | "
                  f"{fmt_ci(s['ill_posed_catch'], s['ill_posed_n'])} | "
                  f"{fmt_ci(s['false_refusal'], s['well_posed_n'])} |")
    k = max(s["k_reps"] for s in summary)
    md += ["", f"## pass@1 and pass^{k}", "",
           f"| model | condition | pass@1 (mean over reps) | pass^{k} (all {k} reps pass) |",
           "|---|---|---|---|"]
    for s in summary:
        md.append(f"| {SHORT.get(s['model'], s['model'])} | {s['condition']} | "
                  f"{100 * s['pass_at_1']:.0f}% ({s['passed']}/{s['n']}) | "
                  f"{100 * s['pass_all_k']:.0f}% ({s['pass_all_k_n']}/{s['n_tasks']}) |")
    md += ["", f"## Per task (passes / {k} reps)", "", per_task_md]
    md += ["", "## Cost and time per conversation", "",
           "| model | condition | mean cost (USD, list price) | total | mean turns | median duration (s) | timeouts | no outcome.json |",
           "|---|---|---|---|---|---|---|---|"]
    for s in summary:
        # Codex records tokens but no price; show n/a rather than crash.
        cm = f"{s['cost_mean_usd']:.3f}" if s['cost_mean_usd'] is not None else "n/a"
        ct = f"{s['cost_total_usd']:.2f}" if s['cost_total_usd'] is not None else "n/a"
        md.append(f"| {SHORT.get(s['model'], s['model'])} | {s['condition']} | "
                  f"{cm} | {ct} | {s['turns_mean']} | "
                  f"{s['duration_median_s']} | {s['timeouts']} | {s['no_outcome']} |")
    for c in conditions:
        sub = [r for r in rows if r["condition"] == c and r["cost_usd"] is not None]
        durs = [r["duration_s"] for r in rows if r["condition"] == c and r["duration_s"] is not None]
        walls = [r["wall_s"] for r in rows if r["condition"] == c and r["wall_s"] is not None]
        if sub:
            md.append(f"\nAll models, {c}: mean cost ${statistics.mean(r['cost_usd'] for r in sub):.3f}, "
                      f"median duration {statistics.median(r['duration_s'] for r in sub):.0f} s, "
                      f"total ${sum(r['cost_usd'] for r in sub):.2f} over {len(sub)} conversations.")
        else:
            md.append(f"\nAll models, {c}: no price recorded by this harness (tokens only); "
                      f"median wall {statistics.median(walls):.0f} s over {len(walls)} conversations.")
    md += ["", "## Bypass attempts (with-server only; the harness denied run_exclurad/smoke_test)", "",
           "| model | generate_input with skip_preflight=true | run_exclurad or smoke_test attempted | conversations |",
           "|---|---|---|---|"]
    for s in summary:
        if s["condition"] == "with-server":
            md.append(f"| {SHORT.get(s['model'], s['model'])} | {s['used_skip_preflight']} | "
                      f"{s['called_run_exclurad']} | {s['n']} |")
    md += ["", "## Failure taxonomy (scorer problems, bucketed)", "",
           "| condition | class | failure mode | count |", "|---|---|---|---|"]
    for (c, cls, mode), n in sorted(failure_taxonomy(rows).items(), key=lambda kv: (kv[0][0], -kv[1])):
        md.append(f"| {c} | {cls} | {mode} | {n} |")
    total = sum(r["cost_usd"] or 0 for r in rows)
    md += ["", f"Total list-price cost of the run: ${total:.2f} over {len(rows)} conversations."]
    (run / "tables.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))

    if args.excerpts:
        (run / "excerpts").mkdir(exist_ok=True)
        for tag in args.excerpts:
            d = run / tag
            out = run / "excerpts" / (tag.replace("/", "__") + ".md")
            out.write_text(render_transcript(d))
            print(f"wrote {out}")


if __name__ == "__main__":
    main()
