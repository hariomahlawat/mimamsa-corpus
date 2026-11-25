"""Portable R2-N01 reference coordinator for synthetic PoC traffic."""
from dataclasses import dataclass
from threading import Event, Lock


@dataclass(frozen=True)
class Handoff:
    outcome: str
    count: int = 0
    attempt: int | None = None


class Delivery:
    def __init__(self, site_limit=8 * 1024**2, connection_limit=256 * 1024):
        if not 0 < connection_limit <= site_limit:
            raise ValueError('invalid credit limits')
        self.site_limit = site_limit
        self.connection_limit = connection_limit
        self._lock = Lock()
        self._writer = Lock()
        self._pending = Event()
        self._revoked = set()
        self._closed = set()
        self._charges = {}
        self._connections = {}
        self._outstanding = 0
        self._next = 0

    @property
    def outstanding(self):
        with self._lock:
            return self._outstanding

    def withdraw(self, copy):
        # One policy writer. Set the flag before waiting for a current handoff.
        with self._writer:
            self._pending.set()
            try:
                with self._lock:
                    self._revoked.add(copy)
            finally:
                self._pending.clear()

    def handoff(self, connection, copy, data, take):
        """take is a bounded, nonblocking adapter accepting an exact prefix.

        A zero denotes proven zero acceptance. None or an exception denotes an
        unresolved transfer. The caller must close an uncertain connection.
        """
        if type(data) is not bytes or not 0 < len(data) <= 64 * 1024:
            raise ValueError('expected bounded immutable bytes')
        with self._lock:
            if self._pending.is_set() or copy in self._revoked or connection in self._closed:
                return Handoff('denied')
            requested = len(data)
            current = self._connections.get(connection, 0)
            if requested > min(self.site_limit - self._outstanding, self.connection_limit - current):
                return Handoff('would_block')
            self._next += 1
            attempt = self._next
            self._charges[attempt] = (connection, requested)
            self._connections[connection] = current + requested
            self._outstanding += requested
            try:
                accepted = take(data)
            except Exception:
                accepted = None
            if type(accepted) is not int or not 0 <= accepted <= requested:
                self._closed.add(connection)
                return Handoff('uncertain', attempt=attempt)
            self._settle(attempt, accepted)
            return Handoff('accepted', accepted, attempt) if accepted else Handoff('would_block')

    def _settle(self, attempt, remaining):
        connection, charged = self._charges[attempt]
        released = charged - remaining
        self._outstanding -= released
        self._connections[connection] -= released
        if remaining:
            self._charges[attempt] = (connection, remaining)
        else:
            del self._charges[attempt]
            if not self._connections[connection]:
                del self._connections[connection]

    def confirm_drain(self, attempt):
        """Release once, only when a trusted adapter can prove drain or termination."""
        with self._lock:
            if attempt not in self._charges:
                return False
            self._settle(attempt, 0)
            return True
