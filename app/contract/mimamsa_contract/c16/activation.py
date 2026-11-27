"""Reference model of crash-consistent activation, rollback and restore (architecture section 8).

An executable specification, not site code: the B1 importer and service must implement the same states and
invariants, and these tests are the acceptance oracle for that implementation. Durable stores are modelled as plain
Python structures; a "crash" stops a transition at any boundary, and recover() must restore the invariants.

Commit domains and the single commit decision
- journal         append-only activation journal (durable, outside the database and generations): BEGIN, DECIDED,
                  OPEN or ABORTED per transaction. The DECIDED entry is the ONE authoritative commit decision.
- db              PostgreSQL: knowledge views and RELEASE_ACTIVATION publication rows (keyed by txn_id: idempotent).
- pointers        ACTIVE / MODELS_ACTIVE files (derived from the journal; rewritten by reconciliation).
- exclusions      ExclusionStore (append-only, monotone; never restored from backup).
- log             activation log (hash chain), one record per DECIDED transaction (keyed by txn_id: idempotent).
Readers pin one generation per request; while a transition or recovery is in progress new pins are refused (the
service returns 503), pinned readers finish on their generation, and retention never deletes a pinned, active,
rollback-target or in-flight generation, nor the sole recovery copy.
"""
from __future__ import annotations

import copy
import hashlib
import json
from collections import Counter

STEPS = ("BEGIN", "DECIDED", "DB_APPLIED", "POINTER_WRITTEN", "EXCLUSIONS_APPLIED", "LOGGED", "OPEN")


class Crash(Exception):
    pass


class Refused(Exception):
    pass


