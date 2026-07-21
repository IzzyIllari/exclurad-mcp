"""Channel registry: the layer that makes the server extendable beyond eta.

Each ChannelConfig encodes what the Fortran hardcodes implicitly — thresholds,
which lookup table a (model, channel) pair actually opens, sane defaults, and
known quirks. Adding a new exclusive channel (e.g. p(e,e'K)Lambda) means adding
an entry here plus its table file, not touching the tool code.
"""

from dataclasses import dataclass, field

# PDG masses [GeV]
M_PROTON = 0.9382720813
M_NEUTRON = 0.9395654205
M_PIPLUS = 0.13957039
M_ETA = 0.547862


@dataclass(frozen=True)
class ChannelConfig:
    key: str
    reaction: str
    description: str
    w_threshold: float          # hadronic threshold W_min = sum of final-state masses [GeV]
    target_mass: float          # struck nucleon mass [GeV]
    ivec_detected_hadron: int   # input.dat `ivec`: 1 = recoil nucleon, 2 = meson
    model: int                  # input.dat model flag: 1 AO, 2 maid98, 3 maid2000-slot
    table_file: str             # filename the Fortran actually opens for this (model, channel)
    table_actual_content: str   # what the table REALLY contains (names are historical aliases)
    default_beam_gev: float
    default_vcut: float
    repo: str
    quirks: tuple[str, ...] = field(default_factory=tuple)


COMMON_QUIRKS = (
    "cos(theta*) must not be exactly +/-1.0; use +/-0.999 (integration fails at the poles)",
    "input files are limited to 10 kinematic points (Fortran reader limit); chunk larger grids",
    "the input format requires two blank lines between the header block and the points block",
    "a trailing '0error detected by nag library routine d01fce - ifail = 2' line appears in "
    "known-good inputs; it is inert but kept for byte-compatibility with validated files",
    "unphysical kinematics can make the integrator hang forever (run with a timeout) or exit "
    "cleanly with no 'tai:' line in stdout (silent N/A) — both must be detected by the runner",
)

CHANNELS: dict[str, ChannelConfig] = {
    "eta": ChannelConfig(
        key="eta",
        reaction="e p -> e' p eta",
        description="Eta electroproduction off the proton (2025/2026 extension, CLAS12 kinematics)",
        w_threshold=M_PROTON + M_ETA,  # ~1.4861 GeV
        target_mass=M_PROTON,
        ivec_detected_hadron=1,  # recoil proton
        model=3,
        table_file="maid07-PPpi.tbl",
        table_actual_content="EtaMAID-2023 multipoles (V. Kashevarov) — the pion filename is kept "
        "because the Fortran hardcodes it; the content is NOT MAID07 pion data",
        default_beam_gev=6.53,
        default_vcut=0.166,
        repo="https://github.com/IzzyIllari/exclurad",
        quirks=COMMON_QUIRKS + (
            "runs near the eta+p threshold (W ~ 1.486 GeV) are the most likely to hang or "
            "return silent N/A; probe with a smoke test first",
        ),
    ),
    "piplus": ChannelConfig(
        key="piplus",
        reaction="e p -> e' n pi+",
        description="Charged-pion electroproduction (original 2002 EXCLURAD, CLAS kinematics)",
        w_threshold=M_NEUTRON + M_PIPLUS,  # ~1.0791 GeV
        target_mass=M_PROTON,
        ivec_detected_hadron=2,  # detected pi+
        model=3,
        table_file="maid07-PPpi.tbl",
        table_actual_content="MAID2007 pion multipoles — the input comment '3: maid2000' is "
        "STALE: in the current source model=3 loads the maid07-*.tbl files "
        "(channel_opt selects PPpi/NPpi/PNpi; model=2 loads maid98; model=1 is "
        "the AO parametrization, no table)",
        default_beam_gev=5.75,
        default_vcut=0.05,
        repo="https://github.com/JeffersonLab/exclurad",
        quirks=COMMON_QUIRKS,
    ),
}


def get_channel(key: str) -> ChannelConfig:
    try:
        return CHANNELS[key]
    except KeyError:
        raise ValueError(
            f"Unknown channel '{key}'. Available: {', '.join(sorted(CHANNELS))}"
        ) from None
