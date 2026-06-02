from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

from scripts.lib.config import app_data_dir


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PREFERRED_PORT = 4173
DEFAULT_SCAN_START = 4174
DEFAULT_SCAN_END = 4273


def parse_port(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid port: {value}") from exc
    if parsed <= 0 or parsed >= 2**16:
        raise argparse.ArgumentTypeError(f"invalid port: {value}")
    return parsed


def parse_host(value: str) -> str:
    if value in {"0.0.0.0", "::", "::0", "0:0:0:0:0:0:0:0"}:
        raise argparse.ArgumentTypeError("host must be loopback/localhost-only (for security)")
    return value


@dataclass
class LauncherConfig:
    host: str = DEFAULT_HOST
    preferred_port: int = DEFAULT_PREFERRED_PORT
    scan_start: int = DEFAULT_SCAN_START
    scan_end: int = DEFAULT_SCAN_END
    app_data_dir: Path = Path()
    frontend_out_dir: Path = Path()
    open_browser: bool = True
    session_file: Path | None = None
    browser_open_log: Path | None = None
    health_timeout_seconds: float = 10.0
    health_poll_interval_seconds: float = 0.1
    shutdown_timeout_seconds: float = 0.5

    def __post_init__(self) -> None:
        if self.app_data_dir == Path():
            self.app_data_dir = app_data_dir()
        if self.frontend_out_dir == Path():
            self.frontend_out_dir = Path(__file__).resolve().parents[2] / "frontend" / "out"
