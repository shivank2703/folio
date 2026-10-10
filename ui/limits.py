"""Fair-use limits for the public demo, which spends the maintainer's API credit.

Three layers, each stopping a different kind of over-use:

- per browser session, 10 questions (ui/app.py): keeps a casual visit short;
  a refresh resets it, so it is a courtesy, not a control;
- per visitor per day, 25 answered questions: a refresh does not reset it;
- all visitors together per day, 500 answered questions: the spend ceiling.
  On Claude Haiku 5.5 a question costs $0.0012 on average and $0.0020 at
  most (measured 11 Oct 2026), so the ceiling is about $1 a day and $20 of
  credit outlasts a month of abuse rather than an afternoon of it.

Only questions that reach the model count against the daily limits. A
question refused at the similarity floor costs nothing and stays free.

Not for the maintainer: running locally (a localhost URL) is never limited, and
on the deployed app a session opened with ?owner=<FOLIO_OWNER_KEY> is exempt.
The key lives only in the host's secrets settings.

Counts live in the server process, shared by every session (st.cache_resource),
so a container restart resets them; the monthly spend limit set in the
Anthropic Console stays the hard backstop. A visitor is a salted hash of their
address, never the address itself, and an address can be spoofed, so this is
fair use, not security.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import threading
import time
import urllib.parse

PER_VISITOR_DAILY = 25
GLOBAL_DAILY = 500


class DailyLimiter:
    """Counts answered questions per visitor and in total, for the current UTC day."""

    def __init__(self, per_visitor: int = PER_VISITOR_DAILY, total: int = GLOBAL_DAILY, clock=time.time):
        self.per_visitor, self.total, self.clock = per_visitor, total, clock
        self._lock = threading.Lock()
        self._day = ""
        self._counts: dict[str, int] = {}
        # Salt per process: hashes cannot be matched to addresses later, or
        # across restarts, and nothing about a visitor outlives the container.
        self._salt = secrets.token_bytes(16)

    def visitor(self, address: str | None) -> str:
        return hashlib.sha256(self._salt + (address or "unknown").encode()).hexdigest()[:16]

    def _roll(self) -> None:
        day = time.strftime("%Y-%m-%d", time.gmtime(self.clock()))
        if day != self._day:
            self._day, self._counts = day, {}

    def take(self, visitor: str) -> str | None:
        """Spend one answered question for this visitor; return why not, if over a limit.

        Check and count happen under one lock, so two sessions arriving
        together cannot both take the last question of the day.
        """
        with self._lock:
            self._roll()
            if sum(self._counts.values()) >= self.total:
                return "total"
            if self._counts.get(visitor, 0) >= self.per_visitor:
                return "visitor"
            self._counts[visitor] = self._counts.get(visitor, 0) + 1
            return None


def visitor_address(ip_address: str | None, headers) -> str | None:
    """The visitor's address: the first X-Forwarded-For hop if a proxy set one, else the socket's.

    Behind a hosting proxy the socket address can be the proxy's own, which
    would make every visitor one visitor and turn the per-visitor limit into a
    second global one.
    """
    forwarded = (headers.get("X-Forwarded-For") or "").split(",")[0].strip() if headers else ""
    return forwarded or ip_address


LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", "[::1]"}


def is_owner(app_url: str | None, offered_key: str | None, owner_key: str | None) -> bool:
    """True for the maintainer: a local run, or the owner key offered in the URL.

    "Local" is read from the URL the app is being served at, not from a
    missing client address: if a host ever reported no address, deciding by
    address would exempt every visitor, while deciding by URL fails closed.
    The key comparison is constant-time, and an unset or empty secret never
    matches, so forgetting to configure it limits the maintainer rather than
    exempting everyone.
    """
    host = urllib.parse.urlsplit(app_url or "").hostname
    if host in LOCAL_HOSTS:
        return True
    if not owner_key or not offered_key:
        return False
    return hmac.compare_digest(offered_key.encode(), owner_key.encode())
