"""Tests for scripts.lib.ai_response — parsing, validation, normalization."""

import pytest

from scripts.lib.ai_response import (
    AIProviderError,
    extract_content_json,
    json_safe_payload,
    normalize_draft_schema,
    system_prompt,
    validate_draft_schema,
)

# ---------------------------------------------------------------------------
# json_safe_payload
# ---------------------------------------------------------------------------


def test_json_safe_payload_passthrough():
    assert json_safe_payload("hello") == "hello"
    assert json_safe_payload(42) == 42
    assert json_safe_payload(True) is True
    assert json_safe_payload(None) is None


def test_json_safe_payload_nan_to_none():
    assert json_safe_payload(float("nan")) is None
    assert json_safe_payload(float("inf")) is None
    assert json_safe_payload(float("-inf")) is None
    assert json_safe_payload(3.14) == 3.14


def test_json_safe_payload_nested():
    data = {"a": [1, float("nan"), "x"], "b": {"c": float("inf")}}
    result = json_safe_payload(data)
    assert result == {"a": [1, None, "x"], "b": {"c": None}}


# ---------------------------------------------------------------------------
# extract_content_json
# ---------------------------------------------------------------------------


def _valid_draft() -> dict:
    return {
        "opinion": "매수",
        "thesis": "Strong growth ahead",
        "rationale": ["reason1", "reason2"],
        "bull": "Upside case",
        "base": "Base case",
        "bear": "Downside case",
        "risks": ["risk1"],
        "triggers": ["trigger1"],
        "confidence": 0.75,
    }


def _wrap_content(content: str) -> dict:
    return {"choices": [{"message": {"content": content}, "finish_reason": "stop"}]}


def test_extract_content_json_valid():
    import json

    payload = _wrap_content(json.dumps(_valid_draft()))
    result = extract_content_json(payload)
    assert result["opinion"] == "매수"
    assert result["confidence"] == 0.75


def test_extract_content_json_embedded_in_text():
    import json

    text = f"Here is the analysis:\n```json\n{json.dumps(_valid_draft())}\n```"
    payload = _wrap_content(text)
    result = extract_content_json(payload)
    assert result["thesis"] == "Strong growth ahead"


def test_extract_content_json_not_dict():
    with pytest.raises(AIProviderError, match="must be a JSON object"):
        extract_content_json("not a dict")


def test_extract_content_json_no_choices():
    with pytest.raises(AIProviderError, match="missing choices"):
        extract_content_json({"choices": []})


def test_extract_content_json_empty_content():
    payload = {"choices": [{"message": {"content": "  "}, "finish_reason": "stop"}]}
    with pytest.raises(AIProviderError, match="content is empty"):
        extract_content_json(payload)


def test_extract_content_json_reasoning_only():
    payload = {"choices": [{"message": {"content": "", "reasoning": "thinking..."}, "finish_reason": "stop"}]}
    with pytest.raises(AIProviderError, match="reasoning-only"):
        extract_content_json(payload)


def test_extract_content_json_length_cutoff():
    payload = {"choices": [{"message": {"content": ""}, "finish_reason": "length"}]}
    with pytest.raises(AIProviderError, match="stopped before JSON"):
        extract_content_json(payload)


def test_extract_content_json_invalid_json():
    payload = _wrap_content("this is not json at all")
    with pytest.raises(AIProviderError, match="not valid JSON"):
        extract_content_json(payload)


# ---------------------------------------------------------------------------
# validate_draft_schema
# ---------------------------------------------------------------------------


def test_validate_draft_schema_valid():
    draft = _valid_draft()
    result = validate_draft_schema(draft)
    assert result["opinion"] == "매수"


def test_validate_draft_schema_missing_field():
    draft = _valid_draft()
    del draft["thesis"]
    with pytest.raises(AIProviderError, match="missing required field: thesis"):
        validate_draft_schema(draft)


def test_validate_draft_schema_empty_opinion():
    draft = _valid_draft()
    draft["opinion"] = "  "
    with pytest.raises(AIProviderError, match="non-empty string: opinion"):
        validate_draft_schema(draft)


def test_validate_draft_schema_bad_rationale():
    draft = _valid_draft()
    draft["rationale"] = "not a list"
    with pytest.raises(AIProviderError, match="list of strings: rationale"):
        validate_draft_schema(draft)


def test_validate_draft_schema_bool_confidence():
    draft = _valid_draft()
    draft["confidence"] = True
    with pytest.raises(AIProviderError, match="numeric confidence"):
        validate_draft_schema(draft)


# ---------------------------------------------------------------------------
# normalize_draft_schema
# ---------------------------------------------------------------------------


def test_normalize_string_to_list():
    draft = _valid_draft()
    draft["rationale"] = "single reason"
    result = normalize_draft_schema(draft, repair_local_model=False)
    assert result["rationale"] == ["single reason"]


def test_normalize_confidence_string():
    draft = _valid_draft()
    draft["confidence"] = "높음"
    result = normalize_draft_schema(draft, repair_local_model=False)
    assert result["confidence"] == 0.7


def test_normalize_confidence_numeric_string():
    draft = _valid_draft()
    draft["confidence"] = "0.85"
    result = normalize_draft_schema(draft, repair_local_model=False)
    assert result["confidence"] == 0.85


def test_normalize_repair_local_model_backfills():
    draft = {"opinion": "중립", "thesis": "test"}
    result = normalize_draft_schema(draft, repair_local_model=True)
    assert isinstance(result["bull"], str) and result["bull"]
    assert isinstance(result["base"], str) and result["base"]
    assert isinstance(result["bear"], str) and result["bear"]
    assert isinstance(result["rationale"], list)
    assert isinstance(result["risks"], list)
    assert isinstance(result["triggers"], list)
    assert result["confidence"] == 0.5


def test_normalize_repair_joins_scenario_lists():
    draft = _valid_draft()
    draft["bull"] = ["point a", "point b"]
    result = normalize_draft_schema(draft, repair_local_model=True)
    assert result["bull"] == "point a / point b"


# ---------------------------------------------------------------------------
# system_prompt
# ---------------------------------------------------------------------------


def test_system_prompt_contains_required_keys():
    prompt = system_prompt()
    for key in ("opinion", "thesis", "rationale", "bull", "base", "bear", "risks", "triggers", "confidence"):
        assert key in prompt
