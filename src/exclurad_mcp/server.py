"""MCP server exposing EXCLURAD pre-flight validation, input generation, and
execution tools.

Division of labor: the connected LLM translates physics intent ("eta at CLAS12
kinematics, this W x Q2 grid") into tool calls and explains results; every
correctness judgement is made by the deterministic code in validators.py.

Configuration (environment variables):
  EXCLURAD_WORK_DIR           — default work dir (contains build/exclurad[.exe]
                                and the .tbl tables).
  EXCLURAD_WORK_DIR_<CHANNEL> — per-channel override, e.g. EXCLURAD_WORK_DIR_ETA,
                                EXCLURAD_WORK_DIR_PIPLUS. Required when serving
                                multiple channels: eta and pion are DIFFERENT
                                BUILDS (masses/channel constants are compiled in
                                via mpintp.inc), not just different tables.
Tools also accept an explicit work_dir argument that overrides both.
"""

import json
import os
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from .buildgen import list_slots, verify_against, write_build
from .channels import CHANNELS, get_channel
from .inputgen import InputHeader, generate_input_files
from .outputs import (
    SCHEMAS,
    collect_results,
    coverage_map,
    parse_output_file,
    write_tidy_csv,
)
from .runner import run_input_file, smoke_test as _smoke_test
from .tables import resolve_table, scan_table_grid
from .validators import KinematicPoint, preflight

mcp = FastMCP("exclurad")


def _work_dir(override: str | None = None, channel: str | None = None) -> Path:
    wd = override
    if not wd and channel:
        wd = os.environ.get(f"EXCLURAD_WORK_DIR_{channel.upper()}")
    if not wd:
        wd = os.environ.get("EXCLURAD_WORK_DIR")
    if not wd:
        raise ValueError(
            "No work directory: pass work_dir, or set EXCLURAD_WORK_DIR (or the "
            f"per-channel EXCLURAD_WORK_DIR_{(channel or 'ETA').upper()}) to the exclurad "
            "checkout containing build/exclurad[.exe] and the .tbl tables. NOTE: eta and "
            "pion are different builds — point each channel at its own checkout."
        )
    return Path(wd).expanduser()


def _exe(work: Path) -> Path:
    # GNU make produces build/exclurad; the SCons build on ifarm produces exclurad.exe.
    for name in ("exclurad", "exclurad.exe"):
        cand = work / "build" / name
        if cand.exists():
            return cand
    return work / "build" / "exclurad"


def _points(raw: list[dict]) -> list[KinematicPoint]:
    return [
        KinematicPoint(
            w=float(p["w"]), q2=float(p["q2"]),
            cos_theta=float(p["cos_theta"]), phi=float(p["phi"]),
        )
        for p in raw
    ]


def _table_ranges(ch_key: str, work: Path):
    ch = get_channel(ch_key)
    table = work / ch.table_file
    if table.exists():
        grid = scan_table_grid(table)
        return tuple(grid["w_range"]), tuple(grid["q2_range"])
    return None, None


@mcp.tool()
def list_channels() -> str:
    """List the exclusive electroproduction channels this server knows how to
    configure, with thresholds, default kinematics, table aliases, and known quirks."""
    out = {}
    for key, ch in CHANNELS.items():
        out[key] = {
            "reaction": ch.reaction,
            "description": ch.description,
            "w_threshold_gev": round(ch.w_threshold, 4),
            "default_beam_gev": ch.default_beam_gev,
            "default_vcut_gev2": ch.default_vcut,
            "table_file": ch.table_file,
            "table_actual_content": ch.table_actual_content,
            "repo": ch.repo,
            "quirks": list(ch.quirks),
        }
    return json.dumps(out, indent=2)


@mcp.tool()
def resolve_tables(channel: str, work_dir: str | None = None) -> str:
    """Report which lookup table the Fortran will actually open for a channel,
    what the file really contains (the hardcoded names are historical aliases),
    and the (W, Q2) grid scanned from the file itself."""
    work = _work_dir(work_dir, channel)
    return json.dumps(resolve_table(get_channel(channel), work), indent=2)


