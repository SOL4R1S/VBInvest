import json

import pytest

from scripts.lib.ai_provider import AIProviderConfig, AIProviderConfigError, OpenAICompatibleResearchClient


class FakeResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")


class CapturingUrlopen:
    def __init__(self, payload: dict):
        self.payload = payload
        self.request = None
        self.timeout = None

    def __call__(self, request, *, timeout: int):
        self.request = request
        self.timeout = timeout
        return FakeResponse(self.payload)


def test_ai_provider_config_loads_openai_compatible_env_without_secret_repr():
    config = AIProviderConfig.from_env(
        {
            "AI_PROVIDER_API_KEY": "secret-token",
            "AI_PROVIDER_BASE_URL": "https://api.example.com/v1",
            "AI_PROVIDER_MODEL": "research-model",
            "AI_PROVIDER_NAME": "example-ai",
        }
    )

    assert config is not None
    assert config.name == "example-ai"
    assert config.base_url == "https://api.example.com/v1"
    assert config.model == "research-model"
    assert "secret-token" not in repr(config)


def test_ai_provider_config_prefers_macos_keychain_secret():
    class FakeStore:
        def get(self, account: str) -> str:
            return "keychain-token" if account == "AI_API_KEY" else ""

    config = AIProviderConfig.from_env(
        {
            "AI_PROVIDER_API_KEY": "env-token",
            "AI_PROVIDER_BASE_URL": "https://api.example.com/v1",
            "AI_PROVIDER_MODEL": "research-model",
        },
        system_name="Darwin",
        secret_store=FakeStore(),
    )

    assert config is not None
    assert config.api_key == "keychain-token"


def test_local_loopback_provider_allows_empty_api_key():
    config = AIProviderConfig.from_env(
        {
            "AI_PROVIDER_BASE_URL": "http://127.0.0.1:11434/v1",
            "AI_PROVIDER_MODEL": "qwen2.5",
            "AI_PROVIDER_NAME": "ollama",
        }
    )

    assert config is not None
    assert config.api_key == ""
    assert config.name == "ollama"
    assert config.base_url == "http://127.0.0.1:11434/v1"


def test_local_keyless_request_omits_authorization_header():
    opener = CapturingUrlopen(
        {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "opinion": "중립",
                                "thesis": "DB 소스만 사용한 중립 관점입니다.",
                                "rationale": ["가격 지표가 혼재되어 있습니다."],
                                "bull": "수요 회복 가능성",
                                "base": "관망",
                                "bear": "수요 둔화",
                                "risks": ["변동성"],
                                "triggers": ["실적"],
                                "confidence": 0.5,
                            },
                            ensure_ascii=False,
                        )
                    }
                }
            ]
        }
    )
    config = AIProviderConfig(
        name="ollama",
        api_key="",
        base_url="http://127.0.0.1:11434/v1",
        model="qwen2.5",
    )
    client = OpenAICompatibleResearchClient(config, urlopen=opener)

    client.generate_research(
        {"symbol": "NVDA", "display_name_ko": "엔비디아"},
        {"close": 100, "rsi14": 55},
        {"sources": [{"kind": "db_price_indicator", "symbol": "NVDA"}], "source_gap": False},
    )

    assert opener.request is not None
    assert opener.request.get_header("Authorization") is None


def test_cloud_ai_provider_requires_api_key():
    with pytest.raises(AIProviderConfigError, match="AI provider API key is required for non-local providers"):
        AIProviderConfig.from_env(
            {
                "AI_PROVIDER_BASE_URL": "https://api.example.com/v1",
                "AI_PROVIDER_MODEL": "research-model",
            }
        )


def test_openai_compatible_research_client_sends_chat_completion_and_parses_json():
    opener = CapturingUrlopen(
        {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "opinion": "아웃퍼폼",
                                "thesis": "DB 지표와 공개 소스를 바탕으로 모멘텀이 개선됩니다.",
                                "rationale": ["RSI가 중립권입니다."],
                                "bull": "AI 수요가 강합니다.",
                                "base": "기본 시나리오는 점진적 개선입니다.",
                                "bear": "수요 둔화가 리스크입니다.",
                                "risks": ["수요 둔화"],
                                "triggers": ["실적 발표"],
                                "confidence": 0.66,
                            },
                            ensure_ascii=False,
                        )
                    }
                }
            ]
        }
    )
    config = AIProviderConfig(
        name="example-ai",
        api_key="secret-token",
        base_url="https://api.example.com/v1",
        model="research-model",
        timeout_seconds=7,
    )
    client = OpenAICompatibleResearchClient(config, urlopen=opener)

    draft = client.generate_research(
        {"symbol": "NVDA", "display_name_ko": "엔비디아"},
        {"close": 100, "rsi14": 55},
        {"sources": [{"kind": "db_price_indicator", "symbol": "NVDA"}], "source_gap": False},
    )

    assert draft["opinion"] == "아웃퍼폼"
    assert draft["confidence"] == 0.66
    assert opener.timeout == 7
    assert opener.request is not None
    assert opener.request.get_header("Authorization") == "Bearer secret-token"
    assert opener.request.full_url == "https://api.example.com/v1/chat/completions"
