from __future__ import annotations

import json
import math
import socket
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Mapping, Protocol, TypeAlias, cast

from scripts.lib.keychain import SecretStore, resolve_secret


JsonValue: TypeAlias = str | int | float | bool | None | list["JsonValue"] | dict[str, "JsonValue"]


class AIProviderError(RuntimeError):
    pass


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
                {"role": "system", "content": _system_prompt()},
                {
                    "role": "user",
                    "content": json.dumps(
                        _json_safe_payload({"asset": asset, "latest": latest, "packet": packet}),
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
        draft = _extract_content_json(
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


def _build_request_payload(config: AIProviderConfig) -> dict[str, JsonValue]:
    body: dict[str, JsonValue] = {
        "model": config.model,
        "max_tokens": _max_tokens(config),
        "temperature": 0.2,
    }
    if _supports_structured_output(config):
        body["response_format"] = {"type": "json_object"}
    return body


def _extract_content_json(payload: JsonValue, *, repair_local_model: bool = False) -> dict[str, JsonValue]:
    if not isinstance(payload, dict):
        raise AIProviderError("AI provider response must be a JSON object")
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise AIProviderError("AI provider response is missing choices")
    first = choices[0]
    if not isinstance(first, dict):
        raise AIProviderError("AI provider response choice must be an object")
    message = first.get("message")
    if not isinstance(message, dict):
        raise AIProviderError("AI provider response is missing message")
    content = message.get("content")
    if not isinstance(content, str):
        raise AIProviderError("AI provider response content is not text")
    if content.strip() == "":
        raise _empty_content_error(first, message)
    draft = _parse_content_json_object(content)
    if not isinstance(draft, dict):
        raise AIProviderError("AI provider response JSON must be an object")
    return _validate_draft_schema(_normalize_draft_schema(draft, repair_local_model=repair_local_model))


def _json_safe_payload(value: object) -> JsonValue:
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, str | int | bool) or value is None:
        return value
    if isinstance(value, list):
        return [_json_safe_payload(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_safe_payload(child) for key, child in value.items()}
    return cast(JsonValue, value)


def _parse_content_json_object(content: str) -> JsonValue:
    try:
        return json.loads(content)
    except json.JSONDecodeError as direct_exc:
        decoder = json.JSONDecoder()
        for start_index, character in enumerate(content):
            if character != "{":
                continue
            try:
                value, _ = decoder.raw_decode(content[start_index:])
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                return value
        raise AIProviderError("AI provider response content is not valid JSON") from direct_exc


def _empty_content_error(choice: dict[str, JsonValue], message: dict[str, JsonValue]) -> AIProviderError:
    reasoning = _first_text_field(message, "reasoning", "reasoning_content")
    if reasoning:
        return AIProviderError(
            "AI provider returned reasoning-only output without JSON content. "
            "Choose a non-reasoning local model or disable thinking mode."
        )
    finish_reason = choice.get("finish_reason")
    if finish_reason == "length":
        return AIProviderError(
            "AI provider stopped before JSON content was produced. Increase output token limit or choose a smaller model."
        )
    return AIProviderError("AI provider response content is empty")


def _first_text_field(record: dict[str, JsonValue], *keys: str) -> str:
    for key in keys:
        value = record.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return ""


def _validate_draft_schema(draft: dict[str, JsonValue]) -> dict[str, JsonValue]:
    required_fields = ("opinion", "thesis", "rationale", "bull", "base", "bear", "risks", "triggers", "confidence")
    for key in required_fields:
        if key not in draft:
            raise AIProviderError(f"AI provider response schema is missing required field: {key}")

    if not isinstance(draft["opinion"], str) or not draft["opinion"].strip():
        raise AIProviderError("AI provider response schema requires a non-empty string: opinion")
    if not isinstance(draft["thesis"], str) or not draft["thesis"].strip():
        raise AIProviderError("AI provider response schema requires a non-empty string: thesis")
    if not _is_string_list(draft["rationale"]):
        raise AIProviderError("AI provider response schema requires a list of strings: rationale")
    if not isinstance(draft["bull"], str) or not draft["bull"].strip():
        raise AIProviderError("AI provider response schema requires a non-empty string: bull")
    if not isinstance(draft["base"], str) or not draft["base"].strip():
        raise AIProviderError("AI provider response schema requires a non-empty string: base")
    if not isinstance(draft["bear"], str) or not draft["bear"].strip():
        raise AIProviderError("AI provider response schema requires a non-empty string: bear")
    if not _is_string_list(draft["risks"]):
        raise AIProviderError("AI provider response schema requires a list of strings: risks")
    if not _is_string_list(draft["triggers"]):
        raise AIProviderError("AI provider response schema requires a list of strings: triggers")
    confidence = draft["confidence"]
    if not isinstance(confidence, int | float) or isinstance(confidence, bool):
        raise AIProviderError("AI provider response schema requires numeric confidence")
    return draft


def _normalize_draft_schema(draft: dict[str, JsonValue], *, repair_local_model: bool) -> dict[str, JsonValue]:
    normalized = dict(draft)
    if repair_local_model:
        _backfill_scenario_fields(normalized)
        _backfill_list_fields(normalized)
    if repair_local_model and "confidence" not in normalized:
        normalized["confidence"] = 0.5
    for key in ("rationale", "risks", "triggers"):
        value = normalized.get(key)
        if isinstance(value, str) and value.strip():
            normalized[key] = [value.strip()]
    confidence = normalized.get("confidence")
    if isinstance(confidence, str):
        normalized["confidence"] = _normalize_confidence(confidence)
    return normalized


def _backfill_scenario_fields(draft: dict[str, JsonValue]) -> None:
    defaults = {
        "bull": "제공된 가격·지표와 공개 소스가 개선될 때의 강세 시나리오입니다.",
        "base": "현재 제공된 자료를 기준으로 한 기준 시나리오입니다.",
        "bear": "지표 둔화나 소스 공백이 이어질 때의 약세 시나리오입니다.",
    }
    for key, fallback in defaults.items():
        value = draft.get(key)
        if _is_string_list(value):
            draft[key] = " / ".join(value)
            continue
        if not isinstance(value, str) or not value.strip():
            draft[key] = fallback


def _backfill_list_fields(draft: dict[str, JsonValue]) -> None:
    defaults = {
        "rationale": ["제공된 가격·지표와 공개 소스를 기준으로 판단했습니다."],
        "risks": _scenario_list(draft.get("bear")) or ["지표 변동성, 소스 공백, 시장 환경 변화"],
        "triggers": _scenario_list(draft.get("bull")) or ["실적 발표, 공개 소스 업데이트, 가격·거래량 변화"],
    }
    for key, fallback in defaults.items():
        if key not in draft:
            draft[key] = fallback


def _scenario_list(value: JsonValue) -> list[str]:
    if isinstance(value, list):
        return [item.strip() for item in value if isinstance(item, str) and item.strip()]
    if isinstance(value, str) and value.strip():
        parts = [part.strip() for part in value.split(" / ")]
        return [part for part in parts if part]
    return []


def _normalize_confidence(value: str) -> JsonValue:
    normalized = value.strip().lower()
    if normalized in {"높음", "high"}:
        return 0.7
    if normalized in {"중간", "보통", "medium"}:
        return 0.5
    if normalized in {"낮음", "low"}:
        return 0.3
    try:
        return float(normalized)
    except ValueError:
        return value


def _is_string_list(value: JsonValue) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def _system_prompt() -> str:
    return (
        "You are the VBinvest on-demand research analyst. Return JSON only. "
        "Use only the provided packet. Approved opinion labels are 매수, 아웃퍼폼, 중립, 언더퍼폼, 매도. "
        "Do not promise returns or present licensed investment advice. "
        "Required keys: opinion, thesis, rationale, bull, base, bear, risks, triggers, confidence. "
        "Use arrays of short strings for rationale, risks, and triggers. Use a numeric confidence between 0 and 1. "
        "If no collected source states a target price, estimate a target price from the provided price, RSI, moving averages, returns, and scenarios; "
        "keep the estimate conservative and explain the basis in rationale."
    )


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
