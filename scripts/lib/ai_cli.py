from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class AICliStatus:
    name: str
    installed: bool
    authenticated: bool
    path: str | None
    login_command: str
    risk_label: str

    def as_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "installed": self.installed,
            "authenticated": self.authenticated,
            "path": self.path,
            "login_command": self.login_command,
            "risk_label": self.risk_label,
        }


def detect_ai_cli(name: str, *, executable_path: str | None = None, login_command: str) -> AICliStatus:
    path = _resolve_executable(name, executable_path)
    if not path:
        return AICliStatus(
            name=name,
            installed=False,
            authenticated=False,
            path=None,
            login_command=login_command,
            risk_label="계정 제한/정지 가능성 있음",
        )
    authenticated = _check_authenticated(path)
    return AICliStatus(
        name=name,
        installed=True,
        authenticated=authenticated,
        path=path,
        login_command=login_command,
        risk_label="계정 제한/정지 가능성 있음",
    )


def _resolve_executable(name: str, executable_path: str | None) -> str | None:
    if executable_path is not None:
        candidate = Path(executable_path).expanduser()
        if candidate.is_file() and candidate.stat().st_mode & 0o111:
            return str(candidate)
        return None
    return shutil.which(name)


def _check_authenticated(path: str) -> bool:
    try:
        completed = subprocess.run(
            [path, "auth", "status"],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
    except (FileNotFoundError, PermissionError, subprocess.TimeoutExpired):
        return False
    output = f"{completed.stdout}\n{completed.stderr}".lower()
    return completed.returncode == 0 and ("authenticated" in output or "logged in" in output)
