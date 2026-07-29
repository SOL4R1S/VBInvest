"""AI provider configuration and HTTP transport.

Response parsing/validation lives in ai_response.py.
"""

from __future__ import annotations

import json
import socket
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Mapping, Protocol, TypeAlias

from scripts.lib.keychain import SecretStore, resolve_secret
from scripts.lib.ai_response import (
    AIProviderError,
    JsonValue,
    extract_content_json,
    json_safe_payload,
    system_prompt,
)

__all__ = [
    "AIProviderConfig",
    "AIProviderConfigError",
    "AIProviderError",
    "OpenAICompatibleResearchClient",
    "build_research_ai_client_from_env",
]


class AIProviderConfigError(RuntimeError):
    pass


class HttpResponse(Protocol):
    def __enter__(self) -> "HttpResponse":
        ...

    def __exit__(self, exc_type, exc, traceback) -> bool:
        ...

    def read(self) -> bytes:
        ...


class UrlOpen(Protocol):
    def __call__(self, request: urllib.request.Request, *, timeout: int) -> HttpResponse:
        ...


@dataclass(frozen=True, slots=True)
class AIProviderConfig:
    name: str
    api_key: str = field(repr=False)
    base_url: str
    model: str
    timeout_seconds: int = 30

    @staticmethod
    def from_env(
        env: Mapping[str, str],
        *,
        system_name: str | None = None,
        secret_store: SecretStore | None = None,
    ) -> "AIProviderConfig | None":
        api_key = resolve_secret(
            env,
            "AI_API_KEY",
            aliases=("AI_PROVIDER_API_KEY", "DEEPSEEK_API_KEY", "OPENAI_API_KEY"),
            system_name=system_name,
            store=secret_store,
        )
        model = _first_env(env, "AI_PROVIDER_MODEL", "DEEPSEEK_MODEL", "OPENAI_MODEL")
        base_url = _first_env(env, "AI_PROVIDER_BASE_URL", "DEEPSEEK_BASE_URL", "OPENAI_BASE_URL")
        provider_name = _first_env(env, "AI_PROVIDER_NAME") or _provider_name(env)
        if not api_key and not model and not base_url and not _first_env(env, "AI_PROVIDER_NAME"):
            return None
        if not model:
            raise AIProviderConfigError("AI_PROVIDER_MODEL is required when an AI provider API key is set")
        base_url = base_url or _default_base_url(env)
        normalized_base_url = base_url.rstrip("/")
        if not api_key and not _is_keyless_local_provider(provider_name, normalized_base_url):
            raise AIProviderConfigError("AI provider API key is required for non-local providers")
        return AIProviderConfig(
            name=provider_name,
            api_key=api_key,
            base_url=normalized_base_url,
            model=model,
            timeout_seconds=_timeout_seconds(env, provider_name, normalized_base_url),
        )


