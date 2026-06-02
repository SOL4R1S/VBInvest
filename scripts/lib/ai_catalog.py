from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AIProviderCatalogEntry:
    id: str
    display_name: str
    default_base_url: str
    model_examples: tuple[str, ...]
    auth_env_var: str
    structured_output_note: str
    docs_url: str
    local: bool = False

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "display_name": self.display_name,
            "default_base_url": self.default_base_url,
            "model_examples": list(self.model_examples),
            "auth_env_var": self.auth_env_var,
            "structured_output_note": self.structured_output_note,
            "docs_url": self.docs_url,
            "local": self.local,
        }


def provider_catalog() -> tuple[AIProviderCatalogEntry, ...]:
    return (
        AIProviderCatalogEntry(
            id="openai",
            display_name="OpenAI",
            default_base_url="https://api.openai.com/v1",
            model_examples=("gpt-4.1", "gpt-4.1-mini"),
            auth_env_var="OPENAI_API_KEY",
            structured_output_note="JSON schema/structured output support",
            docs_url="https://platform.openai.com/docs",
        ),
        AIProviderCatalogEntry(
            id="openrouter",
            display_name="OpenRouter",
            default_base_url="https://openrouter.ai/api/v1",
            model_examples=("openai/gpt-4.1", "anthropic/claude-sonnet-4"),
            auth_env_var="OPENROUTER_API_KEY",
            structured_output_note="Model-dependent JSON support",
            docs_url="https://openrouter.ai/docs",
        ),
        AIProviderCatalogEntry(
            id="deepseek",
            display_name="DeepSeek",
            default_base_url="https://api.deepseek.com",
            model_examples=("deepseek-chat", "deepseek-reasoner"),
            auth_env_var="DEEPSEEK_API_KEY",
            structured_output_note="OpenAI-compatible JSON object mode",
            docs_url="https://api-docs.deepseek.com",
        ),
        AIProviderCatalogEntry(
            id="qwen_dashscope",
            display_name="Qwen / DashScope",
            default_base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
            model_examples=("qwen-plus", "qwen-max"),
            auth_env_var="DASHSCOPE_API_KEY",
            structured_output_note="OpenAI-compatible mode",
            docs_url="https://www.alibabacloud.com/help/en/model-studio",
        ),
        AIProviderCatalogEntry(
            id="kimi_moonshot",
            display_name="Kimi / Moonshot",
            default_base_url="https://api.moonshot.ai/v1",
            model_examples=("moonshot-v1-8k", "moonshot-v1-128k"),
            auth_env_var="MOONSHOT_API_KEY",
            structured_output_note="OpenAI-compatible mode",
            docs_url="https://platform.moonshot.ai/docs",
        ),
        AIProviderCatalogEntry(
            id="glm_zai",
            display_name="GLM / Z.AI",
            default_base_url="https://open.bigmodel.cn/api/paas/v4",
            model_examples=("glm-4-plus", "glm-4-air"),
            auth_env_var="ZAI_API_KEY",
            structured_output_note="OpenAI-compatible mode",
            docs_url="https://docs.bigmodel.cn",
        ),
        AIProviderCatalogEntry(
            id="custom",
            display_name="Custom OpenAI-compatible Provider",
            default_base_url="https://api.example.com/v1",
            model_examples=("provider-model-name",),
            auth_env_var="AI_PROVIDER_API_KEY",
            structured_output_note="Depends on provider",
            docs_url="https://github.com/SOL4R1S/VBInvest",
        ),
        AIProviderCatalogEntry(
            id="ollama",
            display_name="Ollama / Local LLM",
            default_base_url="http://127.0.0.1:11434/v1",
            model_examples=("qwen2.5", "deepseek-r1", "llama3.1"),
            auth_env_var="optional",
            structured_output_note="Local OpenAI-compatible endpoint",
            docs_url="https://ollama.com",
            local=True,
        ),
    )
