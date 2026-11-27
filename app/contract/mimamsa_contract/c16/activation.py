"""Reference model of crash-consistent activation, rollback and restore (architecture section 8).

An executable specification, not site code: the B1 importer and service must implement the same states and
invariants, and these tests are the acceptance oracle for the STATE MACHINE. The production concurrency and
durability proof (real fsync, PostgreSQL transactions, process crashes, concurrent requests) remains a later
implementation gate (FG-JOURNAL-DURABILITY): this model proves the protocol, not the implementation.

Commit domains and the single commit decision
- journal      append-only activation journal: BEGIN, DECIDED, OPEN or ABORTED per transaction. DECIDED is the ONE
               authoritative commit decision.
- db           knowledge views and RELEASE_ACTIVATION publication rows (keyed by txn: idempotent).
- pointers     ACTIVE / MODELS_ACTIVE (derived from the journal; rewritten by reconciliation).
- exclusions   ExclusionStore (append-only, monotone; never restored from backup).
- log          activation log (hash chain), one record per DECIDED transaction (keyed by txn: idempotent).
- temp         per-transaction scratch (staging views, temporary pointer files); removed on every path.
Readers pin (knowledge generation, model generation, exclusion sequence) per request; while a transition or
recovery is in progress new pins are refused; at the response boundary every response is filtered by the CURRENT
exclusion state, so an exclusion accepted after the pin is never bypassed. Retention keeps the active release plus
two previous DISTINCT verified releases (owner decision 4) and never removes an active, pinned, in-flight, explicit
recovery-target or sole verified generation (decision 6). A measured disk preflight (decision 5) gates every
activation.
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
    def __init__(self, installed: list[str], active: str, models: str = "M1", keep_previous: int = 2,
                 staged_models: dict | None = None, sizes: dict | None = None, free_bytes: int = 10**12,
                 headroom_fraction: float = 0.1, recovery_target: str | None = None):
        self.installed = list(installed)          # verified, staged knowledge generations on disk
        self.staged_models = {models: {"verified": True, "vectors_for": set(installed)}, **(staged_models or {})}
        self.journal: list[dict] = []
        self.db = {"views": active, "publication": {}, "site_rows": {"users": 1}}
        self.pointers = {"KNOWLEDGE": active, "MODELS": models}
        self.exclusions = {"seq": 0, "suppressed": frozenset()}
        self.applied = {active: 0}
        self.log: list[dict] = []
        self.pins: Counter = Counter()
        self.temp: set[str] = set()
        self.state = "OPEN"
        self.keep_previous = keep_previous
        self.history = [active]
        self.sizes = sizes or {}                   # measured bytes per generation (staged and retained)
        self.free_bytes = free_bytes
        self.headroom_fraction = headroom_fraction  # configurable (decision 5)
        self.recovery_target = recovery_target      # explicit verified recovery generation (protected)
        self._txn = 0

    # ------------------------------------------------------------------ readers
    def pin(self) -> dict:
        if self.state != "OPEN":
            raise Refused("transition or recovery in progress")
        g = self.pointers["KNOWLEDGE"]
        if self.applied.get(g, -1) != self.exclusions["seq"]:
            raise Refused("exclusions not applied to the active generation")
        p = {"knowledge": g, "models": self.pointers["MODELS"], "exclusion_seq": self.exclusions["seq"]}
        self.pins[g] += 1
        return p

    def respond(self, pin: dict, items: list[str]) -> list[str]:
        """Response boundary: filter by the CURRENT exclusion state (never only the state seen at pin time)."""
        return [i for i in items if i not in self.exclusions["suppressed"]]

    def unpin(self, pin: dict):
        self.pins[pin["knowledge"]] -= 1

    # ------------------------------------------------------------------ exclusions
    def accept_exclusion(self, items: set[str]):
        self.exclusions = {"seq": self.exclusions["seq"] + 1, "suppressed": self.exclusions["suppressed"] | frozenset(items)}
        if self.state == "OPEN":
            for g in self.installed:
                self.applied[g] = self.exclusions["seq"]

    # ------------------------------------------------------------------ preflight
    def preflight(self, target: str, to: str) -> dict:
        """Measured disk preflight (decision 5): the measured bytes the activation still has to materialise for the
        target (sizes[to]: views, indexes, stores and vault additions measured at staging) plus the configured
        headroom must fit in the measured free space, while every retained release stays on disk. Never a fixed
        allocation; refused when it fails."""
        keep = sorted(self.protected() | ({to} if target == "KNOWLEDGE" else set()))
        need = int(self.sizes.get(to, 0) * (1 + self.headroom_fraction))
        ok = self.free_bytes >= need
        return {"measured_required_bytes": need, "free_bytes": self.free_bytes, "headroom_fraction": self.headroom_fraction,
                "retained_releases": keep, "result": "PASS" if ok else "FAIL"}

    # ------------------------------------------------------------------ transitions
    def transition(self, target: str, to: str, action: str = "ACTIVATE", crash_after: str | None = None, hook=None):
        if self.state != "OPEN":
            raise Refused("another transition or recovery is in progress")
        if target == "KNOWLEDGE" and to not in self.installed:
            raise Refused("target generation is not staged and verified")
        if target == "MODELS":
            m = self.staged_models.get(to)
            if not m or not m.get("verified"):
                raise Refused("target model is not staged and verified")
            if self.pointers["KNOWLEDGE"] not in m.get("vectors_for", set()):
                raise Refused("target model has no verified vectors for the active knowledge generation")
        if target == "KNOWLEDGE":
            model = self.staged_models[self.pointers["MODELS"]]
            if to not in model.get("vectors_for", set()):
                raise Refused("active model has no verified vectors for the target generation")
        if self.preflight(target, to)["result"] != "PASS":
            raise Refused("measured disk preflight failed")
        self._txn += 1
        txn = f"TX-{self._txn:08d}-{hashlib.sha256(f'{target}|{to}|{self._txn}'.encode()).hexdigest()[:12]}"
        self.state = "SWITCHING"
        frm = self.pointers[target]

        def begin():
            self.journal.append({"txn": txn, "step": "BEGIN", "target": target, "from": frm, "to": to, "action": action})
            self.temp.add(f"{txn}:staging")
        self._step(txn, "BEGIN", begin, crash_after, hook)
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
            self.temp.add(f"{txn}:pointer.tmp")
            self.pointers[target] = to
            self.temp.discard(f"{txn}:pointer.tmp")
            if target == "KNOWLEDGE" and (not self.history or self.history[-1] != to):
                self.history.append(to)

        def exclusions():
            self.applied[self.pointers["KNOWLEDGE"]] = self.exclusions["seq"]

        def logged():
            if not any(r["txn"] == txn for r in self.log):
                prev = hashlib.sha256(json.dumps(self.log[-1], sort_keys=True).encode()).hexdigest() if self.log else None
                self.log.append({"seq": len(self.log) + 1, "txn": txn, "target": target, "release": to, "action": e["action"],
                                 "previous_record_sha256": prev, "exclusion_seq": self.exclusions["seq"]})

        def open_():
            for g in self.installed:
                self.applied[g] = self.exclusions["seq"]       # newest state, re-read at exposure
            if not any(j["txn"] == txn and j["step"] == "OPEN" for j in self.journal):
                self.journal.append({"txn": txn, "step": "OPEN"})
            self._cleanup(txn)
            self.state = "OPEN"

        for name, fn in (("DB_APPLIED", db), ("POINTER_WRITTEN", pointer), ("EXCLUSIONS_APPLIED", exclusions),
                         ("LOGGED", logged), ("OPEN", open_)):
            self._step(txn, name, fn, crash_after, hook)

    def _cleanup(self, txn):
        self.temp = {t for t in self.temp if not t.startswith(txn + ":")}

    # ------------------------------------------------------------------ recovery
    def recover(self):
        """Idempotent. Refuses service until done. Aborts undecided transactions, rolls decided ones forward,
        reconciles derived state with the journal and removes every transaction's scratch state."""
        self.state = "RECOVERING"
        txns = [j["txn"] for j in self.journal if j["step"] == "BEGIN"]
        for txn in txns:
            steps = {j["step"] for j in self.journal if j["txn"] == txn}
            if "DECIDED" not in steps and "ABORTED" not in steps:
                self.journal.append({"txn": txn, "step": "ABORTED"})
            elif "DECIDED" in steps and "OPEN" not in steps:
                self.state = "SWITCHING"
                self._roll_forward(txn)
            self._cleanup(txn)
        for target in ("KNOWLEDGE", "MODELS"):
            last = [self._entry(t) for t in txns if self._entry(t)["target"] == target
                    and any(j["txn"] == t and j["step"] == "OPEN" for j in self.journal)]
            if last:
                self.pointers[target] = last[-1]["to"]
        self.db["views"] = self.pointers["KNOWLEDGE"]
        for t in txns:
            if any(j["txn"] == t and j["step"] == "OPEN" for j in self.journal):
                e = self._entry(t)
                self.db["publication"].setdefault(t, {"release": e["to"], "channel": "RELEASE_ACTIVATION", "target": e["target"]})
        for g in self.installed:
            self.applied[g] = self.exclusions["seq"]
        self.temp.clear()
        self.state = "OPEN"

    # ------------------------------------------------------------------ retention, backup, restore
    def previous_distinct(self) -> list[str]:
        """Previous DISTINCT verified generations, most recent first (rollback history can repeat ids)."""
        active, out = self.pointers["KNOWLEDGE"], []
        for g in reversed(self.history):
            if g != active and g not in out and g in self.installed:
                out.append(g)
        return out[: self.keep_previous]

    def protected(self) -> set[str]:
        inflight = {e["to"] for e in self.journal if e["step"] == "BEGIN" and e["target"] == "KNOWLEDGE"
                    and not any(j["txn"] == e["txn"] and j["step"] in ("OPEN", "ABORTED") for j in self.journal)}
        pinned = {g for g, n in self.pins.items() if n > 0}
        rt = {self.recovery_target} if self.recovery_target in self.installed else set()
        return {self.pointers["KNOWLEDGE"], *self.previous_distinct(), *inflight, *pinned, *rt}

    def prune(self) -> list[str]:
        if self.state != "OPEN":
            return []
        keep = self.protected()
        removed = [g for g in self.installed if g not in keep]
        if len(self.installed) - len(removed) < 1:
            return []
        self.installed = [g for g in self.installed if g in keep]
        return removed

    def backup(self) -> dict:
        return copy.deepcopy({"db": self.db})

    def restore(self, backup: dict):
        self.state = "RECOVERING"
        self.db = copy.deepcopy(backup["db"])
        self.recover()
