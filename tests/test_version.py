"""Tests for scripts.lib.version — version metadata loading."""

from pathlib import Path

from scripts.lib.version import (
    DEFAULT_VERSION,
    GitResult,
    _clean_token,
    load_version_metadata,
)


def _fake_git(responses: dict[str, str]):
    """Return a git_runner that returns canned responses keyed by a prefix of the subcommand."""

    def runner(args: tuple[str, ...], cwd: Path) -> GitResult:
        joined = " ".join(args[1:])
        for key, stdout in responses.items():
            if joined.startswith(key):
                return GitResult(stdout=stdout, returncode=0)
        return GitResult(stdout="", returncode=1)

    return runner


def test_default_version_no_file(tmp_path):
    meta = load_version_metadata(project_root=tmp_path, environ={})
    assert meta.version == DEFAULT_VERSION


def test_version_from_file(tmp_path):
    (tmp_path / "VERSION").write_text("1.2.3\n", encoding="utf-8")
    meta = load_version_metadata(project_root=tmp_path, environ={})
    assert meta.version == "1.2.3"


def test_version_from_env(tmp_path):
    meta = load_version_metadata(project_root=tmp_path, environ={"VBINVEST_VERSION": "9.9.9"})
    assert meta.version == "9.9.9"


def test_build_version_override(tmp_path):
    meta = load_version_metadata(
        project_root=tmp_path,
        environ={"VBINVEST_VERSION": "1.0.0", "VBINVEST_BUILD_VERSION": "custom-build"},
    )
    assert meta.build_version == "custom-build"


def test_build_version_from_git(tmp_path):
    git = _fake_git(
        {
            "describe --tags": "v1.0.0-5-gabc123",
            "rev-parse --short": "abc123def456",
            "rev-list --count": "42",
            "rev-parse --abbrev": "main",
            "status --porcelain": "",
        }
    )
    meta = load_version_metadata(project_root=tmp_path, environ={"VBINVEST_VERSION": "1.0.0"}, git_runner=git)
    assert "42" in meta.build_version
    assert "abc123def456" in meta.build_version
    assert "main" in meta.build_version
    assert ".dirty" not in meta.build_version


def test_build_version_dirty(tmp_path):
    git = _fake_git(
        {
            "describe --tags": "v1.0.0",
            "rev-parse --short": "abc123",
            "rev-list --count": "10",
            "rev-parse --abbrev": "dev",
            "status --porcelain": "M file.py",
        }
    )
    meta = load_version_metadata(project_root=tmp_path, environ={"VBINVEST_VERSION": "1.0.0"}, git_runner=git)
    assert meta.build_version.endswith(".dirty")


def test_build_version_no_git(tmp_path):
    git = _fake_git({})
    meta = load_version_metadata(project_root=tmp_path, environ={"VBINVEST_VERSION": "1.0.0"}, git_runner=git)
    assert meta.build_version == "1.0.0+unknown"


def test_clean_token():
    assert _clean_token("v1.0.0-5-gabc") == "v1.0.0-5-gabc"
    assert _clean_token("feature/my branch") == "feature-my-branch"
    assert _clean_token("  ") == "unknown"
    assert _clean_token("...") == "unknown"
