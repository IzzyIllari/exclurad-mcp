

class TestRcMode:
    def test_named_modes_resolve(self):
        from exclurad_mcp.inputgen import resolve_rc_mode
        assert resolve_rc_mode("full") == 0
        assert resolve_rc_mode("leading_log") == 1
        assert resolve_rc_mode("leading-log") == 1
        assert resolve_rc_mode(0) == 0 and resolve_rc_mode(1) == 1

    def test_bad_mode_rejected(self):
        from exclurad_mcp.inputgen import resolve_rc_mode
        import pytest
        with pytest.raises(ValueError):
            resolve_rc_mode("exact")
        with pytest.raises(ValueError):
            resolve_rc_mode(2)
