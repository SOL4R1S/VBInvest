import sys
from collections.abc import Callable
from pathlib import Path

import pytest

from scripts.lib import version as version_module
from scripts.lib.version import GitResult, default_git_runner, load_version_metadata


def test_load_version_metadata_uses_version_file_and_git_metadata(tmp_path: Path) -> None:
    (tmp_path / "VERSION").write_text("1.2.3\n", encoding="utf-8")

    def git_runner(args: tuple[str, ...], cwd: Path) -> GitResult:
        del cwd
        responses = {
            ("git", "describe", "--tags", "--always", "--dirty"): "v1.2.3",
            ("git", "rev-parse", "--short=12", "HEAD"): "abc123def456",
            ("git", "rev-list", "--count", "HEAD"): "42",
            ("git", "rev-parse", "--abbrev-ref", "HEAD"): "feature/version",
            ("git", "status", "--porcelain"): "",
        }
        return GitResult(stdout=responses[args], returncode=0)

    metadata = load_version_metadata(project_root=tmp_path, environ={}, git_runner=git_runner)

    assert metadata.version == "1.2.3"
    assert metadata.build_version == "v1.2.3+42.abc123def456.feature-version"


def test_build_version_changes_when_git_commit_changes(tmp_path: Path) -> None:
    (tmp_path / "VERSION").write_text("1.2.3\n", encoding="utf-8")

    def git_runner_for(sha: str) -> Callable[[tuple[str, ...], Path], GitResult]:
        def git_runner(args: tuple[str, ...], cwd: Path) -> GitResult:
            del cwd
            responses = {
                ("git", "describe", "--tags", "--always", "--dirty"): sha,
                ("git", "rev-parse", "--short=12", "HEAD"): sha,
                ("git", "rev-list", "--count", "HEAD"): "7",
                ("git", "rev-parse", "--abbrev-ref", "HEAD"): "main",
                ("git", "status", "--porcelain"): "",
            }
            return GitResult(stdout=responses[args], returncode=0)

        return git_runner

    first = load_version_metadata(project_root=tmp_path, environ={}, git_runner=git_runner_for("111111111111"))
    second = load_version_metadata(project_root=tmp_path, environ={}, git_runner=git_runner_for("222222222222"))

    assert first.build_version != second.build_version


def test_load_version_metadata_prefers_environment_overrides(tmp_path: Path) -> None:
    metadata = load_version_metadata(
        project_root=tmp_path,
        environ={"VBINVEST_VERSION": "9.9.9", "VBINVEST_BUILD_VERSION": "manual-build"},
    )

    assert metadata.version == "9.9.9"
    assert metadata.build_version == "manual-build"


def test_load_version_metadata_treats_empty_environment_as_empty(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    (tmp_path / "VERSION").write_text("1.2.3\n", encoding="utf-8")
    monkeypatch.setenv("VBINVEST_VERSION", "9.9.9")

    metadata = load_version_metadata(project_root=tmp_path, environ={})

    assert metadata.version == "1.2.3"


def test_load_version_metadata_falls_back_when_version_and_git_are_unavailable(tmp_path: Path) -> None:
    def failing_git_runner(args: tuple[str, ...], cwd: Path) -> GitResult:
        del args, cwd
        return GitResult(stdout="", returncode=1)

    metadata = load_version_metadata(project_root=tmp_path, environ={}, git_runner=failing_git_runner)

    assert metadata.version == "0.1.0"
    assert metadata.build_version == "0.1.0+unknown"


def test_load_version_metadata_marks_dirty_worktree(tmp_path: Path) -> None:
    (tmp_path / "VERSION").write_text("1.2.3\n", encoding="utf-8")

    def git_runner(args: tuple[str, ...], cwd: Path) -> GitResult:
        del cwd
        responses = {
            ("git", "describe", "--tags", "--always", "--dirty"): "abc123",
            ("git", "rev-parse", "--short=12", "HEAD"): "abc123abc123",
            ("git", "rev-list", "--count", "HEAD"): "5",
            ("git", "rev-parse", "--abbrev-ref", "HEAD"): "develop",
            ("git", "status", "--porcelain"): " M scripts/api.py",
        }
        return GitResult(stdout=responses[args], returncode=0)

    metadata = load_version_metadata(project_root=tmp_path, environ={}, git_runner=git_runner)

    assert metadata.build_version == "abc123+5.abc123abc123.develop.dirty"


def test_default_git_runner_times_out(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(version_module, "GIT_TIMEOUT_SECONDS", 0.01)

    result = default_git_runner((sys.executable, "-c", "import time; time.sleep(1)"), tmp_path)

    assert result == GitResult(stdout="", returncode=1)
