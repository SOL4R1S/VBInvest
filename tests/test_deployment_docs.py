import stat
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_readme_has_required_local_first_sections():
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    english_text = (ROOT / "README.en.md").read_text(encoding="utf-8")

    for required in [
        "[한국어](README.md)",
        "[English](README.en.md)",
        "로컬 우선",
        "빠른 시작",
        "초기 설정",
        "OpenDART",
        "AI API",
        "SQLite",
        "PostgreSQL",
        "면책 고지",
    ]:
        assert required in text

    for required in [
        "[한국어](README.md)",
        "[English](README.en.md)",
        "local-first",
        "Quick Start",
        "First-Run Choices",
        "OpenDART",
        "AI API",
        "SQLite",
        "PostgreSQL",
        "Disclaimer",
    ]:
        assert required in english_text


def test_readme_documents_cross_platform_launch_paths():
    korean = (ROOT / "README.md").read_text(encoding="utf-8")
    english = (ROOT / "README.en.md").read_text(encoding="utf-8")

    for required in [
        "macOS",
        "./VBinvest.command",
        "chmod +x VBinvest.command",
        "Windows",
        "VBinvest.bat",
        "빈 포트를 자동으로 선택",
    ]:
        assert required in korean

    for required in [
        "macOS",
        "./VBinvest.command",
        "chmod +x VBinvest.command",
        "Windows",
        "VBinvest.bat",
        "chooses free ports",
    ]:
        assert required in english


def test_readme_separates_launch_instructions_by_operating_system():
    korean = (ROOT / "README.md").read_text(encoding="utf-8")
    english = (ROOT / "README.en.md").read_text(encoding="utf-8")

    korean_macos = korean.index("### macOS 사용자")
    korean_windows = korean.index("### Windows 사용자")
    assert korean_macos < korean_windows
    assert "./VBinvest.command" in korean[korean_macos:korean_windows]
    assert "VBinvest.bat" in korean[korean_windows:]

    english_macos = english.index("### macOS Users")
    english_windows = english.index("### Windows Users")
    assert english_macos < english_windows
    assert "./VBinvest.command" in english[english_macos:english_windows]
    assert "VBinvest.bat" in english[english_windows:]


def test_readme_documents_startup_sources_and_report_source_gap():
    korean = (ROOT / "README.md").read_text(encoding="utf-8")
    english = (ROOT / "README.en.md").read_text(encoding="utf-8")

    for required in [
        "프로그램 시작 시",
        "뉴스",
        "SEC",
        "OpenDART",
        "리포트 발행",
        "DB에 저장된 최신 가격",
        "source_gap",
        "실시간 웹 탐색을 수행하지 않습니다",
    ]:
        assert required in korean

    for required in [
        "When the program starts",
        "news",
        "SEC",
        "OpenDART",
        "Generate Report",
        "latest DB-backed prices",
        "source_gap",
        "does not perform live web browsing",
    ]:
        assert required in english


def test_readme_documents_secure_storage_and_ai_modes():
    korean = (ROOT / "README.md").read_text(encoding="utf-8")
    english = (ROOT / "README.en.md").read_text(encoding="utf-8")

    for required in [
        'save_secret "AI_API_KEY"',
        'save_secret "OPENDART_API_KEY"',
        "Windows Credential Manager",
        "Ollama",
        "OpenAI-compatible",
        "로컬 모델은 키 없이",
        "클라우드 AI provider는 API 키가 필요",
        "Codex/Copilot CLI",
    ]:
        assert required in korean

    for required in [
        'save_secret "AI_API_KEY"',
        'save_secret "OPENDART_API_KEY"',
        "Windows Credential Manager",
        "Ollama",
        "OpenAI-compatible",
        "local models can run without a key",
        "cloud AI providers require an API key",
        "Codex/Copilot CLI",
    ]:
        assert required in english


def test_cross_platform_local_launchers_are_tracked():
    mac_launcher = ROOT / "VBinvest.command"
    windows_launcher = ROOT / "VBinvest.bat"

    assert mac_launcher.is_file()
    assert windows_launcher.is_file()
    assert mac_launcher.stat().st_mode & stat.S_IXUSR

    mac_text = mac_launcher.read_text(encoding="utf-8")
    windows_text = windows_launcher.read_text(encoding="utf-8")

    assert "uvicorn scripts.api:app" in mac_text
    assert 'open "http://127.0.0.1:${API_PORT}"' in mac_text
    assert "uvicorn scripts.api:app" in windows_text
    assert 'start "" "http://127.0.0.1:%API_PORT%"' in windows_text
    assert "VBINVEST_API_BASE_URL" in mac_text
    assert "VBINVEST_API_BASE_URL" in windows_text

    for forbidden in [
        "npm was not found",
        "command -v npm",
        "where npm",
        "npx next dev",
        "next start",
    ]:
        assert forbidden not in mac_text
        assert forbidden not in windows_text

    assert 'save_secret "AI_API_KEY"' in mac_text
    assert 'save_secret "OPENDART_API_KEY"' in mac_text
    assert '-m scripts.save_secret "$account"' in mac_text
    assert "-m scripts.save_secret AI_API_KEY" in windows_text
    assert "-m scripts.save_secret OPENDART_API_KEY" in windows_text


def test_hosted_platform_artifacts_are_absent_from_local_first_repository():
    hosted_platform = "".join(["v", "e", "r", "c", "e", "l"])
    tracked = subprocess.run(
        ["git", "ls-files"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()

    assert f"{hosted_platform}.json" not in tracked
    assert f"frontend/public/{hosted_platform}.svg" not in tracked
    assert not (ROOT / f"{hosted_platform}.json").exists()
    assert not (ROOT / "frontend" / "public" / f"{hosted_platform}.svg").exists()


def test_public_config_uses_placeholders_only():
    checked = [
        ROOT / ".env.example",
        ROOT / "frontend" / ".env.example",
    ]
    combined = "\n".join(path.read_text(encoding="utf-8") for path in checked)

    assert "service_role=" not in combined
    assert "client_secret=" not in combined
    assert "POSTGRES_PASSWORD=secret" not in combined
    assert "<openai-compatible-api-key>" in combined


def test_deployment_docs_do_not_present_hosted_saas_as_default():
    combined = "\n".join(
        [
            (ROOT / "README.md").read_text(encoding="utf-8"),
            (ROOT / ".env.example").read_text(encoding="utf-8"),
        ]
    )

    hosted_phrase = "Default: Supabase + " + "".join(["V", "e", "r", "c", "e", "l"])

    assert hosted_phrase not in combined
    assert "Public users must use managed Postgres" not in combined
    assert "payment/ad provider" not in combined


def test_root_env_example_is_local_first():
    text = (ROOT / ".env.example").read_text(encoding="utf-8")

    assert "VBINVEST_DB_MODE=sqlite" in text
    assert "OPENDART_API_KEY=<optional-opendart-api-key>" in text
    assert "AI_API_KEY=<openai-compatible-api-key>" in text
    assert "SUPABASE_SERVICE_ROLE_KEY" not in text


def test_root_env_example_documents_local_and_cloud_ai_placeholders():
    text = (ROOT / ".env.example").read_text(encoding="utf-8")

    assert "AI_PROVIDER_NAME=ollama" in text
    assert "AI_PROVIDER_BASE_URL=http://127.0.0.1:11434/v1" in text
    assert "AI_PROVIDER_NAME=<openai|openrouter|deepseek|qwen_dashscope|kimi_moonshot|glm_zai|custom>" in text
    assert "AI_API_KEY=<openai-compatible-api-key>" in text
    assert "source_gap" in text
