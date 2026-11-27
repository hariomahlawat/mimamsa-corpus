"""Network confinement: only S1 (fetch) may open a connection.

Every other stage runs inside `no_network()`, which makes any socket connect, DNS lookup or connection attempt from
this process raise NetworkForbidden. Child processes (the .NET accelerator builder) contain no network code; OS-level
isolation of children (firewall rules) needs administrator rights and is not applied on the development host.
"""
from __future__ import annotations

import contextlib
import socket


class NetworkForbidden(RuntimeError):
    pass


def _deny(*_a, **_k):
    raise NetworkForbidden("network use outside stage S1 (fetch) is forbidden")


@contextlib.contextmanager
def no_network():
    saved = (socket.socket.connect, socket.socket.connect_ex, socket.create_connection, socket.getaddrinfo)
    socket.socket.connect = _deny          # type: ignore[method-assign]
    socket.socket.connect_ex = _deny       # type: ignore[method-assign]
    socket.create_connection = _deny       # type: ignore[assignment]
    socket.getaddrinfo = _deny             # type: ignore[assignment]
    try:
        yield
    finally:
        socket.socket.connect, socket.socket.connect_ex, socket.create_connection, socket.getaddrinfo = saved  # type: ignore[method-assign]
