"""Deterministic pre-flight validation of EXCLURAD kinematic points.

This module is the trust boundary of the whole system: every physics
correctness judgement lives here as testable code. The LLM never decides
whether a value is physical — it only calls preflight() and relays the result.

Each check returns PASS, WARN, or FAIL:
  FAIL — the run is unphysical or will not work; do not submit.
  WARN — the run may work but sits in a regime known to hang, silently
         return N/A, or extrapolate beyond table coverage.
"""

from dataclasses import dataclass, asdict
from .channels import ChannelConfig

PASS, WARN, FAIL = "PASS", "WARN", "FAIL"

# |cos(theta*)| above this is inside the regime where the integrator is known
# to misbehave even though the value is formally physical.
COS_SAFE_LIMIT = 0.999
# Fortran reader hard limit on points per input file.
MAX_POINTS_PER_FILE = 10
# W within this margin above threshold gets a near-threshold warning [GeV].
NEAR_THRESHOLD_MARGIN = 0.01


@dataclass
class CheckResult:
    check: str
    level: str
    message: str
    suggestion: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class KinematicPoint:
    w: float          # invariant mass W [GeV]
    q2: float         # photon virtuality Q^2 [GeV^2]
    cos_theta: float  # cos(theta*) of the detected hadron in the CM frame
    phi: float        # phi* [deg]


def check_w_threshold(pt: KinematicPoint, ch: ChannelConfig) -> CheckResult:
    thr = ch.w_threshold
    if pt.w < thr:
        return CheckResult(
            "w_threshold", FAIL,
            f"W = {pt.w:.4f} GeV is below the {ch.reaction} threshold ({thr:.4f} GeV); "
            "the final state cannot be produced.",
            f"Use W >= {thr + NEAR_THRESHOLD_MARGIN:.4f} GeV.",
        )
    if pt.w < thr + NEAR_THRESHOLD_MARGIN:
        return CheckResult(
            "w_threshold", WARN,
            f"W = {pt.w:.4f} GeV is within {NEAR_THRESHOLD_MARGIN*1000:.0f} MeV of threshold "
            f"({thr:.4f} GeV); the integrator is known to hang or return silent N/A here.",
            "Run a smoke test with a short timeout before submitting a grid.",
        )
    return CheckResult("w_threshold", PASS, f"W = {pt.w:.4f} GeV is above threshold ({thr:.4f} GeV).")


def check_cos_theta(pt: KinematicPoint) -> CheckResult:
    c = pt.cos_theta
    if abs(c) >= 1.0:
        return CheckResult(
            "cos_theta", FAIL,
            f"cos(theta*) = {c} — the code cannot evaluate exactly at the poles.",
            f"Clamp to +/-{COS_SAFE_LIMIT} (this is the validated convention for this code).",
        )
    if abs(c) > COS_SAFE_LIMIT:
        return CheckResult(
            "cos_theta", WARN,
            f"cos(theta*) = {c} exceeds the validated safe limit |cos| <= {COS_SAFE_LIMIT}.",
            f"Prefer |cos(theta*)| <= {COS_SAFE_LIMIT}.",
        )
    return CheckResult("cos_theta", PASS, f"cos(theta*) = {c} is inside the safe range.")


def check_beam_accessibility(pt: KinematicPoint, ch: ChannelConfig, beam_gev: float) -> CheckResult:
    """Is (W, Q^2) reachable with this beam energy on a fixed target?

    nu = (W^2 + Q^2 - M^2) / 2M must leave a positive scattered-electron
    energy E' = E - nu, and Q^2 cannot exceed its backscattering maximum
    Q^2_max = 4 E E'.
    """
    m = ch.target_mass
    nu = (pt.w**2 + pt.q2 - m**2) / (2.0 * m)
    e_prime = beam_gev - nu
    if e_prime <= 0.0:
        return CheckResult(
            "beam_accessibility", FAIL,
            f"(W={pt.w:.3f}, Q2={pt.q2:.3f}) requires energy transfer nu = {nu:.3f} GeV, "
            f"which exceeds the beam energy {beam_gev} GeV.",
            "Lower W/Q2 or raise the beam energy.",
        )
    q2_max = 4.0 * beam_gev * e_prime
    if pt.q2 > q2_max:
        return CheckResult(
            "beam_accessibility", FAIL,
            f"Q2 = {pt.q2:.3f} GeV^2 exceeds the kinematic maximum {q2_max:.3f} GeV^2 "
            f"for W = {pt.w:.3f} GeV at E_beam = {beam_gev} GeV (backscattering limit).",
            "Reduce Q2 or W, or raise the beam energy.",
        )
    y = nu / beam_gev
    if y > 0.95:
        return CheckResult(
            "beam_accessibility", WARN,
            f"Inelasticity y = {y:.3f} is extreme (E' = {e_prime:.3f} GeV); radiative "
            "corrections and the vcut behaviour become delicate here.",
            "Cross-check this corner against a smoke test.",
        )
    return CheckResult(
        "beam_accessibility", PASS,
        f"(W, Q2) reachable: nu = {nu:.3f} GeV, E' = {e_prime:.3f} GeV, y = {y:.3f}.",
    )


