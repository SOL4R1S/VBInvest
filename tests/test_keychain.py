from __future__ import annotations

import subprocess

from scripts.lib.keychain import KeychainSecretStore, WindowsCredentialStore, platform_secret_store, resolve_secret
from scripts.lib import config


def test_keychain_store_reads_secret_without_logging_value() -> None:
    calls: list[list[str]] = []

    def runner(command: list[str]) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, stdout="secret-token\n", stderr="")

    store = KeychainSecretStore(runner=runner)

    value = store.get("AI_API_KEY")

    assert value == "secret-token"
    assert calls == [["security", "find-generic-password", "-a", "AI_API_KEY", "-s", "VBinvest", "-w"]]
    assert "secret-token" not in repr(store)


def test_keychain_store_returns_empty_when_secret_is_missing() -> None:
    def runner(command: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 44, stdout="", stderr="not found")

    store = KeychainSecretStore(runner=runner)

    assert store.get("OPENDART_API_KEY") == ""


def test_keychain_store_writes_secret_with_update_flag() -> None:
    calls: list[list[str]] = []

    def runner(command: list[str]) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    store = KeychainSecretStore(runner=runner)

    store.set("POSTGRES_PASSWORD", "db-password")

    assert calls == [
        [
            "security",
            "add-generic-password",
            "-U",
            "-a",
            "POSTGRES_PASSWORD",
            "-s",
            "VBinvest",
            "-w",
            "db-password",
        ]
    ]


def test_resolve_secret_prefers_keychain_on_macos() -> None:
    class FakeStore:
        def get(self, account: str) -> str:
            return "from-keychain" if account == "AI_API_KEY" else ""

    value = resolve_secret(
        {"AI_API_KEY": "from-env"},
        "AI_API_KEY",
        system_name="Darwin",
        store=FakeStore(),
    )

    assert value == "from-keychain"


def test_resolve_secret_keeps_env_fallback_when_keychain_is_empty() -> None:
    class FakeStore:
        def get(self, account: str) -> str:
            return ""

    value = resolve_secret(
        {"OPENAI_API_KEY": "from-env"},
        "AI_API_KEY",
        aliases=("AI_PROVIDER_API_KEY", "OPENAI_API_KEY"),
        system_name="Darwin",
        store=FakeStore(),
    )

    assert value == "from-env"


def test_windows_credential_store_reads_and_writes_secret() -> None:
    class FakeWindowsBackend:
        def __init__(self) -> None:
            self.values: dict[str, str] = {}

        def read(self, target_name: str) -> str:
            return self.values.get(target_name, "")

        def write(self, target_name: str, value: str) -> None:
            self.values[target_name] = value

    backend = FakeWindowsBackend()
    store = WindowsCredentialStore(backend=backend)

    store.set("AI_API_KEY", "windows-secret")

    assert store.get("AI_API_KEY") == "windows-secret"
    assert backend.values == {"VBinvest:AI_API_KEY": "windows-secret"}
    assert "windows-secret" not in repr(store)


def test_platform_secret_store_uses_windows_credential_manager() -> None:
    store = platform_secret_store("Windows")

    assert isinstance(store, WindowsCredentialStore)


def test_resolve_secret_prefers_windows_credential_manager() -> None:
    class FakeStore:
        def get(self, account: str) -> str:
            return "from-windows" if account == "OPENDART_API_KEY" else ""

    value = resolve_secret(
        {"OPENDART_API_KEY": "from-env"},
        "OPENDART_API_KEY",
        system_name="Windows",
        store=FakeStore(),
    )

    assert value == "from-windows"


def test_resolve_opendart_key_prefers_secure_storage() -> None:
    class FakeStore:
        def get(self, account: str) -> str:
            return "from-secure-storage" if account == "OPENDART_API_KEY" else ""

    value = config.resolve_opendart_api_key(
        {"OPENDART_API_KEY": "from-env", "DART_API_KEY": "from-alias"},
        system_name="Darwin",
        store=FakeStore(),
        config_value="from-config",
    )

    assert value == "from-secure-storage"


def test_resolve_opendart_key_accepts_dart_api_key_env_alias() -> None:
    class FakeStore:
        def get(self, account: str) -> str:
            return ""

    value = config.resolve_opendart_api_key(
        {"DART_API_KEY": "from-alias"},
        system_name="Darwin",
        store=FakeStore(),
        config_value="from-config",
    )

    assert value == "from-alias"
