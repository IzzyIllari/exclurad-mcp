import json
from pathlib import Path

import pytest

from exclurad_mcp.buildgen import (
    TEMPLATE_DIR,
    build_template,
    generate_source,
    list_slots,
    weave,
)

ETA_SRC = "line one\n      ot=1d-3\nline three\n      DATA XM /.54786/\nend\n"
PION_SRC = "line one\n      ot=1d-2\nline three\n      DATA XM /.1395/\nend\n"
ANN = [
    {"name": "tolerance", "description": "integration tolerance",
     "accepted_values": {"eta": "1d-3", "pion": "1d-2"}},
    {"name": "mass", "description": "meson mass",
     "accepted_values": {"eta": "0.54786", "pion": "0.1395"}},
]


class TestWeaver:
    def test_roundtrip_both_channels(self, tmp_path):
        template, slots = build_template(ETA_SRC, PION_SRC, ANN)
        assert template.count("@@SLOT") == 2
        (tmp_path / "f.F.template").write_text(template)
        (tmp_path / "slots.json").write_text(
            json.dumps({"files": ["f.F"], "slots": {"f.F": slots}})
        )
        assert generate_source("eta", tmp_path)["f.F"] == ETA_SRC
        assert generate_source("pion", tmp_path)["f.F"] == PION_SRC

    def test_annotation_count_mismatch_raises(self):
        with pytest.raises(ValueError, match="differing regions"):
            build_template(ETA_SRC, PION_SRC, ANN[:1])

    def test_unknown_channel_raises(self, tmp_path):
        template, slots = build_template(ETA_SRC, PION_SRC, ANN)
        (tmp_path / "f.F.template").write_text(template)
        (tmp_path / "slots.json").write_text(
            json.dumps({"files": ["f.F"], "slots": {"f.F": slots}})
        )
        with pytest.raises(ValueError, match="kaon"):
            generate_source("kaon", tmp_path)

    def test_weave_marks_common_and_slots(self):
        segs = weave(ETA_SRC.splitlines(keepends=True), PION_SRC.splitlines(keepends=True))
        kinds = [s[0] for s in segs]
        assert kinds.count("slot") == 2
        assert kinds[0] == "common"


class TestShippedTemplates:
    """The real EXCLURAD templates shipped with the package."""

    def test_templates_exist(self):
        assert (TEMPLATE_DIR / "slots.json").exists()
        assert (TEMPLATE_DIR / "exclurad.F.template").exists()
        assert (TEMPLATE_DIR / "mpintp.inc.template").exists()

    def test_sixteen_slots_documented(self):
        slots = list_slots()
        assert len(slots) == 16
        names = {s["name"] for s in slots}
        # the four meson-mass sites must all be tracked
        assert {"meson_mass_amhad", "meson_mass_born_1",
                "meson_mass_born_2", "meson_mass_born_3"} <= names
        assert all(s["description"] for s in slots)

    def test_generates_valid_fortran_for_both_channels(self):
        for ch in ("eta", "pion"):
            src = generate_source(ch)
            assert "@@SLOT" not in src["exclurad.F"]
            assert "@@SLOT" not in src["mpintp.inc"]
            assert "PARAMETER( NVAR1" in src["mpintp.inc"]
        # the physics actually differs between the two generations
        assert "0.54786" in generate_source("eta")["exclurad.F"]
        assert "0.13957" in generate_source("pion")["exclurad.F"]
