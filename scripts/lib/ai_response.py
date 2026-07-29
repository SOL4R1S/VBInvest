"""AI provider response parsing, validation, and normalization.

Extracted from ai_provider.py to separate HTTP transport from response logic.
"""

from __future__ import annotations

import json
import math
from typing import TypeAlias, cast

JsonValue: TypeAlias = str | int | float | bool | None | list["JsonValue"] | dict[str, "JsonValue"]


class AIProviderError(RuntimeError):
    pass


def json_safe_payload(value: object) -> JsonValue:
    """Recursively sanitize a value for JSON serialization (NaN → None)."""
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, str | int | bool) or value is None:
        return value
    if isinstance(value, list):
        return [json_safe_payload(item) for item in value]
    if isinstance(value, dict):
        return {str(key): json_safe_payload(child) for key, child in value.items()}
    return cast(JsonValue, value)


def extract_content_json(payload: JsonValue, *, repair_local_model: bool = False) -> dict[str, JsonValue]:
    """Extract and validate the research draft from an OpenAI-compatible response."""
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
    return validate_draft_schema(normalize_draft_schema(draft, repair_local_model=repair_local_model))


def validate_draft_schema(draft: dict[str, JsonValue]) -> dict[str, JsonValue]:
    """Validate required fields and types in a research draft."""
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


def normalize_draft_schema(draft: dict[str, JsonValue], *, repair_local_model: bool) -> dict[str, JsonValue]:
    """Normalize a draft, optionally repairing missing fields for local models."""
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


def system_prompt() -> str:
    """System prompt for the research generation model."""
    return (
        "You are the VBinvest on-demand research analyst. Return JSON only. "
        "Use only the provided packet. Approved opinion labels are 매수, 아웃퍼폼, 중립, 언더퍼폼, 매도. "
        "Do not promise returns or present licensed investment advice. "
        "Required keys: opinion, thesis, rationale, bull, base, bear, risks, triggers, confidence. "
        "Use arrays of short strings for rationale, risks, and triggers. Use a numeric confidence between 0 and 1. "
        "If no collected source states a target price, estimate a target price from the provided price, RSI, moving averages, returns, and scenarios; "
        "keep the estimate conservative and explain the basis in rationale."
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

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