def check_table_coverage(
    pt: KinematicPoint, w_range: tuple[float, float] | None, q2_range: tuple[float, float] | None
) -> CheckResult:
    """Compare the point against the (W, Q2) grid actually present in the lookup table.

    Ranges come from tables.scan_table_grid(); pass None if the table was not scanned.
    """
    if w_range is None or q2_range is None:
        return CheckResult(
            "table_coverage", WARN,
            "Lookup table grid was not scanned; cannot verify (W, Q2) coverage.",
            "Provide the table path so coverage can be checked against the real grid.",
        )
    problems = []
    if not (w_range[0] <= pt.w <= w_range[1]):
        problems.append(f"W = {pt.w:.4f} outside table grid [{w_range[0]:.4f}, {w_range[1]:.4f}]")
    if not (q2_range[0] <= pt.q2 <= q2_range[1]):
        problems.append(f"Q2 = {pt.q2:.3f} outside table grid [{q2_range[0]:.3f}, {q2_range[1]:.3f}]")
    if problems:
        return CheckResult(
            "table_coverage", FAIL,
            "; ".join(problems) + " — the code would extrapolate the hadronic model.",
            "Restrict the grid to the table coverage, or supply an extended table.",
        )
    return CheckResult(
        "table_coverage", PASS,
        f"(W, Q2) inside table grid W:[{w_range[0]:.4f}, {w_range[1]:.4f}], "
        f"Q2:[{q2_range[0]:.3f}, {q2_range[1]:.3f}].",
    )


def check_phi(pt: KinematicPoint) -> CheckResult:
    if not (0.0 <= pt.phi <= 360.0):
        return CheckResult(
            "phi", FAIL, f"phi* = {pt.phi} deg is outside [0, 360].",
            "Map phi* into [0, 360].",
        )
    return CheckResult("phi", PASS, f"phi* = {pt.phi} deg is in range.")


def check_vcut(vcut: float) -> CheckResult:
    if vcut < 0.0:
        return CheckResult(
            "vcut", WARN,
            f"vcut = {vcut}: negative values switch the code to its 'v' interpretation "
            "(see input comment); make sure that is intended.",
            "Use 0 for no cut or a positive inelasticity cut in GeV^2.",
        )
    if vcut > 1.0:
        return CheckResult(
            "vcut", WARN,
            f"vcut = {vcut} GeV^2 is unusually large (validated eta analysis used 0.166).",
        )
    return CheckResult("vcut", PASS, f"vcut = {vcut} GeV^2.")


def preflight_point(
    pt: KinematicPoint,
    ch: ChannelConfig,
    beam_gev: float,
    table_w_range: tuple[float, float] | None = None,
    table_q2_range: tuple[float, float] | None = None,
) -> list[CheckResult]:
    return [
        check_w_threshold(pt, ch),
        check_cos_theta(pt),
        check_beam_accessibility(pt, ch, beam_gev),
        check_table_coverage(pt, table_w_range, table_q2_range),
        check_phi(pt),
    ]


def preflight(
    points: list[KinematicPoint],
    ch: ChannelConfig,
    beam_gev: float,
    vcut: float,
    table_w_range: tuple[float, float] | None = None,
    table_q2_range: tuple[float, float] | None = None,
) -> dict:
    """Validate a full request. Returns a structured report with a per-point
    breakdown and an overall verdict: FAIL if any point fails, else WARN if
    any warns, else PASS."""
    global_checks = [check_vcut(vcut)]
    point_reports = []
    worst = PASS
    order = {PASS: 0, WARN: 1, FAIL: 2}
    for i, pt in enumerate(points):
        results = preflight_point(pt, ch, beam_gev, table_w_range, table_q2_range)
        point_worst = max((r.level for r in results), key=lambda l: order[l])
        worst = max(worst, point_worst, key=lambda l: order[l])
        point_reports.append(
            {
                "index": i,
                "point": asdict(pt),
                "verdict": point_worst,
                "checks": [r.to_dict() for r in results if r.level != PASS] or
                          [{"check": "all", "level": PASS, "message": "all checks passed"}],
            }
        )
    for g in global_checks:
        worst = max(worst, g.level, key=lambda l: order[l])
    n_fail = sum(1 for p in point_reports if p["verdict"] == FAIL)
    n_warn = sum(1 for p in point_reports if p["verdict"] == WARN)
    return {
        "verdict": worst,
        "n_points": len(points),
        "n_fail": n_fail,
        "n_warn": n_warn,
        "global_checks": [g.to_dict() for g in global_checks],
        "points": point_reports,
        "summary": (
            f"{len(points)} point(s): {len(points) - n_fail - n_warn} pass, "
            f"{n_warn} warn, {n_fail} fail. Overall: {worst}."
        ),
    }
