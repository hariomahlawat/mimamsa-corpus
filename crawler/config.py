"""Load and check config/sources.yaml, and answer host-policy questions."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import yaml

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = ROOT / "config" / "sources.yaml"
IST = timezone(timedelta(hours=5, minutes=30))
PLACEHOLDER_EMAIL = "CHANGE-ME@example.org"
DOC_ID_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

REQUIRED_DEFAULTS = {
    "user_agent": str,
    "contact_email": str,
    "min_delay_seconds": (int, float),
    "timeout_seconds": (int, float),
    "max_retries": int,
    "backoff_base_seconds": (int, float),
    "obey_robots_txt": bool,
    "follow_offsite_links": bool,
    "quiet_hours_ist": dict,
    "max_file_mb": (int, float),
}


class ConfigError(ValueError):
    pass


@dataclass
class ConfigReport:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def normalise_host(host: str) -> str:
    return host.strip().lower().rstrip(".")


def url_host(url: str) -> str:
    return normalise_host(urlsplit(url).hostname or "")


@dataclass
class Config:
    raw: dict[str, Any]
    path: Path

    @property
    def defaults(self) -> dict[str, Any]:
        return self.raw["defaults"]

    @property
    def sources(self) -> dict[str, dict[str, Any]]:
        return self.raw["sources"]

    @property
    def blocked_hosts(self) -> set[str]:
        return {normalise_host(h) for h in self.raw.get("blocked_hosts", [])}

    def source(self, name: str) -> dict[str, Any]:
        try:
            return self.sources[name]
        except KeyError:
            raise ConfigError(f"unknown source {name!r}; known: {', '.join(self.sources)}") from None

    def enabled_sources(self) -> list[str]:
        return [n for n, s in self.sources.items() if s.get("enabled")]

    def allowed_hosts(self, name: str) -> set[str]:
        s = self.source(name)
        hosts = set(s.get("allowed_hosts", []))
        for court in s.get("courts", []):
            hosts.update(court.get("allowed_hosts", []))
        return {normalise_host(h) for h in hosts}

    def setting(self, name: str, key: str) -> Any:
        """Per-source override, else global default."""
        s = self.source(name)
        return s.get(key, self.defaults[key])

    def is_url_allowed(self, name: str, url: str) -> tuple[bool, str]:
        """Allow-list check. Returns (allowed, reason)."""
        parts = urlsplit(url)
        if parts.scheme not in ("http", "https"):
            return False, f"scheme {parts.scheme!r} not allowed"
        host = url_host(url)
        if not host:
            return False, "no host"
        if host in self.blocked_hosts:
            return False, f"host {host} is on blocked_hosts"
        if host not in self.allowed_hosts(name):
            return False, f"host {host} not in allowed_hosts for {name}"
        return True, "ok"

    def user_agent_is_placeholder(self) -> bool:
        email = self.defaults["contact_email"].strip().lower()
        return email == PLACEHOLDER_EMAIL.lower() or "@" not in email

    def in_quiet_hours(self, now: datetime | None = None) -> bool:
        """True if `now` falls in the IST window when heavy sources may run."""
        q = self.defaults["quiet_hours_ist"]
        return in_window((now or datetime.now(timezone.utc)).astimezone(IST).time(),
                         _parse_hhmm(q["start"]), _parse_hhmm(q["end"]))

    def may_run_now(self, name: str, now: datetime | None = None) -> bool:
        return not self.source(name).get("heavy") or self.in_quiet_hours(now)


def _parse_hhmm(s: str) -> time:
    h, m = s.split(":")
    return time(int(h), int(m))


def in_window(t: time, start: time, end: time) -> bool:
    if start <= end:
        return start <= t < end
    return t >= start or t < end  # window crosses midnight


def load_config(path: Path | str = DEFAULT_CONFIG) -> Config:
    path = Path(path)
    with path.open(encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    if not isinstance(raw, dict) or "defaults" not in raw or "sources" not in raw:
        raise ConfigError(f"{path}: needs top-level 'defaults' and 'sources'")
    return Config(raw=raw, path=path)


def _iter_urls(src: dict[str, Any]):
    for key in ("seeds", "benches"):
        for item in src.get(key, []) or []:
            if item.get("url"):
                yield key, item["url"]
    if src.get("base_url"):
        yield "base_url", src["base_url"]


def _iter_targets(src: dict[str, Any]):
    for key in ("targets", "also_search"):
        for item in src.get(key, []) or []:
            yield key, item


def check_config(cfg: Config) -> ConfigReport:
    """Static checks. Errors block any run; warnings are shown in dry-run."""
    r = ConfigReport()
    d = cfg.defaults
    for key, typ in REQUIRED_DEFAULTS.items():
        if key not in d:
            r.errors.append(f"defaults.{key} missing")
        elif not isinstance(d[key], typ) or (typ is int and isinstance(d[key], bool)):
            r.errors.append(f"defaults.{key} has wrong type {type(d[key]).__name__}")
    if r.errors:
        return r
    if d["min_delay_seconds"] < 1:
        r.errors.append("defaults.min_delay_seconds below 1 s is not polite")
    if not d["obey_robots_txt"]:
        r.errors.append("defaults.obey_robots_txt must be true")
    if d["follow_offsite_links"]:
        r.errors.append("defaults.follow_offsite_links must be false")
    for k in ("start", "end"):
        try:
            _parse_hhmm(d["quiet_hours_ist"][k])
        except Exception:
            r.errors.append(f"defaults.quiet_hours_ist.{k} must be HH:MM")
    if cfg.user_agent_is_placeholder():
        r.warnings.append("contact_email is still the placeholder; real runs will refuse to start")

    blocked = cfg.blocked_hosts
    seen_ids: dict[str, str] = {}
    for name, src in cfg.sources.items():
        where = f"sources.{name}"
        if not isinstance(src.get("phase"), int):
            r.errors.append(f"{where}.phase must be an integer")
        hosts = cfg.allowed_hosts(name)
        if src.get("enabled") and not hosts:
            r.errors.append(f"{where} is enabled but has no allowed_hosts")
        for h in hosts & blocked:
            r.errors.append(f"{where}: allowed host {h} is also on blocked_hosts")
        if "min_delay_seconds" in src and src["min_delay_seconds"] < d["min_delay_seconds"]:
            r.errors.append(f"{where}.min_delay_seconds lower than the global minimum")
        for key, url in _iter_urls(src):
            ok, why = cfg.is_url_allowed(name, url)
            if not ok:
                r.errors.append(f"{where}.{key}: {url}: {why}")
        for key, t in _iter_targets(src):
            did = t.get("doc_id", "")
            if not DOC_ID_RE.match(did):
                r.errors.append(f"{where}.{key}: bad doc_id {did!r}")
            if not t.get("title"):
                r.errors.append(f"{where}.{key}: {did} has no title")
            if did in seen_ids and seen_ids[did] != name:
                r.warnings.append(f"{did} is targeted by both {seen_ids[did]} and {name} (first hit wins)")
            seen_ids.setdefault(did, name)
        if src.get("enabled") and src.get("verify"):
            r.warnings.append(f"{where} is enabled but marked verify: true (unchecked against live site)")
    return r
