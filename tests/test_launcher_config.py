"""Tests for scripts.lib.launcher_config — port/host parsing and defaults."""

import argparse

import pytest

from scripts.lib.launcher_config import (
    DEFAULT_HOST,
    DEFAULT_PREFERRED_PORT,
    DEFAULT_SCAN_END,
    DEFAULT_SCAN_START,
    LauncherConfig,
    parse_host,
    parse_port,
)

# ---------------------------------------------------------------------------
# parse_port
# ---------------------------------------------------------------------------


def test_parse_port_valid():
    assert parse_port("8080") == 8080
    assert parse_port("1") == 1
    assert parse_port("65535") == 65535


def test_parse_port_invalid_string():
    with pytest.raises(argparse.ArgumentTypeError, match="invalid port"):
        parse_port("abc")


def test_parse_port_out_of_range():
    with pytest.raises(argparse.ArgumentTypeError, match="invalid port"):
        parse_port("0")
    with pytest.raises(argparse.ArgumentTypeError, match="invalid port"):
        parse_port("-1")
    with pytest.raises(argparse.ArgumentTypeError, match="invalid port"):
        parse_port("65536")


# ---------------------------------------------------------------------------
# parse_host
# ---------------------------------------------------------------------------


def test_parse_host_valid():
    assert parse_host("127.0.0.1") == "127.0.0.1"
    assert parse_host("localhost") == "localhost"


def test_parse_host_rejects_wildcard():
    for host in ("0.0.0.0", "::", "::0", "0:0:0:0:0:0:0:0"):
        with pytest.raises(argparse.ArgumentTypeError, match="loopback"):
            parse_host(host)


# ---------------------------------------------------------------------------
# LauncherConfig defaults
# ---------------------------------------------------------------------------


def test_launcher_config_defaults():
    config = LauncherConfig()
    assert config.host == DEFAULT_HOST
    assert config.preferred_port == DEFAULT_PREFERRED_PORT
    assert config.scan_start == DEFAULT_SCAN_START
    assert config.scan_end == DEFAULT_SCAN_END
    assert config.open_browser is True
    assert config.health_timeout_seconds == 10.0


def test_launcher_config_custom():
    config = LauncherConfig(host="localhost", preferred_port=9999, open_browser=False)
    assert config.host == "localhost"
    assert config.preferred_port == 9999
    assert config.open_browser is False
