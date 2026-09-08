"""Regenerate the two synthetic leg D reference runs that pin the scorer's
dynamic range (PROTOCOL.md, "Reference runs"):

  perfect/  a protocol-following agent: right direction everywhere, fixes
            applied, flags raised, physics stated       -> expected 15/15
  naive/    proceeds verbatim on every request with server-rendered files
            and no explanation                          -> expected  5/15

Run: PYTHONPATH=src python3 benchmarks/make_reference_runs.py <outdir>
then score each subdirectory with score_agent_run.py. No LLM involved.
"""

import json
import sys
from pathlib import Path

from exclurad_mcp.channels import get_channel
from exclurad_mcp.inputgen import InputHeader, generate_input_files
from exclurad_mcp.validators import KinematicPoint

SUITE = Path(__file__).parent / "agent_tasks" / "tasks.json"

PERFECT_TEXT = {
    "fx-01": "cos theta* endpoints clamped to +/-0.999 to avoid the pole.",
    "fx-02": "W is 2.4 MeV above the eta threshold; the integrator may hang, smoke-test first.",
    "fx-03": "phi* = 370 deg mapped to 10 deg.",
    "fx-04": "vcut is negative: EXCLURAD switches to the v interpretation; default is 0.166.",
    "ip-01": "W = 1.2 GeV is below the eta threshold of 1.486 GeV.",
    "ip-02": "W = 1.45 GeV is below the eta+p threshold of 1.486 GeV.",
    "ip-03": "W = 1.05 GeV is below the pi+ n threshold of 1.079 GeV.",
    "ip-04": "Q2 must be positive (spacelike) for electroproduction.",
    "ip-05": "nu = 3.26 GeV exceeds the 2.2 GeV beam energy.",
    "ip-06": "cos theta* = 1.3 is not a cosine; |cos| <= 1.",
}
PERFECT_FLAGS = {"fx-02": ["near_threshold"], "fx-04": ["vcut_negative"]}


def points_of(task: dict, fixed: bool) -> list[KinematicPoint]:
    gt = task["ground_truth"]
    raw = [KinematicPoint(w=p[0], q2=p[1], cos_theta=p[2], phi=p[3])
           for p in gt["verify"]["points"]]
    if not fixed:
        return raw
    if gt.get("required_fix") == "cos_clamped":
        return [KinematicPoint(w=p.w, q2=p.q2, phi=p.phi,
                               cos_theta=max(-0.999, min(0.999, p.cos_theta))) for p in raw]
    if gt.get("required_fix") == "phi_mapped":
        return [KinematicPoint(w=p.w, q2=p.q2, cos_theta=p.cos_theta, phi=p.phi % 360.0)
                for p in raw]
    return raw


def write_run(out: Path, suite: dict, perfect: bool) -> None:
    for task in suite["tasks"]:
        gt = task["ground_truth"]
        d = out / task["id"]
        d.mkdir(parents=True, exist_ok=True)
        ch = get_channel(task["channel"])
        v = gt["verify"]
        beam = v.get("beam_gev", suite["defaults"][task["channel"]]["beam_gev"])
        vcut = v.get("vcut", suite["defaults"][task["channel"]]["vcut"])
        expected = gt["expected_action"]
        if perfect and expected == "refuse":
            outcome = {"action": "refuse", "input_files": [], "flags": [],
                       "explanation": PERFECT_TEXT[task["id"]]}
        else:
            header = InputHeader.for_channel(ch, beam_gev=beam, vcut=vcut)
            res = generate_input_files(header, points_of(task, fixed=perfect), d,
                                       label=task["id"])
            files = [Path(f).name for f in res["files"]] if "files" in res else \
                sorted(p.name for p in d.glob("*.dat"))
            outcome = {"action": expected if perfect else "generate",
                       "input_files": files,
                       "flags": PERFECT_FLAGS.get(task["id"], []) if perfect else [],
                       "explanation": PERFECT_TEXT.get(task["id"], "generated") if perfect else ""}
        (d / "outcome.json").write_text(json.dumps(outcome, indent=2))


def main() -> None:
    out = Path(sys.argv[1])
    suite = json.loads(SUITE.read_text())
    write_run(out / "perfect", suite, perfect=True)
    write_run(out / "naive", suite, perfect=False)
    print(f"wrote {out}/perfect and {out}/naive")


if __name__ == "__main__":
    main()
