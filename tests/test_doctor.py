from contextzero.doctor import run_doctor


def test_doctor_detects_missing_setup(tmp_path):
    result = run_doctor(tmp_path, brain_enabled=True, db_path=tmp_path / "missing.db")

    assert result["ok"] is False
    assert result["checks"][".contextzero exists"]["ok"] is False
    assert result["checks"]["Caveman Brain database exists"]["ok"] is False