@mcp.tool()
def preflight_check(
    channel: str,
    points: list[dict],
    beam_gev: float | None = None,
    vcut: float | None = None,
    work_dir: str | None = None,
) -> str:
    """Deterministically validate kinematic points BEFORE any compute is spent.

    Each point is a dict: {"w": GeV, "q2": GeV^2, "cos_theta": [-1,1], "phi": deg}.
    Checks: production threshold, cos(theta*) pole safety, beam-energy
    accessibility (nu, E', backscattering Q2 limit), lookup-table (W, Q2)
    coverage scanned from the actual .tbl file, phi range, and vcut sanity.
    Returns a per-point PASS/WARN/FAIL report with fix suggestions.
    """
    ch = get_channel(channel)
    beam = beam_gev if beam_gev is not None else ch.default_beam_gev
    v = vcut if vcut is not None else ch.default_vcut
    w_range, q2_range = (None, None)
    try:
        w_range, q2_range = _table_ranges(channel, _work_dir(work_dir, channel))
    except ValueError:
        pass  # no work dir configured: table coverage degrades to a WARN
    report = preflight(_points(points), ch, beam, v, w_range, q2_range)
    return json.dumps(report, indent=2)


@mcp.tool()
def generate_input(
    channel: str,
    points: list[dict],
    outdir: str,
    beam_gev: float | None = None,
    vcut: float | None = None,
    rc_mode: int = 0,
    label: str = "rcgrid",
    skip_preflight: bool = False,
    work_dir: str | None = None,
) -> str:
    """Write EXCLURAD input file(s) for the given kinematic points,
    byte-compatible with the validated input format (10-point chunking, blank
    lines, trailer line). Runs preflight first and refuses on FAIL unless
    skip_preflight is set; a manifest.csv accompanies the files."""
    ch = get_channel(channel)
    pts = _points(points)
    beam = beam_gev if beam_gev is not None else ch.default_beam_gev
    v = vcut if vcut is not None else ch.default_vcut
    result: dict = {}
    if not skip_preflight:
        w_range, q2_range = (None, None)
        try:
            w_range, q2_range = _table_ranges(channel, _work_dir(work_dir, channel))
        except ValueError:
            pass
        report = preflight(pts, ch, beam, v, w_range, q2_range)
        result["preflight"] = report["summary"]
        if report["verdict"] == "FAIL":
            failing = [p for p in report["points"] if p["verdict"] == "FAIL"]
            return json.dumps(
                {
                    "error": "preflight FAIL — no files written",
                    "preflight": report["summary"],
                    "failing_points": failing,
                    "hint": "Fix the points (suggestions included) or pass "
                            "skip_preflight=true to force generation.",
                },
                indent=2,
            )
    header = InputHeader.for_channel(ch, beam_gev=beam, vcut=v, rc_mode=rc_mode)
    result.update(generate_input_files(header, pts, outdir, label=label))
    return json.dumps(result, indent=2)


@mcp.tool()
def run_exclurad(
    input_file: str,
    results_dir: str,
    timeout_sec: int = 600,
    channel: str | None = None,
    work_dir: str | None = None,
) -> str:
    """Run the exclurad executable on one input file with a timeout, classify
    the outcome (OK / TIMEOUT / EXIT_NONZERO / NO_TAI silent-N/A / NO_OUTPUT),
    collect the seven output .dat files into results_dir, and return a
    diagnosis. Pass channel to resolve the per-channel work directory (eta and
    pion are separate builds)."""
    work = _work_dir(work_dir, channel)
    outcome = run_input_file(_exe(work), input_file, work, results_dir, timeout_sec)
    return json.dumps(outcome.to_dict(), indent=2)


