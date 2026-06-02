from __future__ import annotations

import json
import os
import socket
from urllib.error import URLError

import pytest

from scripts import launcher


def _free_port() -> int:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])
    finally:
        sock.close()


class FakeResponse:
    def __init__(self, payload: dict[str, str], status: int = 200):
        self.status = status
        self._payload = payload

    def read(self) -> bytes:
        return json.dumps(self._payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return None


class FakeJoinableThread:
    def __init__(self, *, alive: bool = True):
        self.alive = alive
        self.join_calls: list[float | None] = []

    def is_alive(self) -> bool:
        return self.alive

    def join(self, timeout: float | None = None) -> None:
        self.join_calls.append(timeout)
        self.alive = False


def test_launcher_exposes_public_api() -> None:
    assert hasattr(launcher, "PortSelector")
    assert hasattr(launcher, "ReservedSocket")
    assert hasattr(launcher, "LauncherConfig")
    assert hasattr(launcher, "LocalLauncher")
    assert callable(launcher.open_browser)
    assert callable(launcher.main)


def test_port_selector_prefers_preferred_port() -> None:
    preferred = _free_port()
    selector = launcher.PortSelector(preferred_port=preferred, host="127.0.0.1", scan_start=preferred + 1, scan_end=preferred + 3)

    reserved = selector.reserve()

    try:
        assert reserved.host == "127.0.0.1"
        assert reserved.port == preferred
    finally:
        reserved.socket.close()


def test_port_selector_falls_back_to_scan_range() -> None:
    preferred = _free_port()
    blocker = launcher.PortSelector(preferred_port=preferred, host="127.0.0.1", scan_start=preferred + 1, scan_end=preferred + 1).reserve()
    selector = launcher.PortSelector(preferred_port=preferred, host="127.0.0.1", scan_start=preferred + 1, scan_end=preferred + 3)

    try:
        reserved = selector.reserve()
        try:
            assert reserved.host == "127.0.0.1"
            assert reserved.port == preferred + 1
        finally:
            reserved.socket.close()
    finally:
        blocker.socket.close()


def test_port_selector_falls_back_to_os_assigned_when_range_exhausted() -> None:
    blocker = launcher.PortSelector(preferred_port=4173, host="127.0.0.1", scan_start=4174, scan_end=4174).reserve()
    selector = launcher.PortSelector(preferred_port=4173, host="127.0.0.1", scan_start=4173, scan_end=4173)

    try:
        reserved = selector.reserve()
        try:
            assert reserved.host == "127.0.0.1"
            assert reserved.port != 4173
            assert 0 < reserved.port < 65536
        finally:
            reserved.socket.close()
    finally:
        blocker.socket.close()


def test_local_launcher_writes_session_and_runtime_environment(tmp_path, monkeypatch) -> None:
    config = launcher.LauncherConfig(
        host="127.0.0.1",
        preferred_port=4173,
        app_data_dir=tmp_path / "app_data",
        frontend_out_dir=tmp_path / "frontend",
        open_browser=False,
        session_file=tmp_path / "session.json",
    )
    monkeypatch.setattr(launcher.secrets, "token_urlsafe", lambda _n=32: "unit-test-token")
    server = launcher.LocalLauncher(config)
    reserved = launcher.PortSelector(preferred_port=4173, host="127.0.0.1", scan_start=4174, scan_end=4174).reserve()
    server._reserved = reserved

    try:
        server._apply_environment()
        server._write_session_file()

        payload = json.loads((tmp_path / "session.json").read_text(encoding="utf-8"))
        assert payload["selected_url"] == f"http://127.0.0.1:{reserved.port}"
        assert payload["token"] == "unit-test-token"
        assert payload["version"]
        assert payload["build_version"]
        assert os.environ["VBINVEST_LOCAL_SESSION_TOKEN"] == "unit-test-token"
        assert os.environ["VBINVEST_LOCAL_SESSION_USER"] == "local-owner"
        assert os.environ["VBINVEST_FRONTEND_OUT_DIR"] == str(tmp_path / "frontend")
        assert os.environ["VBINVEST_API_BASE_URL"] == f"http://127.0.0.1:{reserved.port}"
    finally:
        server.shutdown()


def test_local_launcher_start_uses_uvicorn_server_with_reserved_socket(tmp_path, monkeypatch) -> None:
    config = launcher.LauncherConfig(
        host="127.0.0.1",
        preferred_port=4173,
        scan_start=4174,
        scan_end=4174,
        app_data_dir=tmp_path / "app_data",
        frontend_out_dir=tmp_path / "frontend",
        open_browser=False,
    )
    server = launcher.LocalLauncher(config)
    reserved = launcher.PortSelector(preferred_port=4173, host="127.0.0.1", scan_start=4174, scan_end=4174).reserve()
    started_sockets = []

    class FakeServer:
        should_exit = False

        def run(self, *, sockets):
            started_sockets.extend(sockets)

    class FakeThread:
        def __init__(self, *, target, kwargs, name, daemon):
            self.target = target
            self.kwargs = kwargs
            self.name = name
            self.daemon = daemon

        def start(self) -> None:
            self.target(**self.kwargs)

        def is_alive(self) -> bool:
            return False

        def join(self, timeout: float | None = None) -> None:
            return None

    monkeypatch.setattr(server, "_bootstrap_database", lambda: None)
    monkeypatch.setattr(server, "_write_session_file", lambda: None)
    monkeypatch.setattr(server, "_append_log", lambda _message: None)
    monkeypatch.setattr(launcher.PortSelector, "reserve", lambda _self, _hint=None: reserved)
    monkeypatch.setattr(launcher.uvicorn, "Server", lambda _config: FakeServer())
    monkeypatch.setattr(launcher.threading, "Thread", FakeThread)

    try:
        server.start()

        assert started_sockets == [reserved.socket]
        assert server._resolve_selected_port() == reserved.port
    finally:
        server.shutdown()


def test_local_launcher_wait_for_health_prefers_expected_payload(tmp_path, monkeypatch) -> None:
    config = launcher.LauncherConfig(host="127.0.0.1", preferred_port=4173, app_data_dir=tmp_path / "app_data")
    server = launcher.LocalLauncher(config)
    reserved = launcher.PortSelector(preferred_port=4173, host="127.0.0.1", scan_start=4174, scan_end=4174).reserve()
    server._reserved = reserved
    server._server_thread = FakeJoinableThread(alive=True)
    call_count = 0

    def fake_urlopen(*_args, **_kwargs) -> FakeResponse:
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise URLError("not ready")
        return FakeResponse({"status": "ok", "version": "0.1.0", "build_version": "0.1.0+test"})

    monkeypatch.setattr(launcher, "urlopen", fake_urlopen)

    try:
        server.wait_for_health()
        assert call_count >= 2
    finally:
        reserved.socket.close()


def test_local_launcher_health_validation_rejects_bad_payload(tmp_path, monkeypatch) -> None:
    config = launcher.LauncherConfig(host="127.0.0.1", preferred_port=4173, app_data_dir=tmp_path / "app_data", health_timeout_seconds=0.2)
    server = launcher.LocalLauncher(config)
    reserved = launcher.PortSelector(preferred_port=4173, host="127.0.0.1", scan_start=4174, scan_end=4174).reserve()
    server._reserved = reserved
    server._server_thread = FakeJoinableThread(alive=True)

    def fake_urlopen(*_args, **_kwargs) -> FakeResponse:
        return FakeResponse({"status": "down"})

    monkeypatch.setattr(launcher, "urlopen", fake_urlopen)

    try:
        with pytest.raises(TimeoutError):
            server.wait_for_health()
    finally:
        reserved.socket.close()


def test_local_launcher_shutdown_requests_server_exit_and_joins_thread(tmp_path) -> None:
    config = launcher.LauncherConfig(host="127.0.0.1", preferred_port=4173, app_data_dir=tmp_path / "app_data")
    server = launcher.LocalLauncher(config)
    fake_server = type("FakeServer", (), {"should_exit": False})()
    fake_thread = FakeJoinableThread(alive=True)
    reserved = launcher.PortSelector(preferred_port=4173, host="127.0.0.1", scan_start=4174, scan_end=4174).reserve()
    server._server = fake_server
    server._server_thread = fake_thread
    server._reserved = reserved

    server.shutdown()

    assert fake_server.should_exit is True
    assert fake_thread.join_calls == [config.shutdown_timeout_seconds]


def test_local_launcher_shutdown_restores_process_environment(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("VBINVEST_LOCAL_SHUTDOWN_ENABLED", raising=False)
    monkeypatch.setenv("VBINVEST_API_BASE_URL", "http://127.0.0.1:9999")
    config = launcher.LauncherConfig(
        host="127.0.0.1",
        preferred_port=4173,
        app_data_dir=tmp_path / "app_data",
        frontend_out_dir=tmp_path / "frontend",
        open_browser=False,
    )
    server = launcher.LocalLauncher(config)
    reserved = launcher.PortSelector(preferred_port=4173, host="127.0.0.1", scan_start=4174, scan_end=4174).reserve()
    server._reserved = reserved

    try:
        server._apply_environment()
        assert os.environ["VBINVEST_LOCAL_SHUTDOWN_ENABLED"] == "1"

        server.shutdown()

        assert "VBINVEST_LOCAL_SHUTDOWN_ENABLED" not in os.environ
        assert os.environ["VBINVEST_API_BASE_URL"] == "http://127.0.0.1:9999"
    finally:
        reserved.socket.close()


def test_parse_args_rejects_invalid_host() -> None:
    with pytest.raises(SystemExit):
        launcher.parse_args(["--host", "0.0.0.0"])
