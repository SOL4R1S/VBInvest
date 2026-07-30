"""Tests for scripts.lib.ai_cli — CLI detection and auth check."""

import subprocess
from unittest.mock import patch

from scripts.lib.ai_cli import AICliStatus, detect_ai_cli


class TestAICliStatus:
    def test_as_dict(self):
        status = AICliStatus(
            name="codex",
            installed=True,
            authenticated=True,
            path="/usr/bin/codex",
            login_command="codex auth login",
            risk_label="위험",
        )
        d = status.as_dict()
        assert d["name"] == "codex"
        assert d["installed"] is True
        assert d["authenticated"] is True
        assert d["path"] == "/usr/bin/codex"

    def test_frozen(self):
        status = AICliStatus(
            name="x",
            installed=False,
            authenticated=False,
            path=None,
            login_command="",
            risk_label="",
        )
        try:
            status.name = "y"  # type: ignore[misc]
            raise AssertionError("should raise")
        except AttributeError:
            pass


class TestDetectAiCli:
    def test_not_installed(self):
        with patch("scripts.lib.ai_cli.shutil.which", return_value=None):
            status = detect_ai_cli("codex", login_command="codex auth login")
        assert status.installed is False
        assert status.authenticated is False
        assert status.path is None

    def test_installed_and_authenticated(self):
        completed = subprocess.CompletedProcess(
            args=["codex", "auth", "status"],
            returncode=0,
            stdout="You are authenticated as user@example.com",
            stderr="",
        )
        with (
            patch("scripts.lib.ai_cli.shutil.which", return_value="/usr/bin/codex"),
            patch("scripts.lib.ai_cli.subprocess.run", return_value=completed),
        ):
            status = detect_ai_cli("codex", login_command="codex auth login")
        assert status.installed is True
        assert status.authenticated is True
        assert status.path == "/usr/bin/codex"

    def test_installed_but_not_authenticated(self):
        completed = subprocess.CompletedProcess(
            args=["codex", "auth", "status"],
            returncode=1,
            stdout="Not logged in",
            stderr="",
        )
        with (
            patch("scripts.lib.ai_cli.shutil.which", return_value="/usr/bin/codex"),
            patch("scripts.lib.ai_cli.subprocess.run", return_value=completed),
        ):
            status = detect_ai_cli("codex", login_command="codex auth login")
        assert status.installed is True
        assert status.authenticated is False

    def test_auth_check_timeout(self):
        with (
            patch("scripts.lib.ai_cli.shutil.which", return_value="/usr/bin/codex"),
            patch("scripts.lib.ai_cli.subprocess.run", side_effect=subprocess.TimeoutExpired("codex", 3)),
        ):
            status = detect_ai_cli("codex", login_command="codex auth login")
        assert status.installed is True
        assert status.authenticated is False

    def test_auth_check_file_not_found(self):
        with (
            patch("scripts.lib.ai_cli.shutil.which", return_value="/usr/bin/codex"),
            patch("scripts.lib.ai_cli.subprocess.run", side_effect=FileNotFoundError),
        ):
            status = detect_ai_cli("codex", login_command="codex auth login")
        assert status.installed is True
        assert status.authenticated is False

    def test_explicit_executable_path_not_found(self, tmp_path):
        status = detect_ai_cli(
            "codex",
            executable_path=str(tmp_path / "nonexistent"),
            login_command="codex auth login",
        )
        assert status.installed is False

    def test_explicit_executable_path_found(self, tmp_path):
        exe = tmp_path / "codex"
        exe.write_text("#!/bin/sh\necho ok")
        exe.chmod(0o755)
        completed = subprocess.CompletedProcess(args=[], returncode=0, stdout="authenticated", stderr="")
        with patch("scripts.lib.ai_cli.subprocess.run", return_value=completed):
            status = detect_ai_cli("codex", executable_path=str(exe), login_command="codex auth login")
        assert status.installed is True
        assert status.authenticated is True

    def test_logged_in_keyword(self):
        completed = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="logged in as admin",
            stderr="",
        )
        with (
            patch("scripts.lib.ai_cli.shutil.which", return_value="/usr/bin/codex"),
            patch("scripts.lib.ai_cli.subprocess.run", return_value=completed),
        ):
            status = detect_ai_cli("codex", login_command="codex auth login")
        assert status.authenticated is True
