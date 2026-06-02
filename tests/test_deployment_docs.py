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
        "처음 실행 설정",
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
        "VBinvest.ps1",
        "VBinvest.bat",
        "빈 포트를 자동으로 선택",
    ]:
        assert required in korean

    for required in [
        "macOS",
        "./VBinvest.command",
        "chmod +x VBinvest.command",
        "Windows",
        "VBinvest.ps1",
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
    assert "VBinvest.ps1" in korean[korean_windows:]
    assert "VBinvest.bat" in korean[korean_windows:]

    english_macos = english.index("### macOS Users")
    english_windows = english.index("### Windows Users")
    assert english_macos < english_windows
    assert "./VBinvest.command" in english[english_macos:english_windows]
    assert "VBinvest.ps1" in english[english_windows:]
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


def test_readme_documents_optional_schedulers_and_uninstall():
    korean = (ROOT / "README.md").read_text(encoding="utf-8")
    english = (ROOT / "README.en.md").read_text(encoding="utf-8")

    for required in [
        "선택적 예약 실행",
        "macOS launchd",
        "Linux cron",
        "주간 사전 계산은 기본 비활성화",
        "launchctl unload -w",
        "crontab -l | sed",
    ]:
        assert required in korean

    for required in [
        "Optional Scheduled Runs",
        "macOS launchd",
        "Linux cron",
        "Weekly precompute remains disabled by default",
        "launchctl unload -w",
        "crontab -l | sed",
    ]:
        assert required in english


def test_readme_documents_backup_uninstall_contribution_and_cost_responsibility():
    korean = (ROOT / "README.md").read_text(encoding="utf-8")
    english = (ROOT / "README.en.md").read_text(encoding="utf-8")
    english_lower = english.lower()

    for required in [
        "백업과 삭제",
        "vbinvest.sqlite3",
        "pg_dump",
        "<!-- Vbinvest:generated -->",
        "개발과 기여",
        "Conventional Commits",
        "라이선스",
        "비용과 면책",
        "사용자 책임",
    ]:
        assert required in korean

    for required in [
        "backup and uninstall",
        "vbinvest.sqlite3",
        "pg_dump",
        "<!-- Vbinvest:generated -->",
        "contributing",
        "Conventional Commits",
        "License",
        "Disclaimer",
        "your own responsibility",
    ]:
        assert required.lower() in english_lower


def test_scheduler_templates_are_present_and_generic():
    daily_launchd = ROOT / "ops" / "launchd" / "vbinvest-daily.plist"
    weekly_launchd = ROOT / "ops" / "launchd" / "vbinvest-weekly.plist"
    daily_cron = ROOT / "ops" / "cron" / "vbinvest-daily.cron"
    weekly_cron = ROOT / "ops" / "cron" / "vbinvest-weekly.cron"

    for path in [daily_launchd, weekly_launchd, daily_cron, weekly_cron]:
        assert path.is_file()

    daily_text = daily_launchd.read_text(encoding="utf-8")
    weekly_text = weekly_launchd.read_text(encoding="utf-8")
    daily_cron_text = daily_cron.read_text(encoding="utf-8")
    weekly_cron_text = weekly_cron.read_text(encoding="utf-8")

    for required in [
        "/path/to/VBinvest",
        "com.vbinvest.daily",
        "StartCalendarInterval",
        "scripts/local_scheduler_tick.py",
    ]:
        assert required in daily_text

    for required in [
        "/path/to/VBinvest",
        "com.vbinvest.weekly",
        "scripts/local_scheduler_tick.py",
    ]:
        assert required in weekly_text

    for required in [
        "/path/to/VBinvest",
        "scripts/local_scheduler_tick.py",
    ]:
        assert required in daily_cron_text
        assert required in weekly_cron_text

    for forbidden in [
        "/Volumes/nv6000t/project/VBInvest",
        "/Volumes/nv6000t/ObsidianVault",
        "daily_market_ingest.py",
        "weekly_pipeline.py",
    ]:
        assert forbidden not in daily_text
        assert forbidden not in weekly_text
        assert forbidden not in daily_cron_text
        assert forbidden not in weekly_cron_text


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


def test_readme_documents_cover_screenshot_and_distribution_notes():
    korean = (ROOT / "README.md").read_text(encoding="utf-8")
    english = (ROOT / "README.en.md").read_text(encoding="utf-8")

    for required in [
        "## 스크린샷",
        "TODO",
        "스크린샷이 준비되는 대로 추가",
        "개발 환경",
        "Python",
        "Node",
        "패키지 배포본은",
        "런타임에 Node.js가 필요하지 않습니다",
    ]:
        assert required in korean

    for required in [
        "## Screenshots",
        "TODO",
        "screenshots are not committed yet",
        "Developer environment",
        "Python",
        "Node",
        "packaged releases",
        "Node.js runtime is not required",
    ]:
        assert required in english


def test_readme_documents_db_modes_and_data_responsibility():
    korean = (ROOT / "README.md").read_text(encoding="utf-8")
    english = (ROOT / "README.en.md").read_text(encoding="utf-8")
    english_lower = english.lower()

    for required in [
        "SQLite",
        "기본값",
        "PostgreSQL Docker",
        "고급 사용자",
        "직접 DSN",
        "데이터 소유권",
        "사용자 소유",
    ]:
        assert required in korean

    for required in [
        "SQLite",
        "default",
        "PostgreSQL Docker",
        "advanced users",
        "Direct DSN",
        "data ownership",
        "you own your data",
    ]:
        assert required.lower() in english_lower


def test_readme_documents_obsidian_backup_uninstall_disclaimer_contributing():
    korean = (ROOT / "README.md").read_text(encoding="utf-8")
    english = (ROOT / "README.en.md").read_text(encoding="utf-8")
    contributing = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")

    for required in [
        "Obsidian",
        "백업",
        "삭제",
        "문제 해결",
        "기여",
        "Git hooks",
        "기여는",
        "라이선스",
        "면책",
        "사용자 비용",
    ]:
        assert required in korean
    for required in [
        "scripts/git_hooks/install_hooks.py",
        "pre-commit 패키지는 필수",
        "CONTRIBUTING.md",
    ]:
        assert required in korean
    assert "pre-commit run --all-files" not in korean

    for required in [
        "Obsidian",
        "Backup",
        "Uninstall",
        "Troubleshooting",
        "Contributing",
        "Git hooks",
        "Contributing",
        "License",
        "Disclaimer",
        "user-paid data and AI costs",
    ]:
        assert required.lower() in english.lower()
    for required in [
        "scripts/git_hooks/install_hooks.py",
        "pre-commit package is not required",
        "CONTRIBUTING.md",
    ]:
        assert required.lower() in english.lower()
    assert "pre-commit run --all-files" not in english

    for required in [
        "scripts/git_hooks/install_hooks.py",
        "check_paths.py",
        "check_commit_msg.py",
        "check_pre_push.py",
        "pre-commit package is not required",
        "pre-commit 패키지는 필수",
    ]:
        assert required in contributing


def test_readme_documents_disallow_central_free_and_fake_service_mentions():
    combined = "\n".join(
        [
            (ROOT / "README.md").read_text(encoding="utf-8"),
            (ROOT / "README.en.md").read_text(encoding="utf-8"),
        ]
    )
    combined_lower = combined.lower()

    forbidden = [
        "Vercel",
        "Supabase",
        "ad unlock",
        "subscription",
        "subscription model",
        "subscription-based",
        "free centralized market data",
        "free ai credits",
    ]

    for phrase in forbidden:
        assert phrase.lower() not in combined_lower

    assert "user-paid data and ai costs" in combined_lower


def test_cross_platform_local_launchers_are_tracked():
    mac_launcher = ROOT / "VBinvest.command"
    windows_launcher = ROOT / "VBinvest.bat"
    windows_ps1_launcher = ROOT / "VBinvest.ps1"

    assert mac_launcher.is_file()
    assert windows_launcher.is_file()
    assert windows_ps1_launcher.is_file()
    assert mac_launcher.stat().st_mode & stat.S_IXUSR

    mac_text = mac_launcher.read_text(encoding="utf-8")
    windows_text = windows_launcher.read_text(encoding="utf-8")
    windows_ps1_text = windows_ps1_launcher.read_text(encoding="utf-8")

    assert "-m scripts.launcher" in mac_text
    assert "-m scripts.launcher" in windows_text
    assert "-m scripts.launcher" in windows_ps1_text

    for forbidden in [
        "npm was not found",
        "command -v npm",
        "where npm",
        "npx next dev",
        "next start",
        "uvicorn scripts.api:app",
        "uvicorn ",
    ]:
        assert forbidden not in mac_text
        assert forbidden not in windows_text
        assert forbidden not in windows_ps1_text

    assert 'save_secret "AI_API_KEY"' in mac_text
    assert 'save_secret "OPENDART_API_KEY"' in mac_text
    assert '-m scripts.save_secret "$account"' in mac_text
    assert "-m scripts.save_secret AI_API_KEY" in windows_text
    assert "-m scripts.save_secret OPENDART_API_KEY" in windows_text
    assert "-m scripts.save_secret AI_API_KEY" in windows_ps1_text
    assert "-m scripts.save_secret OPENDART_API_KEY" in windows_ps1_text


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
