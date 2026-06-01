from __future__ import annotations

import os
import platform
import tomllib
from dataclasses import dataclass, replace
from enum import StrEnum
from pathlib import Path
from typing import Mapping
from urllib.parse import urlsplit, urlunsplit

from scripts.lib.keychain import SecretStore, SecretWriteStore, platform_secret_store, resolve_secret


type TomlScalar = str | bool | int | float
type TomlValue = TomlScalar | dict[str, TomlValue]
type TomlTable = dict[str, TomlValue]
type RedactedValue = str | bool | dict[str, "RedactedValue"]


class ConfigError(Exception):
    def __init__(self, field: str, reason: str):
        self.field = field
        self.reason = reason
        super().__init__(f"{field}: {reason}")


class DatabaseMode(StrEnum):
    SQLITE = "sqlite"
    POSTGRES_DOCKER = "postgres_docker"
    POSTGRES_URL = "postgres_url"


class ExportMode(StrEnum):
    DIRECT = "direct"
    SYMLINK = "symlink"


@dataclass(frozen=True, slots=True)
class DatabaseSettings:
    mode: DatabaseMode
    sqlite_path: Path
    postgres_url: str

    def redacted(self) -> dict[str, RedactedValue]:
        return {
            "mode": self.mode.value,
            "sqlite_path": str(self.sqlite_path),
            "postgres_url": redact_url_password(self.postgres_url),
        }


@dataclass(frozen=True, slots=True)
class ObsidianSettings:
    vault_path: Path | None
    export_mode: ExportMode

    def redacted(self) -> dict[str, RedactedValue]:
        return {
            "vault_path": "" if self.vault_path is None else str(self.vault_path),
            "export_mode": self.export_mode.value,
        }


@dataclass(frozen=True, slots=True)
class ProviderSettings:
    opendart_api_key: str
    ai_base_url: str
    ai_api_key: str

    def redacted(self) -> dict[str, RedactedValue]:
        return {
            "opendart_api_key": redact_secret(self.opendart_api_key),
            "ai_base_url": self.ai_base_url,
            "ai_api_key": redact_secret(self.ai_api_key),
        }


@dataclass(frozen=True, slots=True)
class LocalConfig:
    first_run_completed: bool
    language: str
    database: DatabaseSettings
    obsidian: ObsidianSettings
    providers: ProviderSettings

    def redacted(self) -> dict[str, RedactedValue]:
        return {
            "first_run_completed": self.first_run_completed,
            "language": self.language,
            "database": self.database.redacted(),
            "obsidian": self.obsidian.redacted(),
            "providers": self.providers.redacted(),
        }


def load_local_config(
    config_path: Path | None = None,
    environ: Mapping[str, str] | None = None,
    system_name: str | None = None,
    secret_store: SecretStore | None = None,
) -> LocalConfig:
    env = os.environ if environ is None else environ
    path = config_path or config_path_from_env(env)
    raw = _read_toml(path)
    app_dir = path.parent
    database = _parse_database(_table(raw, "database"), app_dir)
    obsidian = _parse_obsidian(_table(raw, "obsidian"))
    providers = _parse_providers(_table(raw, "providers"), env, system_name=system_name, secret_store=secret_store)
    return LocalConfig(
        first_run_completed=_bool(raw, "first_run_completed", False),
        language=_text(raw, "language", "ko"),
        database=database,
        obsidian=obsidian,
        providers=providers,
    )


def write_local_config(
    config: LocalConfig,
    config_path: Path,
    *,
    system_name: str | None = None,
    secret_store: SecretWriteStore | None = None,
) -> None:
    persisted_config = config
    system = system_name or platform.system()
    if system in {"Darwin", "Windows"}:
        store = secret_store or platform_secret_store(system)
        _save_provider_secrets(config.providers, store)
        persisted_config = replace(
            config,
            providers=replace(config.providers, opendart_api_key="", ai_api_key=""),
        )
    config_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = config_path.with_name(f".{config_path.name}.tmp")
    temp_path.write_text(_to_toml(persisted_config), encoding="utf-8")
    temp_path.chmod(0o600)
    os.replace(temp_path, config_path)
    config_path.chmod(0o600)


def _save_provider_secrets(providers: ProviderSettings, store: SecretWriteStore) -> None:
    if providers.opendart_api_key:
        store.set("OPENDART_API_KEY", providers.opendart_api_key)
    if providers.ai_api_key:
        store.set("AI_API_KEY", providers.ai_api_key)


def config_path_from_env(environ: Mapping[str, str]) -> Path:
    configured = environ.get("VBINVEST_CONFIG_PATH")
    if configured:
        return Path(configured).expanduser()
    return app_data_dir() / "config.toml"


