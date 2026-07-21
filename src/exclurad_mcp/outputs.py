"""Column schemas and parsers for EXCLURAD's seven output files.

Decoded from the write statements in exclurad.F (main loop, ~lines 156-200)
and verified against real CLAS12 eta-grid outputs (results_Oct2025).

BUILD VARIANTS: the output formats are themselves channel slots (see
buildgen.py). The eta build writes radtot as 10-column CSV and radsigpl as
CSV; the upstream pion build writes radtot as 7 fixed-width columns
(e1,w,q2,cos,phi,ddcr,dd) and radsigpl fixed-width. Parsing auto-detects the
variant by sniffing for commas, or takes build='eta'/'pion' explicitly.

Landmines encoded here so downstream plotting never trips on them:
  - radtot.dat and radsigpl.dat are COMMA-separated; radcor.dat, radasm.dat,
    and radsigmi.dat are FIXED-WIDTH (the formats were toggled during
    development and left inconsistent — see the commented write statements
    in the source).
  - radtot column 1 ('e1') is written from a never-populated variable and is
    0.0 in real output; the beam energy actually lives in the input's bmom.
  - radcor.dat has TWO lines per kinematic point (ipol=1 unpolarized,
    ipol=2 polarized) because the write sits inside the polarization loop.
  - fixed-width fields can abut with no separator when values fill the field
    (e.g. phi=252.00 in f6.2), so fixed-width files are sliced by width, not
    whitespace-split.
  - all.dat / allu.dat are legacy DIFFRAD diagnostics ('tai:' lines), not
    physics tables; they are summarized, not parsed into columns.
"""

import csv
import io
from pathlib import Path

# (name, description) per column, in file order.
SCHEMAS: dict[str, dict] = {
    "radtot": {
        "description": "Main results table: RC factor, Born cross section, asymmetries",
        "separator": "csv",
        "columns": [
            ("e1_unused", "UNPOPULATED in current builds — always 0.0; beam energy is the input bmom"),
            ("w", "invariant mass W [GeV]"),
            ("q2", "photon virtuality Q^2 [GeV^2]"),
            ("cos_theta", "cos(theta*) of the detected hadron (CM)"),
            ("phi_deg", "phi* [deg]"),
            ("delta", "radiative correction factor: sigma_obs / sigma_Born (unpolarized)"),
            ("sigma_born", "Born cross section, unpolarized"),
            ("asym_obs_pct", "observed beam-spin asymmetry x100 [%]"),
            ("asym_born_pct", "Born beam-spin asymmetry x100 [%]"),
            ("asym_rc_pct", "relative RC to the asymmetry: (A_obs - A_Born)/A_Born x100 [%]"),
        ],
        "note": "asym_rc_pct is MEANINGLESS at phi = 0/180/360: the beam-spin asymmetry "
                "is proportional to sin(phi), so A_Born ~ 0 and the ratio blows up "
                "(values of +/-1000s of percent, or Fortran ****** field overflow, which "
                "the parser skips and counts as an unparsed line).",
    },
    "radcor": {
        "description": "RC factors per polarization state (two rows per kinematic point)",
        "separator": "widths",
        "widths": [8, 8, 8, 8, 8, 8, 8, 8],
        "columns": [
            ("w", "invariant mass W [GeV]"),
            ("q2", "photon virtuality Q^2 [GeV^2]"),
            ("eps", "virtual-photon polarization epsilon"),
            ("cos_theta", "cos(theta*)"),
            ("phi_deg", "phi* [deg]"),
            ("delta", "sigma_obs / sigma_Born for this polarization row"),
            ("born_check", "sigma_Born(structure functions) / sigma_Born(test) — internal consistency, ~1"),
            ("delta_ll", "leading-log approximation of delta"),
        ],
        "note": "Row 1 of each pair: unpolarized (SF 1-4). Row 2: polarized (5th SF).",
    },
    "radasm": {
        "description": "Beam-spin asymmetry before/after radiative corrections",
        "separator": "widths",
        "widths": [6, 6, 6, 6, 6, 8, 8, 8],
        "columns": [
            ("w", "invariant mass W [GeV]"),
            ("q2", "photon virtuality Q^2 [GeV^2]"),
            ("eps", "virtual-photon polarization epsilon"),
            ("cos_theta", "cos(theta*)"),
            ("phi_deg", "phi* [deg]"),
            ("asym_obs_pct", "observed beam-spin asymmetry x100 [%]"),
            ("asym_born_pct", "Born beam-spin asymmetry x100 [%]"),
            ("asym_rc_pct", "(A_obs - A_Born)/A_Born x100 [%]"),
        ],
        "note": "Kinematic columns are f6.2 — cos(theta*)=0.999 rounds to 1.00 here. "
                "Use radtot.dat (F16.10) as the source of truth for point identity.",
    },
    "radsigpl": {
        "description": "Helicity-plus cross sections (sum of polarization states)",
        "separator": "csv",
        "columns": [
            ("w", "invariant mass W [GeV]"),
            ("q2", "photon virtuality Q^2 [GeV^2]"),
            ("eps", "virtual-photon polarization epsilon"),
            ("cos_theta", "cos(theta*)"),
            ("phi_deg", "phi* [deg]"),
            ("sigma_born_plus", "Born cross section, helicity +"),
            ("sigma_obs_plus", "observed (radiatively corrected) cross section, helicity +"),
        ],
    },
    "radsigmi": {
        "description": "Helicity-minus cross sections (difference of polarization states)",
        "separator": "widths",
        "widths": [6, 6, 6, 6, 6, 11, 11],
        "columns": [
            ("w", "invariant mass W [GeV]"),
            ("q2", "photon virtuality Q^2 [GeV^2]"),
            ("eps", "virtual-photon polarization epsilon"),
            ("cos_theta", "cos(theta*)"),
            ("phi_deg", "phi* [deg]"),
            ("sigma_born_minus", "Born cross section, helicity -"),
            ("sigma_obs_minus", "observed (radiatively corrected) cross section, helicity -"),
        ],
        "note": "Kinematic columns are f6.2 (low precision) — join to radtot.dat for exact "
                "point identity. radsigpl is CSV but this file is fixed-width.",
    },
    "all": {
        "description": "Legacy DIFFRAD diagnostics: run header + 'tai:' bremsstrahlung-tail lines",
        "separator": "diagnostic",
        "columns": [],
    },
}

