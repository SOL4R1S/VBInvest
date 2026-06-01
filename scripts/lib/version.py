from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Mapping, Protocol

DEFAULT_VERSION: Final = "0.1.0"
GIT_TIMEOUT_SECONDS: Final = 2.0


@dataclass(frozen=True, slots=True)
class GitResult:
    stdout: str
    returncode: int


@dataclass(frozen=True, slots=True)
class VersionMetadata:
    version: str
    build_version: str


class GitRunner(Protocol):
    def __call__(self, args: tuple[str, ...], cwd: Path) -> GitResult: ...


def default_git_runner(args: tuple[str, ...], cwd: Path) -> GitResult:
    try:
        completed = subprocess.run(
            args,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=GIT_TIMEOUT_SECONDS,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return GitResult(stdout="", returncode=1)
    return GitResult(stdout=completed.stdout.strip(), returncode=completed.returncode)


def load_version_metadata(
    project_root: Path | None = None,
    environ: Mapping[str, str] | None = None,
    git_runner: GitRunner = default_git_runner,
) -> VersionMetadata:
    root = project_root or Path(__file__).resolve().parents[2]
    env = os.environ if environ is None else environ
    version = env.get("VBINVEST_VERSION") or _read_version(root)
    build_override = env.get("VBINVEST_BUILD_VERSION")
    if build_override:
        return VersionMetadata(version=version, build_version=build_override)
    return VersionMetadata(version=version, build_version=_build_version(root, version, git_runner))


def _read_version(project_root: Path) -> str:
    version_path = project_root / "VERSION"
    try:
        version = version_path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return DEFAULT_VERSION
    return version or DEFAULT_VERSION


def _build_version(project_root: Path, version: str, git_runner: GitRunner) -> str:
    describe = _git_stdout(git_runner, ("git", "describe", "--tags", "--always", "--dirty"), project_root)
    sha = _git_stdout(git_runner, ("git", "rev-parse", "--short=12", "HEAD"), project_root)
    count = _git_stdout(git_runner, ("git", "rev-list", "--count", "HEAD"), project_root)
    branch = _git_stdout(git_runner, ("git", "rev-parse", "--abbrev-ref", "HEAD"), project_root)
    status = _git_stdout(git_runner, ("git", "status", "--porcelain"), project_root)
    if not describe or not sha or not count or not branch:
        return f"{version}+unknown"
    dirty_suffix = ".dirty" if status else ""
    return f"{_clean_token(describe)}+{_clean_token(count)}.{_clean_token(sha)}.{_clean_token(branch)}{dirty_suffix}"


def _git_stdout(git_runner: GitRunner, args: tuple[str, ...], project_root: Path) -> str:
    result = git_runner(args, project_root)
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def _clean_token(value: str) -> str:
    cleaned = re.sub(r"[^0-9A-Za-z.-]+", "-", value.strip())
    return cleaned.strip(".-") or "unknown"