def app_data_dir(system_name: str | None = None, home: Path | None = None) -> Path:
    base_home = home or Path.home()
    system = system_name or platform.system()
    match system:
        case "Darwin":
            return base_home / "Library" / "Application Support" / "VBinvest"
        case "Windows":
            return Path(os.environ.get("APPDATA") or base_home / "AppData" / "Roaming") / "VBinvest"
        case _:
            return base_home / ".local" / "share" / "vbinvest"


def redact_secret(value: str) -> str:
    return "<redacted>" if value else ""


def redact_url_password(value: str) -> str:
    if not value:
        return ""
    parsed = urlsplit(value)
    if not parsed.password:
        return value
    username = parsed.username or ""
    host = parsed.hostname or ""
    port = "" if parsed.port is None else f":{parsed.port}"
    netloc = f"{username}:***@{host}{port}"
    return urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment))


def _read_toml(path: Path) -> TomlTable:
    if not path.exists():
        return {}
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError("config", "invalid TOML") from exc


def _parse_database(raw: TomlTable, app_dir: Path) -> DatabaseSettings:
    mode = _enum(DatabaseMode, _text(raw, "mode", DatabaseMode.SQLITE.value), "database.mode")
    sqlite_path = Path(_text(raw, "sqlite_path", str(app_dir / "vbinvest.sqlite3"))).expanduser()
    if sqlite_path.exists() and sqlite_path.is_dir():
        raise ConfigError("database.sqlite_path", "must be a file path")
    postgres_url = _text(raw, "postgres_url", "")
    if mode is DatabaseMode.POSTGRES_URL and not postgres_url:
        raise ConfigError("database.postgres_url", "is required for postgres_url mode")
    return DatabaseSettings(mode=mode, sqlite_path=sqlite_path, postgres_url=postgres_url)


def _parse_obsidian(raw: TomlTable) -> ObsidianSettings:
    export_mode = _enum(ExportMode, _text(raw, "export_mode", ExportMode.DIRECT.value), "obsidian.export_mode")
    vault_text = _text(raw, "vault_path", "")
    vault_path = Path(vault_text).expanduser() if vault_text else None
    if vault_path is not None and not vault_path.exists():
        raise ConfigError("obsidian.vault_path", "does not exist")
    return ObsidianSettings(vault_path=vault_path, export_mode=export_mode)


def _parse_providers(
    raw: TomlTable,
    environ: Mapping[str, str],
    *,
    system_name: str | None,
    secret_store: SecretStore | None,
) -> ProviderSettings:
    ai_base_url = _text(raw, "ai_base_url", environ.get("AI_PROVIDER_BASE_URL", ""))
    if ai_base_url:
        parsed = urlsplit(ai_base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ConfigError("providers.ai_base_url", "must be an http(s) URL")
    return ProviderSettings(
        opendart_api_key=resolve_secret(
            environ,
            "OPENDART_API_KEY",
            system_name=system_name,
            store=secret_store,
        )
        or _text(raw, "opendart_api_key", ""),
        ai_base_url=ai_base_url,
        ai_api_key=resolve_secret(
            environ,
            "AI_API_KEY",
            aliases=("AI_PROVIDER_API_KEY", "OPENAI_API_KEY", "DEEPSEEK_API_KEY"),
            system_name=system_name,
            store=secret_store,
        )
        or _text(raw, "ai_api_key", ""),
    )


def _table(raw: TomlTable, name: str) -> TomlTable:
    value = raw.get(name, {})
    if isinstance(value, dict):
        return value
    raise ConfigError(name, "must be a table")


def _text(raw: TomlTable, name: str, default: str) -> str:
    value = raw.get(name, default)
    if isinstance(value, str):
        return value
    raise ConfigError(name, "must be a string")


def _bool(raw: TomlTable, name: str, default: bool) -> bool:
    value = raw.get(name, default)
    if isinstance(value, bool):
        return value
    raise ConfigError(name, "must be a boolean")


def _enum[T: StrEnum](enum_type: type[T], value: str, field: str) -> T:
    try:
        return enum_type(value)
    except ValueError as exc:
        raise ConfigError(field, f"unsupported value {value!r}") from exc


def _to_toml(config: LocalConfig) -> str:
    lines = [
        f"first_run_completed = {_toml_bool(config.first_run_completed)}",
        f'language = "{config.language}"',
        "[database]",
        f'mode = "{config.database.mode.value}"',
        f'sqlite_path = "{config.database.sqlite_path}"',
        f'postgres_url = "{config.database.postgres_url}"',
        "[obsidian]",
        f'vault_path = "{"" if config.obsidian.vault_path is None else config.obsidian.vault_path}"',
        f'export_mode = "{config.obsidian.export_mode.value}"',
        "[providers]",
        f'opendart_api_key = "{config.providers.opendart_api_key}"',
        f'ai_base_url = "{config.providers.ai_base_url}"',
        f'ai_api_key = "{config.providers.ai_api_key}"',
    ]
    return "\n".join(lines) + "\n"


def _toml_bool(value: bool) -> str:
    return "true" if value else "false"