@mcp.tool()
def smoke_test(
    channel: str,
    w: float,
    q2: float,
    cos_theta: float,
    phi: float,
    beam_gev: float | None = None,
    vcut: float | None = None,
    timeout_sec: int = 120,
    scratch_dir: str = "/tmp/exclurad-smoke",
    work_dir: str | None = None,
) -> str:
    """Probe a single kinematic point with a short timeout BEFORE committing a
    grid: builds a one-point input, runs it, and classifies the outcome. Use
    this to map where the code hangs or returns silent N/A (the NO_TAI status)
    so those regions can be diagnosed instead of discovered mid-run."""
    work = _work_dir(work_dir, channel)
    ch = get_channel(channel)
    pt = KinematicPoint(w=w, q2=q2, cos_theta=cos_theta, phi=phi)
    outcome = _smoke_test(
        _exe(work), work, scratch_dir, ch, pt,
        beam_gev=beam_gev, vcut=vcut, timeout_sec=timeout_sec,
    )
    return json.dumps(outcome.to_dict(), indent=2)


@mcp.tool()
def map_failures(
    skip_log: str | None = None,
    results_dir: str | None = None,
    kind: str = "radtot",
    csv_out: str | None = None,
) -> str:
    """Map which kinematic regions failed, two ways (pass one of them):

    - skip_log: aggregate a skipped_files.log (from run_exclurad_skip_unphys.sh
      or this server's runner) into failure reasons by kinematics parsed from
      input filenames.
    - results_dir: compute the COVERAGE map instead — parse all outputs of
      `kind`, count unique points per (W, Q2) cell, and report missing points
      per cell (catches silent losses with no skip log, e.g. farm runs).
      Set csv_out to write the long-form cells as CSV for a heatmap.

    Feed this to collaborators to diagnose WHY those regions fail."""
    import csv as _csv
    import re

    if results_dir:
        collected = collect_results(results_dir, kind=kind)
        cov = coverage_map(collected["records"])
        if csv_out:
            out = Path(csv_out)
            out.parent.mkdir(parents=True, exist_ok=True)
            cols = [cov["x_field"], cov["y_field"], "n_present", "n_missing",
                    "completeness_pct"]
            with out.open("w", newline="") as f:
                w = _csv.DictWriter(f, fieldnames=cols)
                w.writeheader()
                w.writerows(cov["cells"])
            cov["csv_written"] = str(out)
        cov["cells"] = cov["cells"][:100]
        return json.dumps(cov, indent=2)
    if not skip_log:
        raise ValueError("Pass skip_log or results_dir.")

    path = Path(skip_log)
    if not path.exists():
        raise FileNotFoundError(f"skip log not found: {path}")
    kin_pat = re.compile(r"W(?P<w>\d+\.\d+).*?Q2(?P<q2>\d+\.\d+)(?:.*?cos(?P<cos>-?\d+\.\d+))?")
    entries = []
    by_reason: dict[str, int] = {}
    for line in path.read_text().splitlines():
        parts = line.split()
        if len(parts) < 3:
            continue
        _, reason, fname = parts[0], parts[1], parts[-1]
        reason = reason.split("=")[0]
        by_reason[reason] = by_reason.get(reason, 0) + 1
        m = kin_pat.search(fname)
        entry = {"reason": reason, "file": fname}
        if m:
            entry["w"] = float(m.group("w"))
            entry["q2"] = float(m.group("q2"))
            if m.group("cos"):
                entry["cos_theta"] = float(m.group("cos"))
        entries.append(entry)
    with_kin = [e for e in entries if "w" in e]
    summary: dict = {"total_skipped": len(entries), "by_reason": by_reason}
    if with_kin:
        ws = [e["w"] for e in with_kin]
        q2s = [e["q2"] for e in with_kin if "q2" in e]
        summary["w_range_of_failures"] = (min(ws), max(ws))
        if q2s:
            summary["q2_range_of_failures"] = (min(q2s), max(q2s))
    return json.dumps({"summary": summary, "entries": entries}, indent=2)


