"""Execution and outcome classification for exclurad.exe.

Failure taxonomy (mirrors run_exclurad_skip_unphys.sh, made machine-readable):
  OK           — ran, produced 'tai:' output and output files
  TIMEOUT      — integrator hung past the deadline (almost always unphysical kinematics)
  EXIT_NONZERO — crashed / NAG error propagated to the exit code
  NO_TAI       — exited cleanly but produced no 'tai:' line: silent N/A result
  NO_OUTPUT    — 'tai:' seen but no output .dat files materialized
"""

import shutil
import subprocess
from dataclasses import dataclass, asdict
from pathlib import Path

from .channels import ChannelConfig
from .inputgen import InputHeader, render_input
from .validators import KinematicPoint

OUTPUT_KEYS = ("all", "allu", "radasm", "radcor", "radsigmi", "radsigpl", "radtot")

OK = "OK"
TIMEOUT = "TIMEOUT"
EXIT_NONZERO = "EXIT_NONZERO"
NO_TAI = "NO_TAI"
NO_OUTPUT = "NO_OUTPUT"


@dataclass
class RunOutcome:
    status: str
    input_file: str
    exit_code: int | None
    elapsed_note: str
    stdout_tail: str
    outputs: dict[str, str]  # output key -> collected file path
    nag_errors: list[str]
    diagnosis: str

    def to_dict(self) -> dict:
        return asdict(self)


def _diagnose(status: str) -> str:
    return {
        OK: "Run succeeded.",
        TIMEOUT: "Integrator hung — this almost always means the kinematics are unphysical "
                 "or sit on a pathological edge (near threshold, |cos(theta*)| ~ 1).",
        EXIT_NONZERO: "Non-zero exit; check the stdout tail for NAG integration errors "
                      "(d01fce ifail) or a failed table open.",
        NO_TAI: "Clean exit but no 'tai:' line — the silent-N/A failure mode. The kinematics "
                "passed the reader but the calculation produced nothing; log this point for "
                "diagnosis rather than treating it as zero.",
        NO_OUTPUT: "'tai:' was printed but no output files appeared; check working-directory "
                   "permissions and that no stale outputs were locked.",
    }[status]


def run_input_file(
    exe_path: str | Path,
    input_file: str | Path,
    work_dir: str | Path,
    results_dir: str | Path,
    timeout_sec: int = 600,
) -> RunOutcome:
    """Copy input into the work dir as input.dat, run the executable, classify
    the outcome, and collect outputs into results_dir keyed by input basename."""
    exe = Path(exe_path)
    work = Path(work_dir)
    inp = Path(input_file)
    results = Path(results_dir)
    if not exe.exists():
        raise FileNotFoundError(f"exclurad executable not found: {exe} (build with make/scons)")
    if not inp.exists():
        raise FileNotFoundError(f"input file not found: {inp}")

    # Clear stale outputs so NO_OUTPUT detection is trustworthy.
    for key in OUTPUT_KEYS:
        (work / f"{key}.dat").unlink(missing_ok=True)
    target = work / "input.dat"
    if not (target.exists() and inp.samefile(target)):
        shutil.copyfile(inp, target)

    try:
        proc = subprocess.run(
            [str(exe)], cwd=work, capture_output=True, text=True, timeout=timeout_sec,
        )
        exit_code: int | None = proc.returncode
        stdout = (proc.stdout or "") + (proc.stderr or "")
        timed_out = False
    except subprocess.TimeoutExpired as exc:
        exit_code = None
        stdout = ((exc.stdout or b"").decode(errors="replace")
                  if isinstance(exc.stdout, bytes) else (exc.stdout or ""))
        timed_out = True

    nag_errors = [ln.strip() for ln in stdout.splitlines() if "nag library" in ln.lower()]
    tail = "\n".join(stdout.splitlines()[-15:])

    if timed_out:
        status = TIMEOUT
    elif exit_code != 0:
        status = EXIT_NONZERO
    elif "tai:" not in stdout:
        status = NO_TAI
    else:
        status = OK

    outputs: dict[str, str] = {}
    if status == OK:
        base = inp.stem
        collected_any = False
        for key in OUTPUT_KEYS:
            src = work / f"{key}.dat"
            if src.exists():
                dest_dir = results / key
                dest_dir.mkdir(parents=True, exist_ok=True)
                dest = dest_dir / f"{base}.dat"
                shutil.move(str(src), dest)
                outputs[key] = str(dest)
                collected_any = True
        if not collected_any:
            status = NO_OUTPUT

    return RunOutcome(
        status=status,
        input_file=str(inp),
        exit_code=exit_code,
        elapsed_note=f"timeout budget {timeout_sec}s" + (" (hit)" if timed_out else ""),
        stdout_tail=tail,
        outputs=outputs,
        nag_errors=nag_errors,
        diagnosis=_diagnose(status),
    )


def smoke_test(
    exe_path: str | Path,
    work_dir: str | Path,
    scratch_dir: str | Path,
    ch: ChannelConfig,
    point: KinematicPoint,
    beam_gev: float | None = None,
    vcut: float | None = None,
    timeout_sec: int = 120,
) -> RunOutcome:
    """Probe a single kinematic point with a short timeout before committing a
    full grid. This is how N/A regions get mapped instead of discovered mid-run."""
    scratch = Path(scratch_dir)
    scratch.mkdir(parents=True, exist_ok=True)
    header = InputHeader.for_channel(ch, beam_gev=beam_gev, vcut=vcut)
    probe = scratch / (
        f"smoke_{ch.key}_W{point.w:.4f}_Q2{point.q2:.4f}"
        f"_c{point.cos_theta:.3f}_phi{point.phi:.0f}.dat"
    )
    probe.write_text(render_input(header, [point]))
    return run_input_file(exe_path, probe, work_dir, scratch / "smoke_results", timeout_sec)
