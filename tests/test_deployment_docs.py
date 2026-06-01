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


def test_cross_platform_local_launchers_are_tracked():
    mac_launcher = ROOT / "VBinvest.command"
    windows_launcher = ROOT / "VBinvest.bat"

    assert mac_launcher.is_file()
    assert windows_launcher.is_file()
    assert mac_launcher.stat().st_mode & stat.S_IXUSR

    mac_text = mac_launcher.read_text(encoding="utf-8")
    windows_text = windows_launcher.read_text(encoding="utf-8")

    assert "uvicorn scripts.api:app" in mac_text
    assert "npx next dev" in mac_text
    assert "open" in mac_text
    assert "uvicorn scripts.api:app" in windows_text
    assert "npx next dev" in windows_text
    assert "start" in windows_text
    assert "VBINVEST_API_BASE_URL" in mac_text
    assert "VBINVEST_API_BASE_URL" in windows_text
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