class OpenAICompatibleResearchClient:
    _max_tokens = 1024
    _local_max_tokens = 2048

    def __init__(self, config: AIProviderConfig, *, urlopen: UrlOpen = urllib.request.urlopen) -> None:
        self._config = config
        self._urlopen = urlopen

    @property
    def provider_name(self) -> str:
        return self._config.name

    def generate_research(
        self,
        asset: dict[str, JsonValue],
        latest: dict[str, JsonValue],
        packet: dict[str, JsonValue],
    ) -> dict[str, JsonValue]:
        body = _build_request_payload(self._config)
        try:
            body["messages"] = [
                {"role": "system", "content": system_prompt()},
                {
                    "role": "user",
                    "content": json.dumps(
                        json_safe_payload({"asset": asset, "latest": latest, "packet": packet}),
                        ensure_ascii=False,
                        allow_nan=False,
                    ),
                },
            ]
        except TypeError as exc:
            raise AIProviderError("AI provider request payload is not JSON-serializable") from exc

        headers = {
            "Content-Type": "application/json",
            "User-Agent": "VBinvest/0.1",
        }
        if self._config.api_key:
            headers["Authorization"] = f"Bearer {self._config.api_key}"

        try:
            payload = self._request_json(body, headers)
        except urllib.error.HTTPError as exc:
            if exc.code == 401:
                raise AIProviderConfigError("AI provider authentication failed. Verify API credentials.") from exc
            if exc.code == 429:
                raise AIProviderError("AI provider is rate limited. Retry after a short interval.") from exc
            if (
                exc.code == 400
                and body.get("response_format") is not None
                and _is_unsupported_response_format_error(exc)
            ):
                fallback_body = dict(body)
                fallback_body.pop("response_format", None)
                try:
                    payload = self._request_json(fallback_body, headers)
                except urllib.error.HTTPError as fallback_exc:
                    raise AIProviderError(f"{self._config.name}: chat completion failed with HTTP {fallback_exc.code}") from fallback_exc
            else:
                raise AIProviderError(f"{self._config.name}: chat completion failed with HTTP {exc.code}") from exc
        draft = extract_content_json(
            payload,
            repair_local_model=_is_keyless_local_provider(self._config.name, self._config.base_url),
        )
        draft["model_provider"] = self._config.name
        draft["model_name"] = self._config.model
        return draft

    def _request_json(
        self,
        body: dict[str, JsonValue],
        headers: dict[str, str],
    ) -> dict[str, JsonValue]:
        request = urllib.request.Request(
            f"{self._config.base_url}/chat/completions",
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with self._urlopen(request, timeout=self._config.timeout_seconds) as response:
                raw = response.read()
        except (socket.timeout, TimeoutError):
            raise AIProviderError("AI provider request timed out") from None
        except urllib.error.HTTPError:
            raise
        except urllib.error.URLError as exc:
            raise AIProviderError(f"{self._config.name}: chat completion request failed: {exc}") from exc
        try:
            return json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise AIProviderError("AI provider response is not valid JSON") from exc


def build_research_ai_client_from_env(env: Mapping[str, str]) -> OpenAICompatibleResearchClient | None:
    config = AIProviderConfig.from_env(env)
    return None if config is None else OpenAICompatibleResearchClient(config)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_request_payload(config: AIProviderConfig) -> dict[str, JsonValue]:
    body: dict[str, JsonValue] = {
        "model": config.model,
        "max_tokens": _max_tokens(config),
        "temperature": 0.2,
    }
    if _supports_structured_output(config):
        body["response_format"] = {"type": "json_object"}
    return body


def _first_env(env: Mapping[str, str], *keys: str) -> str:
    for key in keys:
        value = env.get(key, "").strip()
        if value:
            return value
    return ""


def _provider_name(env: Mapping[str, str]) -> str:
    if env.get("AI_API_KEY"):
        return "openai-compatible"
    if env.get("DEEPSEEK_API_KEY"):
        return "deepseek"
    if env.get("OPENAI_API_KEY"):
        return "openai"
    return "openai-compatible"


def _default_base_url(env: Mapping[str, str]) -> str:
    if env.get("DEEPSEEK_API_KEY"):
        return "https://api.deepseek.com"
    if env.get("OPENAI_API_KEY"):
        return "https://api.openai.com/v1"
    raise AIProviderConfigError("AI_PROVIDER_BASE_URL is required for custom AI providers")


def _supports_structured_output(config: AIProviderConfig) -> bool:
    if config.name.strip().lower() == "ollama":
        return False
    return not _is_keyless_local_provider(config.name, config.base_url)


def _is_keyless_local_provider(provider_name: str, base_url: str) -> bool:
    if provider_name.strip().lower() == "ollama":
        return True
    host = urllib.parse.urlparse(base_url).hostname
    return host in {"localhost", "127.0.0.1", "::1"}


def _max_tokens(config: AIProviderConfig) -> int:
    if _is_keyless_local_provider(config.name, config.base_url):
        return OpenAICompatibleResearchClient._local_max_tokens
    return OpenAICompatibleResearchClient._max_tokens


def _is_unsupported_response_format_error(exc: urllib.error.HTTPError) -> bool:
    try:
        body = exc.read().decode("utf-8").lower()
    except (UnicodeDecodeError, OSError):
        return False
    return "response_format" in body and "unsupported" in body


def _timeout_seconds(env: Mapping[str, str], provider_name: str, base_url: str) -> int:
    default = "90" if _is_keyless_local_provider(provider_name, base_url) else "30"
    raw = env.get("AI_PROVIDER_TIMEOUT_SECONDS", default).strip()
    try:
        value = int(raw)
    except ValueError as exc:
        raise AIProviderConfigError("AI_PROVIDER_TIMEOUT_SECONDS must be an integer") from exc
    if value <= 0 or value > 120:
        raise AIProviderConfigError("AI_PROVIDER_TIMEOUT_SECONDS must be between 1 and 120")
    return value
