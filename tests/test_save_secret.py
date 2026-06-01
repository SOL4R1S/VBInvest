from __future__ import annotations

from scripts import save_secret


def test_save_secret_cli_ignores_missing_env_without_logging_secret(monkeypatch) -> None:
    saved: dict[str, str] = {}

    class FakeStore:
        def set(self, account: str, value: str) -> None:
            saved[account] = value

    monkeypatch.delenv("AI_API_KEY", raising=False)

    exit_code = save_secret.main(["AI_API_KEY"], environ={}, store=FakeStore())

    assert exit_code == 0
    assert saved == {}


def test_save_secret_cli_saves_named_env_to_platform_store() -> None:
    saved: dict[str, str] = {}

    class FakeStore:
        def set(self, account: str, value: str) -> None:
            saved[account] = value

    exit_code = save_secret.main(["OPENDART_API_KEY"], environ={"OPENDART_API_KEY": "dart-secret"}, store=FakeStore())

    assert exit_code == 0
    assert saved == {"OPENDART_API_KEY": "dart-secret"}
