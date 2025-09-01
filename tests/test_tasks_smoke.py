from app.tasks.smoke import ping_db
from app.utils.context import run_with_app


def test_ping_db_ok():
    res = run_with_app(ping_db)
    assert res.get("ok") is True
    assert "ts" in res


def test_run_tasks_error_path(monkeypatch, caplog):
    import run_tasks

    caplog.set_level("ERROR")

    def boom():
        raise RuntimeError("boom")

    monkeypatch.setattr("app.tasks.smoke.ping_db", boom, raising=True)
    code = run_tasks.main()
    assert code == 1
    assert any("fatal" in r.message.lower() for r in caplog.records)
