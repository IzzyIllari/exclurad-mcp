

class TestRcModeAwareClassification:
    def test_input_rc_mode_reads_the_second_record(self, tmp_path):
        from exclurad_mcp.runner import input_rc_mode
        from exclurad_mcp.channels import get_channel
        from exclurad_mcp.inputgen import InputHeader, render_input
        from exclurad_mcp.validators import KinematicPoint
        ch = get_channel("eta")
        pts = [KinematicPoint(w=1.6, q2=1.0, cos_theta=0.5, phi=90.0)]
        for name, expected in (("full", 0), ("leading_log", 1)):
            f = tmp_path / f"{name}.dat"
            f.write_text(render_input(InputHeader.for_channel(ch, rc_mode=name), pts))
            assert input_rc_mode(f) == expected

    def test_leading_log_is_not_reported_as_silent_na(self, tmp_path):
        """A leading-log run never prints 'tai:'; before 2026-09-10 that made
        every successful one look like the silent-N/A failure mode."""
        from exclurad_mcp import runner
        from exclurad_mcp.channels import get_channel
        from exclurad_mcp.inputgen import InputHeader, render_input
        from exclurad_mcp.validators import KinematicPoint
        ch = get_channel("eta")
        pts = [KinematicPoint(w=1.6, q2=1.0, cos_theta=0.5, phi=90.0)]
        work = tmp_path / "work"
        work.mkdir()
        inp = tmp_path / "in.dat"
        inp.write_text(render_input(InputHeader.for_channel(ch, rc_mode="leading_log"), pts))
        # a stub "executable" that writes outputs but prints no 'tai:' line
        exe = tmp_path / "fake_exclurad"
        exe.write_text("#!/bin/sh\necho ' npoi= 1 data points'\n"
                       "for k in all allu radasm radcor radsigmi radsigpl radtot; do "
                       "echo '0.0, 1.6, 1.0, 0.5, 90.0, 0.9, 0.006' > $k.dat; done\n")
        exe.chmod(0o755)
        out = runner.run_input_file(exe, inp, work, tmp_path / "results")
        assert out.status == runner.OK
        assert out.rc_mode == "leading_log"

    def test_full_mode_without_tai_is_still_silent_na(self, tmp_path):
        from exclurad_mcp import runner
        from exclurad_mcp.channels import get_channel
        from exclurad_mcp.inputgen import InputHeader, render_input
        from exclurad_mcp.validators import KinematicPoint
        ch = get_channel("eta")
        pts = [KinematicPoint(w=1.6, q2=1.0, cos_theta=0.5, phi=90.0)]
        work = tmp_path / "work"
        work.mkdir()
        inp = tmp_path / "in.dat"
        inp.write_text(render_input(InputHeader.for_channel(ch, rc_mode="full"), pts))
        exe = tmp_path / "fake_exclurad"
        exe.write_text("#!/bin/sh\necho ' npoi= 1 data points'\n")
        exe.chmod(0o755)
        out = runner.run_input_file(exe, inp, work, tmp_path / "results")
        assert out.status == runner.NO_TAI
