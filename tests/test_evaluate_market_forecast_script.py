from __future__ import annotations

import json

from scripts import evaluate_market_forecast


def test_evaluate_script_loads_local_env_file_without_overriding(tmp_path, monkeypatch, capsys):
    (tmp_path / ".env").write_text(
        "SUPABASE_URL=https://fixture.supabase.co\nSUPABASE_SECRET_KEY=sb_secret_from_file\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("PYTHON_DOTENV_DISABLED", raising=False)
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.setenv("SUPABASE_SECRET_KEY", "sb_secret_already_set")
    seen: dict[str, str] = {}

    class Store:
        def read_history(self, symbol: str, *, limit: int):
            return []

    def from_env():
        import os

        seen["url"] = os.environ["SUPABASE_URL"]
        seen["key"] = os.environ["SUPABASE_SECRET_KEY"]
        return Store()

    monkeypatch.setattr(evaluate_market_forecast.SupabaseDailyBarStore, "from_env", staticmethod(from_env))

    assert evaluate_market_forecast.main(["--symbol", "INFY"]) == 0

    assert seen == {"url": "https://fixture.supabase.co", "key": "sb_secret_already_set"}
    result = json.loads(capsys.readouterr().out)
    assert result["INFY"]["status"] == "insufficient_history"
    assert result["INFY"]["release_eligible"] is False
