"""Tests for scripts.lib.ai_catalog — provider catalog entries."""

from scripts.lib.ai_catalog import AIProviderCatalogEntry, provider_catalog


class TestAIProviderCatalogEntry:
    def test_as_dict_roundtrip(self):
        entry = AIProviderCatalogEntry(
            id="test",
            display_name="Test Provider",
            default_base_url="https://api.test.com/v1",
            model_examples=("model-a", "model-b"),
            auth_env_var="TEST_API_KEY",
            structured_output_note="JSON mode",
            docs_url="https://docs.test.com",
        )
        d = entry.as_dict()
        assert d["id"] == "test"
        assert d["display_name"] == "Test Provider"
        assert d["model_examples"] == ["model-a", "model-b"]
        assert d["local"] is False

    def test_local_flag(self):
        entry = AIProviderCatalogEntry(
            id="local-test",
            display_name="Local",
            default_base_url="http://127.0.0.1:11434/v1",
            model_examples=("llama3",),
            auth_env_var="optional",
            structured_output_note="local",
            docs_url="https://example.com",
            local=True,
        )
        assert entry.local is True
        assert entry.as_dict()["local"] is True

    def test_frozen_dataclass(self):
        entry = AIProviderCatalogEntry(
            id="x",
            display_name="X",
            default_base_url="",
            model_examples=(),
            auth_env_var="",
            structured_output_note="",
            docs_url="",
        )
        try:
            entry.id = "y"  # type: ignore[misc]
            raise AssertionError("should raise")
        except AttributeError:
            pass


class TestProviderCatalog:
    def test_returns_tuple_of_entries(self):
        catalog = provider_catalog()
        assert isinstance(catalog, tuple)
        assert len(catalog) >= 7
        assert all(isinstance(e, AIProviderCatalogEntry) for e in catalog)

    def test_known_provider_ids(self):
        ids = {e.id for e in provider_catalog()}
        assert "openai" in ids
        assert "openrouter" in ids
        assert "deepseek" in ids
        assert "ollama" in ids
        assert "custom" in ids

    def test_ollama_is_local(self):
        catalog = provider_catalog()
        ollama = next(e for e in catalog if e.id == "ollama")
        assert ollama.local is True

    def test_cloud_providers_not_local(self):
        catalog = provider_catalog()
        for entry in catalog:
            if entry.id != "ollama":
                assert entry.local is False, f"{entry.id} should not be local"

    def test_all_entries_have_required_fields(self):
        for entry in provider_catalog():
            assert entry.id, "id must not be empty"
            assert entry.display_name, "display_name must not be empty"
            assert entry.default_base_url, "default_base_url must not be empty"
            assert entry.auth_env_var, "auth_env_var must not be empty"
            assert entry.docs_url, "docs_url must not be empty"
            assert len(entry.model_examples) >= 1, f"{entry.id} needs model examples"

    def test_as_dict_serializable(self):
        import json

        for entry in provider_catalog():
            json.dumps(entry.as_dict())
