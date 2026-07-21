"""Benchmark leg C: seeded failure detection (see docs/benchmark-plan.md).

Copies a sample of real chunk files into a scratch tree, seeds known damage
(deleted files, deleted rows, injected NaN in both spellings, truncated
files), then scores whether collect_results/coverage_map detect exactly what
was seeded. Scoring is differential against the pristine sample, so
pre-existing holes in the source tree cannot contaminate the score.

Usage:
  PYTHONPATH=src python3 benchmarks/seeded_failure_detection.py \
      --source /path/to/results_tree --outdir benchmarks/<date>-seeded-failure \
      [--n-files 1500] [--seed 20260721]

No LLM anywhere. The RNG seed is recorded so a run is exactly repeatable.
"""

import argparse
import json
import random
import shutil
import sys
from collections import Counter
from pathlib import Path

from exclurad_mcp.outputs import collect_results

KEY_FIELDS = ("w", "q2", "cos_theta", "phi_deg")


def point_key(rec: dict) -> tuple:
    return tuple(round(rec[f], 4) for f in KEY_FIELDS)


def data_lines(path: Path) -> list[int]:
    """Indices of parseable-looking data lines (non-blank) in a radtot CSV."""
    return [i for i, ln in enumerate(path.read_text().splitlines())
            if ln.strip() and "," in ln]


def file_points(path: Path) -> list[tuple]:
    from exclurad_mcp.outputs import parse_output_file
    parsed = parse_output_file(path, kind="radtot")
    return [point_key(r) for r in parsed["records"]]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True)
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--n-files", type=int, default=1500)
    ap.add_argument("--seed", type=int, default=20260721)
    ap.add_argument("--n-delete-file", type=int, default=40)
    ap.add_argument("--n-delete-row", type=int, default=60)
    ap.add_argument("--n-nan", type=int, default=60)  # half "NaN", half "nan"
    ap.add_argument("--n-truncate", type=int, default=20)
    args = ap.parse_args()

    rng = random.Random(args.seed)
    outdir = Path(args.outdir)
    scratch = outdir / "scratch_tree"
    if scratch.exists():
        shutil.rmtree(scratch)
    scratch.mkdir(parents=True)

    # ---- sample chunk files into a scratch tree (flat: one dir per file) ----
    source = Path(args.source)
    all_files = sorted(f for f in source.rglob("*.dat") if f.parent.name == "radtot")
    if len(all_files) < args.n_files:
        sys.exit(f"source has only {len(all_files)} radtot chunk files")
    sample = rng.sample(all_files, args.n_files)
    copies = []
    for i, f in enumerate(sample):
        d = scratch / f"chunk_{i:05d}" / "radtot"
        d.mkdir(parents=True)
        copies.append(Path(shutil.copy2(f, d / f.name)))

    # ---- pristine baseline ----
    base = collect_results(scratch, kind="radtot")
    base_counts = Counter(point_key(r) for r in base["records"])
    base_nan_points = {point_key(r) for r in base["records"] if r["delta"] != r["delta"]}
    base_problems = {p["file"] for p in base["problems"]}

    # ---- seed damage (disjoint file sets so ground truth stays crisp) ----
    rng.shuffle(copies)
    need = args.n_delete_file + args.n_delete_row + args.n_nan + args.n_truncate
    if need > len(copies):
        sys.exit(f"not enough sampled files ({len(copies)}) for {need} damage sites")
    it = iter(copies)
    take = lambda n: [next(it) for _ in range(n)]
    del_files, delrow_files, nan_files, trunc_files = (
        take(args.n_delete_file), take(args.n_delete_row),
        take(args.n_nan), take(args.n_truncate),
    )

    truth_missing: Counter = Counter()
    truth_nan: set = set()
    truth_trunc_files: set = set()

    for f in del_files:
        for k in file_points(f):
            truth_missing[k] += 1
        f.unlink()

    for f in delrow_files:
        lines = f.read_text().splitlines()
        idxs = data_lines(f)
        drop = rng.choice(idxs)
        pts = file_points(f)
        # data line order == record order for radtot CSV chunks
        truth_missing[pts[idxs.index(drop)]] += 1
        del lines[drop]
        f.write_text("\n".join(lines) + "\n")

    for j, f in enumerate(nan_files):
        lines = f.read_text().splitlines()
        idxs = data_lines(f)
        pts = file_points(f)
        # never seed onto a point that is already NaN in the baseline — the
        # differential score could not attribute it, by construction
        candidates = [i for i in idxs if pts[idxs.index(i)] not in base_nan_points]
        hit = rng.choice(candidates or idxs)
        fields = lines[hit].split(",")
        fields[5] = "NaN" if j % 2 == 0 else "nan"  # delta column, both spellings
        lines[hit] = ",".join(fields)
        truth_nan.add(pts[idxs.index(hit)])
        f.write_text("\n".join(lines) + "\n")

    for f in trunc_files:
        lines = f.read_text().splitlines()
        idxs = data_lines(f)
        last = idxs[-1]
        pts = file_points(f)
        truth_missing[pts[idxs.index(last)]] += 1
        # drop the last data row and leave a partial line behind it
        partial = lines[last][: len(lines[last]) // 2].rstrip(",")
        lines = lines[:last] + [partial]
        truth_trunc_files.add(f.name)
        f.write_text("\n".join(lines) + "\n")

    # ---- detect ----
    dam = collect_results(scratch, kind="radtot")
    dam_counts = Counter(point_key(r) for r in dam["records"])
    detected_missing = base_counts - dam_counts  # multiset difference
    # Differential, like missing_points: the source data carries real NaN from
    # the integrator defect; only NEW NaN counts as detected seeded damage.
    detected_nan = {
        point_key(r) for r in dam["records"] if r["delta"] != r["delta"]
    } - base_nan_points
    detected_problem_files = {
        Path(p["file"]).name for p in dam["problems"]
        if p["file"] not in base_problems
    }
    def score(truth, found):
        truth, found = set(truth), set(found)
        tp = len(truth & found)
        fp = len(found - truth)
        fn = len(truth - found)
        return {
            "seeded": len(truth), "detected": len(found),
            "true_pos": tp, "false_pos": fp, "false_neg": fn,
            "recall": round(tp / len(truth), 4) if truth else None,
            "precision": round(tp / len(found), 4) if found else None,
        }

    results = {
        "seed": args.seed,
        "source": str(source),
        "sampled_files": args.n_files,
        "baseline": {
            "n_records": base["n_records"],
            "n_unique_points": len(base_counts),
            "pre_existing_nan_points": len(base_nan_points),
        },
        "damage": {
            "deleted_files": args.n_delete_file,
            "deleted_rows": args.n_delete_row,
            "nan_injections": args.n_nan,
            "truncated_files": args.n_truncate,
        },
        "scores": {
            "missing_points": score(truth_missing, detected_missing),
            "nan_points": score(truth_nan, detected_nan),
            "truncated_file_flags": score(truth_trunc_files, detected_problem_files),
        },
        "note": "cell-level coverage_map is meaningful on full trees, not sparse "
                "samples; this benchmark scores at point level. Pre-existing NaN in "
                "the source (the integrator defect) is excluded differentially.",
    }
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "results.json").write_text(json.dumps(results, indent=2))
    shutil.rmtree(scratch)
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