# Formats written by the upstream pion build (slots output_format_radtot /
# output_format_radsigpl in buildgen.py). Kinds not listed here are identical
# across builds.
PION_VARIANTS: dict[str, dict] = {
    "radtot": {
        "description": "Main results table (pion/upstream build: 7 fixed-width columns)",
        "separator": "widths",
        "widths": [6, 6, 6, 6, 6, 8, 8],
        "columns": [
            ("e1_unused", "beam-energy variable; unpopulated in known builds — verify before use"),
            ("w", "invariant mass W [GeV]"),
            ("q2", "photon virtuality Q^2 [GeV^2]"),
            ("cos_theta", "cos(theta*)"),
            ("phi_deg", "phi* [deg]"),
            ("delta", "radiative correction factor sigma_obs/sigma_Born (unpolarized)"),
            ("asym_rc_pct", "(A_obs - A_Born)/A_Born x100 [%]"),
        ],
    },
    "radsigpl": {
        "description": "Helicity-plus cross sections (pion/upstream build: fixed-width)",
        "separator": "widths",
        "widths": [6, 6, 6, 6, 6, 11, 11],
        "columns": SCHEMAS["radsigpl"]["columns"],
    },
}

SCHEMAS["allu"] = {
    "description": "Legacy DIFFRAD diagnostics (unpolarized tail information)",
    "separator": "diagnostic",
    "columns": [],
}


def _parse_line(line: str, schema: dict) -> list[float] | None:
    """Parse one data line according to the schema; None if not a data row."""
    stripped = line.strip()
    if not stripped or stripped.startswith(("!", "#", "*")):
        return None
    ncol = len(schema["columns"])
    if schema["separator"] == "csv":
        fields = [f for f in stripped.split(",") if f.strip()]
        if len(fields) != ncol:
            return None
        try:
            return [float(f) for f in fields]
        except ValueError:
            return None
    # Fixed-width: try width slicing first; fall back to whitespace split when
    # the split happens to yield the right column count.
    widths = schema["widths"]
    if len(line.rstrip("\n")) >= sum(widths) - widths[-1]:
        pos, vals = 0, []
        ok = True
        for wdt in widths:
            field = line[pos:pos + wdt].strip()
            pos += wdt
            if not field:
                ok = False
                break
            try:
                vals.append(float(field))
            except ValueError:
                ok = False
                break
        if ok and len(vals) == ncol:
            return vals
    parts = stripped.split()
    if len(parts) == ncol:
        try:
            return [float(p) for p in parts]
        except ValueError:
            return None
    return None


def _select_schema(kind: str, build: str, text: str) -> dict:
    """Pick the eta or pion schema for kinds whose format differs per build.

    build: 'eta', 'pion', or 'auto' (sniff: the eta build writes these files
    as CSV, so the presence of commas decides).
    """
    schema = SCHEMAS[kind]
    if kind not in PION_VARIANTS:
        return schema
    if build == "pion":
        return PION_VARIANTS[kind]
    if build == "eta":
        return schema
    for line in text.splitlines():
        if line.strip():
            return schema if "," in line else PION_VARIANTS[kind]
    return schema


