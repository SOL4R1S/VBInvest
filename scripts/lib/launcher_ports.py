from __future__ import annotations

import socket
from dataclasses import dataclass


@dataclass(frozen=True)
class ReservedSocket:
    host: str
    port: int
    socket: socket.socket


class PortSelector:
    def __init__(self, *, host: str, preferred_port: int, scan_start: int, scan_end: int) -> None:
        self.host = host
        self.preferred_port = preferred_port
        self.scan_start = scan_start
        self.scan_end = scan_end

    def is_port_free(self, port: int) -> bool:
        if port <= 0 or port > 65535:
            return False
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.bind((self.host, port))
            return True
        except OSError:
            return False
        finally:
            sock.close()

    def allocate_fallback_port(self) -> ReservedSocket:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind((self.host, 0))
        sock.listen()
        port = sock.getsockname()[1]
        return ReservedSocket(self.host, port, sock)

    def select_port(self) -> int:
        return self.reserve().port

    def reserve(self, hint: int | None = None) -> ReservedSocket:
        candidates = [self.preferred_port]
        if hint is not None and self.scan_start <= hint <= self.scan_end:
            candidates.append(hint)
        if self.scan_start <= self.scan_end:
            candidates.extend(range(self.scan_start, self.scan_end + 1))
        for candidate in dict.fromkeys(candidates):
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                sock.bind((self.host, candidate))
                sock.listen()
                return ReservedSocket(self.host, candidate, sock)
            except OSError:
                sock.close()
        return self.allocate_fallback_port()
