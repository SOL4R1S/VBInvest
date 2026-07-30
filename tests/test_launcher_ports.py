"""Tests for scripts.lib.launcher_ports — port selection."""

from scripts.lib.launcher_ports import PortSelector


def test_is_port_free_invalid():
    selector = PortSelector(host="127.0.0.1", preferred_port=8080, scan_start=9000, scan_end=9010)
    assert selector.is_port_free(0) is False
    assert selector.is_port_free(-1) is False
    assert selector.is_port_free(70000) is False


def test_reserve_preferred():
    selector = PortSelector(host="127.0.0.1", preferred_port=0, scan_start=0, scan_end=0)
    reserved = selector.reserve()
    assert reserved.port > 0
    assert reserved.host == "127.0.0.1"
    reserved.socket.close()


def test_select_port_returns_int():
    selector = PortSelector(host="127.0.0.1", preferred_port=0, scan_start=0, scan_end=0)
    port = selector.select_port()
    assert isinstance(port, int)
    assert port > 0


def test_allocate_fallback():
    selector = PortSelector(host="127.0.0.1", preferred_port=1, scan_start=1, scan_end=1)
    reserved = selector.allocate_fallback_port()
    assert reserved.port > 0
    reserved.socket.close()


def test_reserve_with_hint():
    selector = PortSelector(host="127.0.0.1", preferred_port=0, scan_start=0, scan_end=0)
    reserved = selector.reserve(hint=0)
    assert reserved.port > 0
    reserved.socket.close()
