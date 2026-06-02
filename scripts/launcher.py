from __future__ import annotations

import argparse
import json
import os
import secrets
import sys
import threading
import time
import webbrowser
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import uvicorn

from scripts.lib.db_factory import build_database_from_local_config
from scripts.lib.launcher_config import DEFAULT_HOST, DEFAULT_PREFERRED_PORT, DEFAULT_SCAN_END, DEFAULT_SCAN_START, LauncherConfig, parse_host, parse_port
from scripts.lib.launcher_ports import PortSelector, ReservedSocket
from scripts.lib.version import load_version_metadata


LAUNCHER_ENV_KEYS = (
    "VBINVEST_LOCAL_SESSION_TOKEN",
    "VBINVEST_LOCAL_SESSION_USER",
    "VBINVEST_LOCAL_SHUTDOWN_ENABLED",
    "VBINVEST_FRONTEND_OUT_DIR",
    "VBINVEST_API_BASE_URL",
    "VBINVEST_CONFIG_PATH",
    "VBINVEST_SELECTED_PORT",
)


def open_browser(url: str) -> bool:
    return bool(webbrowser.open(url, new=1, autoraise=True))


class LocalLauncher:
    def __init__(self, config: LauncherConfig) -> None:
        self.config = config
        self.config.app_data_dir.mkdir(parents=True, exist_ok=True)
        if self.config.session_file is None:
            self.config.session_file = self.config.app_data_dir / "session.json"
        if self.config.browser_open_log is None:
            self.config.browser_open_log = self.config.app_data_dir / "browser-open.log"

        self._selected_port: int | None = None
        self._reserved: ReservedSocket | None = None
        self._server: uvicorn.Server | None = None
        self._server_thread: threading.Thread | None = None
        self._previous_env: dict[str, str | None] | None = None

    def _resolve_selected_port(self) -> int:
        if self._selected_port is not None:
            return self._selected_port
        if self._reserved is not None:
            return self._reserved.port
        raise RuntimeError("selected port is not assigned")

    def build_child_env(self) -> dict[str, str]:
        env = os.environ.copy()
        token = secrets.token_urlsafe(32)
        env["VBINVEST_LOCAL_SESSION_TOKEN"] = token
        env["VBINVEST_LOCAL_SESSION_USER"] = "local-owner"
        env["VBINVEST_LOCAL_SHUTDOWN_ENABLED"] = "1"
        env["VBINVEST_FRONTEND_OUT_DIR"] = str(self.config.frontend_out_dir)
        env["VBINVEST_API_BASE_URL"] = f"http://{self.config.host}:{self._resolve_selected_port()}"
        env.setdefault("VBINVEST_CONFIG_PATH", str(self.config.app_data_dir / "config.toml"))
        env["VBINVEST_SELECTED_PORT"] = str(self._resolve_selected_port())
        return env

    def _append_log(self, message: str) -> None:
        if self.config.browser_open_log is None:
            return
        self.config.browser_open_log.parent.mkdir(parents=True, exist_ok=True)
        with self.config.browser_open_log.open("a", encoding="utf-8") as f:
            f.write(f"{message}\n")

    def _apply_environment(self) -> None:
        if self._previous_env is None:
            self._previous_env = {key: os.environ.get(key) for key in LAUNCHER_ENV_KEYS}
        env = self.build_child_env()
        os.environ.update(env)

    def _restore_environment(self) -> None:
        if self._previous_env is None:
            return
        for key, value in self._previous_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self._previous_env = None

    def _write_session_file(self) -> None:
        assert self.config.session_file is not None
        payload = {
            "selected_url": self.api_base_url(),
            "token": os.environ.get("VBINVEST_LOCAL_SESSION_TOKEN", ""),
            "version": load_version_metadata().version,
            "build_version": load_version_metadata().build_version,
            "selected_port": self._resolve_selected_port(),
            "log_path": str(self.config.app_data_dir / "logs" / "launcher.log"),
        }
        self.config.session_file.parent.mkdir(parents=True, exist_ok=True)
        self.config.session_file.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    def api_base_url(self) -> str:
        return f"http://{self.config.host}:{self._resolve_selected_port()}"

    def _bootstrap_database(self) -> None:
        build_database_from_local_config(environ=os.environ)

    def start(self) -> str:
        if self._server_thread and self._server_thread.is_alive():
            return self.api_base_url()

        reserved = PortSelector(
            host=self.config.host,
            preferred_port=self.config.preferred_port,
            scan_start=self.config.scan_start,
            scan_end=self.config.scan_end,
        ).reserve()
        self._reserved = reserved
        self._selected_port = reserved.port

        self._apply_environment()
        self._bootstrap_database()
        self._write_session_file()
        from scripts import api

        api.LOCAL_SHUTDOWN_CALLBACK = self._request_server_exit
        uvicorn_config = uvicorn.Config(api.app, host=self.config.host, port=self._selected_port, log_level="info")
        self._server = uvicorn.Server(uvicorn_config)
        self._server_thread = threading.Thread(
            target=self._server.run,
            kwargs={"sockets": [reserved.socket]},
            name="vbinvest-backend", daemon=False,
        )
        self._server_thread.start()

        if self._server_thread.is_alive():
            self.wait_for_health()
        if self.config.open_browser:
            success = open_browser(self.api_base_url())
            self._append_log(f"browser_opened={success} url={self.api_base_url()}")
        return self.api_base_url()

    def _request_server_exit(self) -> None:
        if self._server is not None:
            setattr(self._server, "should_exit", True)

    def wait_for_health(self) -> None:
        deadline = time.time() + self.config.health_timeout_seconds
        interval = min(self.config.health_poll_interval_seconds, max(0.05, self.config.health_timeout_seconds / 5))
        while time.time() < deadline:
            try:
                with urlopen(Request(self.api_base_url() + "/health", method="GET"), timeout=1.0) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                if isinstance(payload, dict) and payload.get("status") == "ok" and payload.get("version") and payload.get("build_version"):
                    return
            except (OSError, URLError, json.JSONDecodeError, ValueError):
                if self._server_thread is None or not self._server_thread.is_alive():
                    break
            time.sleep(interval)

        raise TimeoutError("backend did not become healthy in time")

    def shutdown(self) -> None:
        if self._server is not None:
            setattr(self._server, "should_exit", True)
        try:
            from scripts import api

            if api.LOCAL_SHUTDOWN_CALLBACK is self._request_server_exit:
                api.LOCAL_SHUTDOWN_CALLBACK = None
        except ImportError:
            pass
        if self._server_thread is not None:
            self._server_thread.join(self.config.shutdown_timeout_seconds)
        if self._reserved is not None:
            try:
                self._reserved.socket.close()
            finally:
                self._reserved = None
        self._selected_port = None
        self._restore_environment()

    def run(self) -> int:
        self.start()
        try:
            if self._server_thread is None:
                return 1
            while self._server_thread.is_alive():
                time.sleep(0.2)
        except KeyboardInterrupt:
            return 130
        finally:
            self.shutdown()
        return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run VBinvest local backend and frontend host")
    parser.add_argument("--host", default=DEFAULT_HOST, type=parse_host)
    parser.add_argument("--port", "--preferred-port", dest="port", default=DEFAULT_PREFERRED_PORT, type=parse_port)
    parser.add_argument("--scan-start", type=parse_port, default=DEFAULT_SCAN_START)
    parser.add_argument("--scan-end", type=parse_port, default=DEFAULT_SCAN_END)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--app-data-dir", default=str(LauncherConfig().app_data_dir), help="local app data directory")
    parser.add_argument("--frontend-out-dir", default=str(Path(__file__).resolve().parents[1] / "frontend" / "out"))
    parser.add_argument("--session-file", default="")
    parser.add_argument("--browser-open-log", default="")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    try:
        args = parse_args(argv)
    except SystemExit as exc:
        code = exc.code
        return int(code) if isinstance(code, int) else 1

    config = LauncherConfig(
        host=args.host,
        preferred_port=args.port,
        scan_start=args.scan_start,
        scan_end=args.scan_end,
        app_data_dir=Path(args.app_data_dir),
        frontend_out_dir=Path(args.frontend_out_dir),
        open_browser=not args.no_browser and os.environ.get("VBINVEST_SKIP_BROWSER", "") != "1",
        session_file=Path(args.session_file) if args.session_file else None,
        browser_open_log=Path(args.browser_open_log) if args.browser_open_log else None,
    )
    launcher = LocalLauncher(config)
    return launcher.run()


if __name__ == "__main__":
    raise SystemExit(main())
