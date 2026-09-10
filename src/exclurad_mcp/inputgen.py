"""Input-file generation, byte-compatible with Izzy's validated inputs.

Format quirks reproduced deliberately (all load-bearing):
  - exactly two blank lines between the header block and the points block;
  - at most 10 points per file (this tool's convention; the Fortran reader
    accepts up to npoimax=10000) with automatic chunking;
  - the inert trailing '0error detected by nag library routine ...' line that
    appears in every known-good input.
"""

import csv
from dataclasses import dataclass
from pathlib import Path

from .channels import ChannelConfig
from .validators import KinematicPoint, MAX_POINTS_PER_FILE

TRAILER = "0error detected by nag library routine   d01fce - ifail =     2\n"


# The input file's second field. It is NOT a boolean: 0 is the full O(alpha)
# calculation every validated result was produced with, 1 is the factorised
# leading-log approximation. Leg E (2026-09-10) had a model pass rc_mode=1 in
# 11 of 15 conversations while asking for the exact correction, so the tools
# accept (and echo) these names.
RC_MODES: dict[str, int] = {"full": 0, "leading_log": 1}
RC_MODE_NAMES: dict[int, str] = {0: "full", 1: "leading_log"}
RC_MODE_HELP = {
    "full": "full O(alpha) radiative correction — what every validated eta and pi+ "
            "result was produced with; prints the 'tai:' integration lines; "
            "~50 s per point",
    "leading_log": "factorizable + leading-log APPROXIMATION — ~1 s per point, but "
                   "measured on the eta reference point (W=1.5576, Q2=0.5552, "
                   "cos=0.6517, phi=72) it gives delta = 0.8493 against the full "
                   "0.9160, a 7% difference, and returns NO radiative correction to "
                   "the beam-spin asymmetry at all (A_obs = A_Born exactly). Use it "
                   "for a fast survey, never as a substitute for an exact correction",
}


def resolve_rc_mode(value: "int | str") -> int:
    """Accept 'full'/'leading_log' or the raw 0/1 the Fortran reads."""
    if isinstance(value, str):
        key = value.strip().lower().replace("-", "_").replace(" ", "_")
        if key not in RC_MODES:
            raise ValueError(
                f"rc_mode '{value}' is not one of {sorted(RC_MODES)} "
                "(0 = full, 1 = leading_log)."
            )
        return RC_MODES[key]
    if value not in RC_MODE_NAMES:
        raise ValueError(f"rc_mode {value} must be 0 (full) or 1 (leading_log).")
    return int(value)


@dataclass
class InputHeader:
    model: int
    rc_mode: int      # 0: full, 1: factorizable + leading log (see RC_MODES)
    bmom: float       # beam (lepton) momentum [GeV]
    tmom: float       # target momentum per nucleon
    lepton: int       # 1: electron, 2: muon
    ivec: int         # detected hadron flag
    vcut: float       # inelasticity cut [GeV^2]

    @classmethod
    def for_channel(cls, ch: ChannelConfig, beam_gev: float | None = None,
                    vcut: float | None = None,
                    rc_mode: "int | str" = 0) -> "InputHeader":
        return cls(
            model=ch.model,
            rc_mode=resolve_rc_mode(rc_mode),
            bmom=beam_gev if beam_gev is not None else ch.default_beam_gev,
            tmom=0.0,
            lepton=1,
            ivec=ch.ivec_detected_hadron,
            vcut=vcut if vcut is not None else ch.default_vcut,
        )


def render_input(header: InputHeader, points: list[KinematicPoint]) -> str:
    if not points:
        raise ValueError("No kinematic points supplied.")
    if len(points) > MAX_POINTS_PER_FILE:
        raise ValueError(
            f"{len(points)} points exceed this tool's per-file limit of "
            f"{MAX_POINTS_PER_FILE}; use generate_input_files() which chunks automatically."
        )
    n = len(points)
    lines = [
        f"{header.model}       !  1: AO 2: maid98  3: maid2000",
        f"{header.rc_mode}       !  0: Full, 1: Factorizable and Leading log",
        f"{header.bmom}    !  bmom - lepton momentum",
        f"{header.tmom}     !  tmom - momentum per nucleon",
        f"{header.lepton}       !  lepton - 1 electron, 2 muon",
        f"{header.ivec}       !  ivec - detected hadron (1) p, (2) pi+",
        f"{header.vcut}   !  vcut - cut on inelasticity (0.) if no cut, negative -- v",
        "",
        "",
        f"{n} ! no. of points",
        " ".join(f"{p.w:.4f}" for p in points) + " ! W values",
        " ".join(f"{p.q2:.4f}" for p in points) + " ! Q^2 values",
        # six decimals so clamped values never round back to +/-1.000
        " ".join(f"{p.cos_theta:.6f}" for p in points) + " ! Cos(Theta) values",
        " ".join(f"{p.phi:.1f}" for p in points) + " ! phi values",
        "",
    ]
    return "\n".join(lines) + TRAILER


def _chunk(seq: list, size: int):
    for i in range(0, len(seq), size):
        yield seq[i:i + size], i // size


def generate_input_files(
    header: InputHeader,
    points: list[KinematicPoint],
    outdir: str | Path,
    label: str = "rcgrid",
) -> dict:
    """Write points into chunked input files plus a manifest.csv. Returns a
    summary with paths."""
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    manifest_rows = []
    files = []
    for chunk, idx in _chunk(points, MAX_POINTS_PER_FILE):
        first, last = chunk[0], chunk[-1]
        fname = (
            f"{label}_W{first.w:.4f}-{last.w:.4f}_Q2{first.q2:.4f}-{last.q2:.4f}"
            f"_p{idx + 1:03d}.dat"
        )
        fpath = out / fname
        fpath.write_text(render_input(header, chunk))
        files.append(str(fpath))
        manifest_rows.append([
            fname, f"{first.w:.6f}", f"{last.w:.6f}", f"{first.q2:.6f}", f"{last.q2:.6f}",
            f"{first.cos_theta:.6f}", f"{last.cos_theta:.6f}",
            f"{first.phi:.1f}", f"{last.phi:.1f}", str(len(chunk)),
        ])
    manifest = out / "manifest.csv"
    with manifest.open("w", newline="") as mf:
        w = csv.writer(mf)
        w.writerow([
            "file", "W_first", "W_last", "Q2_first", "Q2_last",
            "cos_first", "cos_last", "phi_first", "phi_last", "N_points",
        ])
        w.writerows(manifest_rows)
    return {
        "outdir": str(out),
        "n_points": len(points),
        "n_files": len(files),
        "files": files,
        "manifest": str(manifest),
    }
