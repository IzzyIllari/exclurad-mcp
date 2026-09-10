"""Report for leg E (end-to-end) runs, one or several run directories.

    python3 benchmarks/report_leg_e.py --out <dir> <run-dir> [<run-dir> ...]

Per (harness, model, condition): pass rate with Wilson 95% CI, well-posed
and trap counts, median wall time, list-price cost where the harness records
one, and a failure taxonomy specific to running the code:

    no outcome (timeout / turn cap)      wrong beam energy assumed
    wrong radtot column                  NaN passed through as a number
    refused a runnable point             ran a point below threshold
    delta off, no matching run on disk   other

"wrong beam energy" is detected from the conversation itself: the beam_gev
the agent passed to generate_input (with-server) or wrote into input.dat
(baseline), compared with the suite default of 6.53 GeV.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from report_leg_d import fmt_ci, wilson, write_csv  # noqa: E402
from report_leg_d_combined import HARNESS_LABEL, short_model  # noqa: E402

BEAM_DEFAULT = 6.53
CONDITIONS = ("with-server", "baseline")


def beam_used(d: Path, harness: str, condition: str) -> float | None:
    """Beam energy the agent actually used, if it can be recovered."""
    t = d / "transcript.jsonl"
    if condition == "with-server" and t.exists():
        for line in t.read_text().splitlines():
            if "generate_input" not in line or "beam_gev" not in line:
                continue
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                continue
            found: list[float] = []

            def grab(o):
                if isinstance(o, dict):
                    if "beam_gev" in o and isinstance(o["beam_gev"], (int, float)):
                        found.append(float(o["beam_gev"]))
                    for v in o.values():
                        grab(v)
                elif isinstance(o, list):
                    for v in o:
                        grab(v)
            grab(ev)
            if found:
                return found[-1]
        return None
    # baseline: the input.dat the executable read (third line is bmom)
    for cand in sorted(d.rglob("input*.dat")):
        try:
            lines = cand.read_text().splitlines()
            return float(lines[2].split()[0])
        except (OSError, IndexError, ValueError):
            continue
    return None


def classify(problems: str, beam: float | None, notes: str) -> str:
    if "no outcome.json" in problems:
        return "no outcome (timeout / turn cap)"
    if beam is not None and abs(beam - BEAM_DEFAULT) > 1e-3:
        # a wrong beam energy explains a wrong number AND a finite delta at
        # the NaN-trap point (the NaN is specific to 6.53 GeV)
        return f"wrong beam energy assumed ({beam:g} GeV)"
    if "reported a finite delta" in problems:
        return "NaN passed through as a number"
    if "refused a runnable request" in problems:
        return "refused a runnable point"
    if "direction: expected refuse" in problems or "below threshold" in problems:
        return "ran a point below threshold"
    if "sigma_born" in problems and "delta" not in problems:
        return "wrong radtot column (sigma_born)"
    if "delta" in problems and "vs reference" in problems:
        return "delta off (no matching run on disk)" if "delta missing" not in problems else "delta missing"
    if "not reported" in problems:
        return "requested point not reported"
    return "other: " + problems[:50]


def load(run: Path) -> list[dict]:
    prov = json.loads((run / "provenance.json").read_text())
    harness = prov.get("harness", "claude")
    server = (prov.get("server_installed") or {}).get("version", "?")
    rows = []
    for m in prov["models"]:
        for c in prov["conditions"]:
            for rep_dir in sorted((run / m / c).glob("rep*")):
                sc = rep_dir / "scores.json"
                if not sc.exists():
                    continue
                for t in json.loads(sc.read_text())["tasks"]:
                    d = rep_dir / t["id"]
                    res = json.loads((d / "result.json").read_text()) if (d / "result.json").exists() else {}
                    r = res.get("result") or {}
                    problems = "; ".join(t["problems"])
                    beam = beam_used(d, harness, c) if not t["passed"] else None
                    rows.append({
                        "harness": harness, "model": m, "model_short": short_model(m),
                        "server": server, "condition": c, "rep": int(rep_dir.name[3:]),
                        "task": t["id"], "class": t["class"], "passed": int(t["passed"]),
                        "problems": problems, "notes": "; ".join(t.get("notes") or []),
                        "run_evidence": int(bool(t.get("run_evidence"))),
                        "mode": "" if t["passed"] else classify(problems, beam, ""),
                        "cost_usd": r.get("total_cost_usd"), "num_turns": r.get("num_turns"),
                        "wall_s": res.get("wall_seconds"), "timed_out": int(bool(res.get("timed_out"))),
                        "tool_calls": json.dumps(res.get("tool_calls", {}), sort_keys=True),
                        "run": run.name,
                    })
    return rows


def summarise(rows: list[dict]) -> list[dict]:
    out = []
    keys = sorted({(r["harness"], r["model"], r["condition"]) for r in rows},
                  key=lambda k: (list(HARNESS_LABEL).index(k[0]), k[1], CONDITIONS.index(k[2])))
    for h, m, c in keys:
        sub = [r for r in rows if (r["harness"], r["model"], r["condition"]) == (h, m, c)]
        n, k = len(sub), sum(r["passed"] for r in sub)
        p, lo, hi = wilson(k, n)
        wp = [r for r in sub if r["class"] == "well_posed"]
        tr = [r for r in sub if r["class"] == "trap"]
        walls = [r["wall_s"] for r in sub if r["wall_s"] is not None]
        costs = [r["cost_usd"] for r in sub if r["cost_usd"] is not None]
        out.append({
            "harness": HARNESS_LABEL[h], "model": short_model(m), "condition": c,
            "n": n, "passed": k, "pass_rate": round(p, 4), "ci_lo": round(lo, 4), "ci_hi": round(hi, 4),
            "well_posed": f"{sum(r['passed'] for r in wp)}/{len(wp)}",
            "trap": f"{sum(r['passed'] for r in tr)}/{len(tr)}",
            "nan_trap": f"{sum(r['passed'] for r in tr if r['task'] == 'e2e-05')}/{sum(1 for r in tr if r['task'] == 'e2e-05')}",
            "wall_median_s": round(statistics.median(walls), 0) if walls else None,
            "cost_total_usd": round(sum(costs), 2) if costs else None,
            "timeouts": sum(r["timed_out"] for r in sub),
        })
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("runs", nargs="+", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    for run in args.runs:
        rows.extend(load(run))
    write_csv(args.out / "lege_results.csv", rows)
    summary = summarise(rows)
    write_csv(args.out / "lege_summary.csv", summary)

    md = ["# Leg E (end-to-end) tables", "",
          f"Runs: {', '.join(r.name for r in args.runs)}. {len(rows)} conversations.", "",
          "## Pass rate per harness × model × condition", "",
          "| harness | model | condition | pass rate | well-posed | trap | NaN trap | median wall | cost | timeouts |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for s in summary:
        cost = f"${s['cost_total_usd']:.2f}" if s["cost_total_usd"] is not None else "n/a"
        md.append(f"| {s['harness']} | {s['model']} | {s['condition']} | {fmt_ci(s['passed'], s['n'])} "
                  f"| {s['well_posed']} | {s['trap']} | {s['nan_trap']} | {s['wall_median_s']:.0f} s | {cost} "
                  f"| {s['timeouts']} |")
    md += ["", "## Pooled", "", "| condition | n | pass rate | well-posed | trap |", "|---|---|---|---|---|"]
    for c in CONDITIONS:
        sub = [r for r in rows if r["condition"] == c]
        wp = [r for r in sub if r["class"] == "well_posed"]
        tr = [r for r in sub if r["class"] == "trap"]
        md.append(f"| {c} | {len(sub)} | {fmt_ci(sum(r['passed'] for r in sub), len(sub))} "
                  f"| {sum(r['passed'] for r in wp)}/{len(wp)} | {sum(r['passed'] for r in tr)}/{len(tr)} |")
    tax = Counter((r["condition"], r["mode"]) for r in rows if not r["passed"])
    md += ["", "## Failure taxonomy", "", "| condition | failure mode | n |", "|---|---|---|"]
    for (c, mode), n in sorted(tax.items(), key=lambda x: (x[0][0], -x[1])):
        md.append(f"| {c} | {mode} | {n} |")
    md += ["", "## Every failure", "", "| harness | model | condition | rep | task | mode | scorer |",
           "|---|---|---|---|---|---|---|"]
    for r in rows:
        if not r["passed"]:
            md.append(f"| {HARNESS_LABEL[r['harness']]} | {r['model_short']} | {r['condition']} | {r['rep']} "
                      f"| {r['task']} | {r['mode']} | {r['problems'][:90]} |")
    (args.out / "tables.md").write_text("\n".join(md) + "\n")
    print(f"wrote {args.out}: {len(rows)} rows, {len(summary)} cells")


if __name__ == "__main__":
    main()