@mcp.tool()
def describe_outputs() -> str:
    """Document the columns, units, and separators of EXCLURAD's seven output
    files (radtot, radcor, radasm, radsigpl, radsigmi, all, allu), decoded from
    the Fortran write statements and verified against real CLAS12 eta results.
    Includes the known landmines: mixed CSV/fixed-width formats, the unpopulated
    e1 column in radtot, and radcor's two-rows-per-point layout."""
    out = {}
    for kind, schema in SCHEMAS.items():
        entry = {
            "file": f"{kind}.dat",
            "description": schema["description"],
            "format": schema["separator"],
            "columns": [{"name": n, "meaning": d} for n, d in schema["columns"]],
        }
        if "note" in schema:
            entry["note"] = schema["note"]
        out[kind] = entry
    return json.dumps(out, indent=2)


@mcp.tool()
def parse_output(
    path: str,
    kind: str | None = None,
    build: str = "auto",
    csv_out: str | None = None,
    max_records_returned: int = 50,
) -> str:
    """Parse EXCLURAD output into a tidy table ready for plotting (e.g. via the
    plotwright MCP server). `path` may be a single output .dat file or a results
    directory, in which case all chunk files of `kind` (default radtot) are
    combined with a source_file column. build: 'eta', 'pion', or 'auto' —
    radtot/radsigpl formats differ between the two builds (auto sniffs for CSV).
    Set csv_out to also write a CSV; the JSON response returns at most
    max_records_returned records plus totals."""
    p = Path(path)
    if p.is_dir():
        collected = collect_results(p, kind=kind or "radtot", build=build)
    else:
        parsed = parse_output_file(p, kind=kind, build=build)
        if parsed.get("diagnostic"):
            return json.dumps(parsed, indent=2)
        collected = {
            "kind": parsed["kind"],
            "n_files": 1,
            "n_records": parsed["n_records"],
            "columns": parsed["columns"] + ["source_file"],
            "records": [dict(r, source_file=p.name) for r in parsed["records"]],
            "problems": (
                [{"file": str(p), "unparsed_lines": parsed["n_unparsed_lines"]}]
                if parsed["n_unparsed_lines"] else []
            ),
        }
    result = {k: v for k, v in collected.items() if k != "records"}
    if csv_out:
        result["csv_written"] = write_tidy_csv(collected, csv_out)
    result["records_preview"] = collected["records"][:max_records_returned]
    if collected["n_records"] > max_records_returned:
        result["note"] = (
            f"{collected['n_records']} records total; preview truncated to "
            f"{max_records_returned}. Use csv_out for the full table."
        )
    return json.dumps(result, indent=2)


@mcp.tool()
def describe_build_slots() -> str:
    """List every place where the EXCLURAD Fortran hardcodes a channel-specific
    value (meson mass x4 sites, polarization mode, integration tolerance,
    output formats, table-header read format, lookup-table grid dimensions),
    with the currently-accepted values per channel. These 16 slots are the
    complete difference between the eta and pion sources — one template plus
    this registry regenerates either validated source byte-for-byte."""
    return json.dumps(
        {
            "n_slots": len(list_slots()),
            "contract": "A value is 'accepted' because generating with it reproduces a "
                        "validated source byte-for-byte (see generate_build verify).",
            "slots": list_slots(),
        },
        indent=2,
    )


@mcp.tool()
def generate_build(
    channel: str,
    dest_dir: str,
    verify_reference_dir: str | None = None,
) -> str:
    """Render the channel-specific Fortran sources (exclurad.F, mpintp.inc)
    from the single template + slot registry into dest_dir, ready to compile
    with the shared fint.F/spp.inc/Makefile and the channel's lookup table.
    If verify_reference_dir is given (a validated checkout), also byte-compare
    the generated sources against it and report PASS/FAIL."""
    result = write_build(channel, dest_dir)
    if verify_reference_dir:
        result["verification"] = verify_against(channel, verify_reference_dir)
    return json.dumps(result, indent=2)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