class Site:
    def __init__(self, installed: list[str], active: str, models: str = "M1", keep_previous: int = 2):
        self.installed = list(installed)          # verified, staged generations present on disk (in install order)
        self.journal: list[dict] = []
        self.db = {"views": active, "publication": {}, "site_rows": {"users": 1}}
        self.pointers = {"KNOWLEDGE": active, "MODELS": models}
        self.exclusions = {"seq": 0, "suppressed": frozenset()}
        self.applied = {active: 0}                # exclusion seq applied to each generation
        self.log: list[dict] = []
        self.pins: Counter = Counter()
        self.state = "OPEN"
        self.keep_previous = keep_previous
        self.history = [active]                   # activation order of KNOWLEDGE generations
        self._txn = 0

    # ------------------------------------------------------------------ readers
    def pin(self) -> tuple[str, int]:
        if self.state != "OPEN":
            raise Refused("transition or recovery in progress")
        g = self.pointers["KNOWLEDGE"]
        if self.applied.get(g, -1) != self.exclusions["seq"]:
            raise Refused("exclusions not applied to the active generation")
        self.pins[g] += 1
        return g, self.exclusions["seq"]

    def unpin(self, g: str):
        self.pins[g] -= 1

    # ------------------------------------------------------------------ exclusions
    def accept_exclusion(self, items: set[str]):
        """Signed update accepted: monotone, applied at once to the active and retained generations when serving;
        during a transition the transition re-applies the newest state before OPEN."""
        self.exclusions = {"seq": self.exclusions["seq"] + 1, "suppressed": self.exclusions["suppressed"] | frozenset(items)}
        if self.state == "OPEN":
            for g in self.installed:
                self.applied[g] = self.exclusions["seq"]

    # ------------------------------------------------------------------ transitions
    def transition(self, target: str, to: str, action: str = "ACTIVATE", crash_after: str | None = None, hook=None):
        if self.state != "OPEN":
            raise Refused("another transition or recovery is in progress")
        if target == "KNOWLEDGE" and to not in self.installed:
            raise Refused("target generation is not staged and verified")
        self._txn += 1
        txn = f"TX-{self._txn:08d}-{hashlib.sha256(f'{target}|{to}|{self._txn}'.encode()).hexdigest()[:12]}"
        self.state = "SWITCHING"
        frm = self.pointers[target]
        self._step(txn, "BEGIN", lambda: self.journal.append({"txn": txn, "step": "BEGIN", "target": target, "from": frm, "to": to, "action": action}), crash_after, hook)
        self._step(txn, "DECIDED", lambda: self.journal.append({"txn": txn, "step": "DECIDED"}), crash_after, hook)
        self._roll_forward(txn, crash_after, hook)
        return txn

    def _step(self, txn, name, fn, crash_after, hook):
        fn()
        if hook:
            hook(name)
        if crash_after == name:
            self.state = "RECOVERING"
            raise Crash(name)

    def _entry(self, txn):
        return next(e for e in self.journal if e["txn"] == txn and e["step"] == "BEGIN")

    def _roll_forward(self, txn, crash_after=None, hook=None):
        e = self._entry(txn)
        target, to = e["target"], e["to"]

        def db():
            if target == "KNOWLEDGE":
                self.db["views"] = to
            self.db["publication"].setdefault(txn, {"release": to, "channel": "RELEASE_ACTIVATION", "target": target})

        def pointer():
            self.pointers[target] = to
            if target == "KNOWLEDGE" and (not self.history or self.history[-1] != to):
                self.history.append(to)

        def exclusions():
            g = self.pointers["KNOWLEDGE"]
            self.applied[g] = self.exclusions["seq"]          # newest accepted state, read now

        def logged():
            if not any(r["txn"] == txn for r in self.log):
                prev = hashlib.sha256(json.dumps(self.log[-1], sort_keys=True).encode()).hexdigest() if self.log else None
                self.log.append({"seq": len(self.log) + 1, "txn": txn, "target": target, "release": to, "action": e["action"],
                                 "previous_record_sha256": prev, "exclusion_seq": self.exclusions["seq"]})

        def open_():
            # an exclusion accepted after EXCLUSIONS_APPLIED is re-applied before exposure
            g = self.pointers["KNOWLEDGE"]
            if self.applied.get(g) != self.exclusions["seq"]:
                self.applied[g] = self.exclusions["seq"]
            for gg in self.installed:
                self.applied[gg] = self.exclusions["seq"]
            if not any(j["txn"] == txn and j["step"] == "OPEN" for j in self.journal):
                self.journal.append({"txn": txn, "step": "OPEN"})
            self.state = "OPEN"

        for name, fn in (("DB_APPLIED", db), ("POINTER_WRITTEN", pointer), ("EXCLUSIONS_APPLIED", exclusions),
                         ("LOGGED", logged), ("OPEN", open_)):
            self._step(txn, name, fn, crash_after, hook)

    # ------------------------------------------------------------------ recovery
    def recover(self):
        """Idempotent. Refuses service until done. A transaction without DECIDED is aborted (nothing user-visible was
        touched); a DECIDED transaction without OPEN is rolled forward. Derived state is then reconciled with the
        journal: views and pointers, exclusions for every generation."""
        self.state = "RECOVERING"
        txns = []
        for j in self.journal:
            if j["step"] == "BEGIN":
                txns.append(j["txn"])
        for txn in txns:
            steps = {j["step"] for j in self.journal if j["txn"] == txn}
            if "DECIDED" not in steps and "ABORTED" not in steps:
                self.journal.append({"txn": txn, "step": "ABORTED"})
            elif "DECIDED" in steps and "OPEN" not in steps:
                self.state = "SWITCHING"
                self._roll_forward(txn)
        # reconcile derived state with the last OPEN transaction per target
        for target in ("KNOWLEDGE", "MODELS"):
            last = [self._entry(t) for t in txns if self._entry(t)["target"] == target
                    and any(j["txn"] == t and j["step"] == "OPEN" for j in self.journal)]
            if last:
                self.pointers[target] = last[-1]["to"]
        self.db["views"] = self.pointers["KNOWLEDGE"]
        for t in txns:   # publication rows of every committed transaction (a restored database may lack them)
            if any(j["txn"] == t and j["step"] == "OPEN" for j in self.journal):
                e = self._entry(t)
                self.db["publication"].setdefault(t, {"release": e["to"], "channel": "RELEASE_ACTIVATION", "target": e["target"]})
        for g in self.installed:
            self.applied[g] = self.exclusions["seq"]
        self.state = "OPEN"

    # ------------------------------------------------------------------ retention, backup, restore
    def protected(self) -> set[str]:
        active = self.pointers["KNOWLEDGE"]
        prev = [g for g in reversed(self.history[:-1]) if g != active][: self.keep_previous]
        inflight = {e["to"] for e in self.journal if e["step"] == "BEGIN"
                    and not any(j["txn"] == e["txn"] and j["step"] in ("OPEN", "ABORTED") for j in self.journal)}
        pinned = {g for g, n in self.pins.items() if n > 0}
        return {active, *prev, *inflight, *pinned}

    def prune(self) -> list[str]:
        keep = self.protected()
        removed = [g for g in self.installed if g not in keep]
        if len(self.installed) - len(removed) < 1:
            return []                              # never remove the sole recovery copy
        self.installed = [g for g in self.installed if g in keep]
        return removed

    def backup(self) -> dict:
        """Backups hold the site database only. Journal, activation log and ExclusionStore are separate append-only
        stores copied to offline media, never overwritten by a restore."""
        return copy.deepcopy({"db": self.db})

    def restore(self, backup: dict):
        self.state = "RECOVERING"
        self.db = copy.deepcopy(backup["db"])
        self.recover()                             # pointers and views from the journal; latest exclusions re-applied