def parse_output_file(path: str | Path, kind: str | None = None,
                      build: str = "auto") -> dict:
    """Parse a single EXCLURAD output file into records.

    kind: one of radtot/radcor/radasm/radsigpl/radsigmi; inferred from the
    filename/parent directory when omitted. build: 'eta', 'pion', or 'auto' —
    radtot/radsigpl formats differ between the two builds.
    """
    p = Path(path)
    if kind is None:
        for key in SCHEMAS:
            if key in p.name or key in (p.parent.name,):
                kind = key
                break
    if kind is None or kind not in SCHEMAS:
        raise ValueError(
            f"Cannot infer output kind for {p.name}; pass kind= one of {sorted(SCHEMAS)}"
        )
    text = p.read_text(errors="replace")
    if SCHEMAS[kind]["separator"] == "diagnostic":
        tai_lines = [ln.strip() for ln in text.splitlines() if "tai:" in ln]
        return {"kind": kind, "diagnostic": True, "n_tai_lines": len(tai_lines),
                "tai_lines": tai_lines[:50]}
    schema = _select_schema(kind, build, text)
    names = [c[0] for c in schema["columns"]]
    records = []
    skipped = 0
    for line in text.splitlines():
        vals = _parse_line(line, schema)
        if vals is None:
            if line.strip():
                skipped += 1
            continue
        records.append(dict(zip(names, vals)))
    return {
        "kind": kind,
        "file": str(p),
        "n_records": len(records),
        "n_unparsed_lines": skipped,
        "columns": names,
        "records": records,
    }


def collect_results(results_dir: str | Path, kind: str = "radtot",
                    build: str = "auto") -> dict:
    """Combine all chunk files of one output kind under a results directory
    into a single tidy table (list of records with a source_file column)."""
    root = Path(results_dir)
    subdir = root / kind
    if subdir.is_dir():
        files = sorted(subdir.rglob("*.dat"))
    else:
        # Deep tree (e.g. many results_chunk_*/radtot/ dirs): only take files
        # sitting in a directory named after the kind, so radcor/inputs/etc.
        # chunks are not swept into a radtot table.
        files = sorted(f for f in root.rglob("*.dat") if f.parent.name == kind)
    if not files:
        raise FileNotFoundError(f"No .dat files for kind '{kind}' under {root}")
    all_records = []
    problems = []
    for f in files:
        try:
            parsed = parse_output_file(f, kind=kind, build=build)
        except ValueError as exc:
            problems.append({"file": str(f), "error": str(exc)})
            continue
        for r in parsed["records"]:
            r["source_file"] = f.name
            all_records.append(r)
        if parsed["n_unparsed_lines"]:
            problems.append({"file": str(f), "unparsed_lines": parsed["n_unparsed_lines"]})
    return {
        "kind": kind,
        "n_files": len(files),
        "n_records": len(all_records),
        "columns": [c[0] for c in SCHEMAS[kind]["columns"]] + ["source_file"],
        "records": all_records,
        "problems": problems,
    }


def coverage_map(
    records: list[dict],
    x_field: str = "w",
    y_field: str = "q2",
    expected_per_cell: int | None = None,
) -> dict:
    """Per-(x, y) completeness of a kinematic grid — the silent-failure map.

    Counts unique points per cell over the OTHER kinematic axes (cos_theta,
    phi_deg). expected_per_cell defaults to the maximum observed cell count,
    so fully-populated cells read as 0 missing without needing the original
    run manifest. Returns long-form cells ready for a heatmap."""
    other = [f for f in ("w", "q2", "cos_theta", "phi_deg")
             if f not in (x_field, y_field)]
    cells: dict[tuple, set] = {}
    for r in records:
        cells.setdefault((r[x_field], r[y_field]), set()).add(
            tuple(r[f] for f in other)
        )
    expected = expected_per_cell or max(len(v) for v in cells.values())
    # Rasterize the FULL grid (cartesian product of observed axis values):
    # cells with zero output never appear in the records, and those dead
    # cells are exactly the ones a failure map must not hide.
    xs = sorted({k[0] for k in cells})
    ys = sorted({k[1] for k in cells})
    out_cells = []
    for x in xs:
        for y in ys:
            pts = cells.get((x, y), set())
            out_cells.append(
                {
                    x_field: x, y_field: y,
                    "n_present": len(pts),
                    "n_missing": max(0, expected - len(pts)),
                    "completeness_pct": round(
                        100.0 * min(len(pts), expected) / expected, 2
                    ),
                }
            )
    n_holes = sum(c["n_missing"] for c in out_cells)
    return {
        "x_field": x_field, "y_field": y_field,
        "expected_per_cell": expected,
        "n_cells": len(out_cells),
        "n_incomplete_cells": sum(1 for c in out_cells if c["n_missing"]),
        "total_missing_points": n_holes,
        "cells": out_cells,
    }


def write_tidy_csv(collected: dict, out_path: str | Path) -> str:
    """Write a collect_results() table to CSV for plotting tools."""
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    cols = collected["columns"]
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=cols)
    writer.writeheader()
    for r in collected["records"]:
        writer.writerow(r)
    out.write_text(buf.getvalue())
    return str(out)
