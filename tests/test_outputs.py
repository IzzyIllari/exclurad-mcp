from pathlib import Path

from exclurad_mcp.outputs import SCHEMAS, parse_output_file

# Real lines from CLAS12 eta production output (results_Oct2025).
RADTOT_CSV = (
    "    0.0000000000,    1.5753000000,    1.9586000000,    0.3413790000,"
    "   96.0000000000,    0.8976187036,    0.0001675550,    0.3817654467,"
    "    0.4131095281,   -7.5873537974\n"
)


def _write(tmp_path: Path, name: str, text: str) -> Path:
    p = tmp_path / name
    p.write_text(text)
    return p


class TestRadtot:
    def test_parses_real_line(self, tmp_path):
        f = _write(tmp_path, "radtot_sample.dat", RADTOT_CSV)
        r = parse_output_file(f, kind="radtot")
        assert r["n_records"] == 1
        rec = r["records"][0]
        assert rec["e1_unused"] == 0.0  # documented unpopulated column
        assert abs(rec["w"] - 1.5753) < 1e-6
        assert abs(rec["delta"] - 0.8976187036) < 1e-9
        assert abs(rec["asym_rc_pct"] + 7.5873537974) < 1e-9

    def test_kind_inferred_from_parent_dir(self, tmp_path):
        d = tmp_path / "radtot"
        d.mkdir()
        f = _write(d, "grid_00-00-00_W1.5_p01.dat", RADTOT_CSV)
        assert parse_output_file(f)["kind"] == "radtot"


class TestFixedWidth:
    def test_radcor_two_rows_per_point(self, tmp_path):
        # f8.3 fixed-width: one unpolarized + one polarized row
        lines = (
            "   1.487   0.500   0.980   0.999  90.000   0.638   1.000   0.640\n"
            "   1.487   0.500   0.980   0.999  90.000   0.612   1.000   0.615\n"
        )
        f = _write(tmp_path, "radcor_x.dat", lines)
        r = parse_output_file(f, kind="radcor")
        assert r["n_records"] == 2
        assert abs(r["records"][0]["delta"] - 0.638) < 1e-9

    def test_radasm_abutting_fields(self, tmp_path):
        # f6.2 fields can abut with no separator: phi=252.00 fills its field
        line = "  1.66  1.50  0.75  0.50252.00   0.382   0.413  -7.587\n"
        f = _write(tmp_path, "radasm_x.dat", line)
        r = parse_output_file(f, kind="radasm")
        assert r["n_records"] == 1
        rec = r["records"][0]
        assert abs(rec["phi_deg"] - 252.0) < 1e-9
        assert abs(rec["cos_theta"] - 0.50) < 1e-9


class TestSchemas:
    def test_every_kind_has_schema(self):
        assert set(SCHEMAS) == {"radtot", "radcor", "radasm", "radsigpl", "radsigmi", "all", "allu"}

    def test_diagnostic_files_not_column_parsed(self, tmp_path):
        f = _write(tmp_path, "all_x.dat", "program DIFFRAD 1.0\n tai: 1 2 0.5 0.9\n")
        r = parse_output_file(f, kind="all")
        assert r["diagnostic"] is True
        assert r["n_tai_lines"] == 1


class TestPionVariant:
    def test_pion_radtot_fixed_width_autodetected(self, tmp_path):
        # upstream pion build: 7 columns, '5f6.2,5F8.3', no commas
        line = "  0.00  1.23  0.40  0.00 90.00   1.083  -4.523\n"
        f = _write(tmp_path, "radtot_pion.dat", line)
        r = parse_output_file(f, kind="radtot")  # build='auto'
        assert r["n_records"] == 1
        assert "sigma_born" not in r["records"][0]  # pion schema, not eta
        assert abs(r["records"][0]["delta"] - 1.083) < 1e-9

    def test_eta_csv_autodetected(self, tmp_path):
        f = _write(tmp_path, "radtot_eta.dat", RADTOT_CSV)
        r = parse_output_file(f, kind="radtot", build="auto")
        assert "sigma_born" in r["records"][0]  # 10-column eta schema

    def test_explicit_build_overrides_sniffing(self, tmp_path):
        f = _write(tmp_path, "radtot_x.dat", RADTOT_CSV)
        r = parse_output_file(f, kind="radtot", build="pion")
        assert r["n_records"] == 0  # CSV lines don't parse under the pion schema


class TestCoverageMap:
    def test_dead_cells_are_rasterized(self):
        from exclurad_mcp.outputs import coverage_map
        # 2x2 grid design, but cell (w=2, q2=2) produced NO output at all
        recs = [
            {"w": 1.0, "q2": 1.0, "cos_theta": c, "phi_deg": p}
            for c in (0.0, 0.5) for p in (0.0, 90.0)
        ] + [
            {"w": 2.0, "q2": 1.0, "cos_theta": 0.0, "phi_deg": 0.0},
            {"w": 1.0, "q2": 2.0, "cos_theta": 0.0, "phi_deg": 0.0},
        ]
        cov = coverage_map(recs, expected_per_cell=4)
        assert cov["n_cells"] == 4  # full cartesian grid, not just observed cells
        dead = [c for c in cov["cells"] if c["w"] == 2.0 and c["q2"] == 2.0]
        assert dead and dead[0]["n_present"] == 0 and dead[0]["n_missing"] == 4
        assert cov["total_missing_points"] == 4 + 3 + 3

    def test_expected_defaults_to_max_observed(self):
        from exclurad_mcp.outputs import coverage_map
        recs = [
            {"w": 1.0, "q2": 1.0, "cos_theta": c, "phi_deg": 0.0} for c in (0.0, 0.5)
        ] + [{"w": 2.0, "q2": 1.0, "cos_theta": 0.0, "phi_deg": 0.0}]
        cov = coverage_map(recs)
        assert cov["expected_per_cell"] == 2
        assert cov["total_missing_points"] == 1
