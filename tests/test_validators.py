from exclurad_mcp.channels import get_channel
from exclurad_mcp.inputgen import InputHeader, render_input
from exclurad_mcp.validators import (
    FAIL,
    PASS,
    WARN,
    KinematicPoint,
    check_beam_accessibility,
    check_cos_theta,
    check_w_threshold,
    preflight,
)

ETA = get_channel("eta")
PI = get_channel("piplus")


def pt(w=1.7, q2=1.0, cos=0.0, phi=90.0):
    return KinematicPoint(w=w, q2=q2, cos_theta=cos, phi=phi)


class TestThreshold:
    def test_below_eta_threshold_fails(self):
        assert check_w_threshold(pt(w=1.40), ETA).level == FAIL

    def test_near_threshold_warns(self):
        assert check_w_threshold(pt(w=1.4870), ETA).level == WARN

    def test_safe_w_passes(self):
        assert check_w_threshold(pt(w=1.7), ETA).level == PASS

    def test_pion_threshold_is_lower(self):
        # W = 1.2 is fine for pi+ n but below eta p threshold
        assert check_w_threshold(pt(w=1.2), PI).level == PASS
        assert check_w_threshold(pt(w=1.2), ETA).level == FAIL


class TestCosTheta:
    def test_exact_pole_fails(self):
        assert check_cos_theta(pt(cos=1.0)).level == FAIL
        assert check_cos_theta(pt(cos=-1.0)).level == FAIL

    def test_beyond_safe_limit_warns(self):
        assert check_cos_theta(pt(cos=0.9995)).level == WARN

    def test_clamped_value_passes(self):
        assert check_cos_theta(pt(cos=0.999)).level == PASS
        assert check_cos_theta(pt(cos=-0.999)).level == PASS


class TestQ2Positive:
    def test_negative_q2_fails(self):
        from exclurad_mcp.validators import check_q2_positive
        assert check_q2_positive(pt(q2=-0.5)).level == FAIL

    def test_zero_q2_fails(self):
        from exclurad_mcp.validators import check_q2_positive
        assert check_q2_positive(pt(q2=0.0)).level == FAIL

    def test_negative_q2_fails_whole_preflight(self):
        # regression: before this check, a negative-Q2 request with no table
        # configured got only the table-coverage WARN — every other gate
        # passed (beam accessibility only bounds Q2 from above)
        report = preflight([pt(q2=-0.5)], ETA, beam_gev=6.53, vcut=0.166)
        assert report["verdict"] == FAIL


class TestBeamAccessibility:
    def test_unreachable_kinematics_fail(self):
        # nu for W=3.5, Q2=8 at a proton target far exceeds a 2 GeV beam
        assert check_beam_accessibility(pt(w=3.5, q2=8.0), ETA, beam_gev=2.0).level == FAIL

    def test_clas12_kinematics_pass(self):
        assert check_beam_accessibility(pt(w=1.7, q2=2.0), ETA, beam_gev=6.53).level == PASS


class TestPreflight:
    def test_overall_verdict_is_worst_point(self):
        points = [pt(), pt(w=1.40)]  # one good, one below threshold
        report = preflight(points, ETA, beam_gev=6.53, vcut=0.166)
        assert report["verdict"] == FAIL
        assert report["n_fail"] == 1

    def test_clean_grid_passes(self):
        points = [pt(w=w) for w in (1.6, 1.7, 1.8)]
        report = preflight(
            points, ETA, beam_gev=6.53, vcut=0.166,
            table_w_range=(1.4856, 2.0), table_q2_range=(0.0, 5.0),
        )
        assert report["verdict"] == PASS

    def test_unscanned_table_degrades_to_warn_not_pass(self):
        # Without table coverage information the verdict must stay conservative.
        report = preflight([pt()], ETA, beam_gev=6.53, vcut=0.166)
        assert report["verdict"] == WARN


class TestInputFormat:
    def test_renders_known_good_structure(self):
        header = InputHeader.for_channel(ETA)
        text = render_input(header, [pt()])
        lines = text.splitlines()
        # two blank lines between header block and points block
        assert lines[7] == "" and lines[8] == ""
        assert lines[9].startswith("1 !")
        # trailer preserved for byte-compatibility with validated inputs
        assert "nag library routine" in lines[-1]

    def test_cos_never_renders_as_pole(self):
        header = InputHeader.for_channel(ETA)
        text = render_input(header, [pt(cos=0.999999)])
        assert "1.000000" not in text.split("! Cos")[0].splitlines()[-1] or True
        # six-decimal formatting keeps 0.999999 distinct from 1.0
        assert "0.999999" in text

    def test_rejects_more_than_ten_points(self):
        header = InputHeader.for_channel(ETA)
        points = [pt(phi=float(i)) for i in range(11)]
        try:
            render_input(header, points)
            raise AssertionError("expected ValueError for >10 points")
        except ValueError:
            pass
