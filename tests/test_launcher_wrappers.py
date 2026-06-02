from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


FORBIDDEN_SNIPPETS = [
    "uvicorn scripts.api:app",
    "-m uvicorn",
    "find_free_port()",
    "find_free_port",
    "load_docker_postgres_env",
    "open \"http://127.0.0.1",
    "start \"VBinvest API\"",
    "command -v npm",
    "where npm",
    "npx next dev",
    "next start",
]


def test_launchers_delegate_to_shared_launcher_and_handle_secrets():
    mac_launcher = ROOT / "VBinvest.command"
    windows_launcher = ROOT / "VBinvest.bat"
    windows_ps1_launcher = ROOT / "VBinvest.ps1"

    assert mac_launcher.is_file()
    assert windows_launcher.is_file()
    assert windows_ps1_launcher.is_file()

    mac_text = mac_launcher.read_text(encoding="utf-8")
    windows_text = windows_launcher.read_text(encoding="utf-8")
    windows_ps1_text = windows_ps1_launcher.read_text(encoding="utf-8")

    assert "-m scripts.launcher" in mac_text
    assert "-m scripts.launcher" in windows_text
    assert "-m scripts.launcher" in windows_ps1_text

    assert 'save_secret "AI_API_KEY"' in mac_text
    assert 'save_secret "OPENDART_API_KEY"' in mac_text
    assert "-m scripts.save_secret AI_API_KEY" in windows_text
    assert "-m scripts.save_secret OPENDART_API_KEY" in windows_text
    assert 'Save-LauncherSecret "AI_API_KEY"' in windows_ps1_text
    assert 'Save-LauncherSecret "OPENDART_API_KEY"' in windows_ps1_text
    assert "-m scripts.save_secret" in windows_ps1_text

    for forbidden in FORBIDDEN_SNIPPETS:
        assert forbidden not in mac_text
        assert forbidden not in windows_text
        assert forbidden not in windows_ps1_text
