"""B06 conformance scenarios (contract 2.1 interface): one language-neutral scenario format run by the reference
model here (driving activation.Site) and by the .NET activation implementation; both must produce the same
observable trace (ACTIVATION_SCENARIO_OUTCOMES_SCHEMA).

The harness adds to activation.Site the parts of the site protocol the reference state machine abstracts:
- single-writer lock with an epoch; a dead or heartbeat-stale holder is taken over (epoch + 1) and the new writer
  must recover before any transition; a stale writer's transition is refused;
- the web service as a PARTICIPANT on the local control channel: a transition starts only when the participant
  acknowledges SWITCHING; a participant lost after DECIDED does not undo the decision, but nothing is served until
  it is back and has loaded the journal head;
- the torn-tail journal reader (an unterminated last record is absent) and corruption elsewhere (fail closed);
- I-6, the read-only signature-verified exclusion reader: monotone sequence; missing store, bad signature or a
  regressed sequence fail closed (no pin, no response, no transition).
"""
from __future__ import annotations

import copy

from . import activation, canonical


class Harness:
    def __init__(self, initial: dict):
        sm = {m: {"verified": v["verified"], "vectors_for": set(v["vectors_for"])} for m, v in initial["staged_models"].items()}
        self.site = activation.Site(installed=list(initial["installed"]), active=initial["active"], models=initial["models"],
                                    keep_previous=initial["keep_previous"], staged_models=sm, sizes=dict(initial["sizes"]),
                                    free_bytes=initial["free_bytes"], recovery_target=initial["recovery_target"])
        self.stale_after = initial["lock_stale_after_seconds"]
        self.clock = 0
        self.lock = None
        self.epoch = 0
        self.participant_up = True
        self.participant_gen = initial["active"]
        self.store = {"present": True, "signature_ok": True}
        self.store_seq_override = None
        self.max_seen = 0
        self.journal_corrupt = False
        self.pins: list[dict] = []
        self.backups: dict[str, dict] = {}
        self.last_response = None

    # ---------------------------------------------------------------- helpers
    def store_seq(self):
        if not self.store["present"]:
            return None
        return self.site.exclusions["seq"] if self.store_seq_override is None else self.store_seq_override

    def reader_state(self) -> str:
        if not self.store["present"]:
            return "MISSING"
        if not self.store["signature_ok"]:
            return "BAD_SIGNATURE"
        if self.store_seq() < self.max_seen:
            return "REGRESSED"
        self.max_seen = self.store_seq()
        return "HEALTHY"

    def state(self) -> str:
        return "FAILED_CLOSED" if self.journal_corrupt else self.site.state

    def serving(self) -> bool:
        return (self.state() == "OPEN" and self.reader_state() == "HEALTHY" and self.participant_up
                and self.participant_gen == self.site.pointers["KNOWLEDGE"])

    def _holder_valid(self, writer):
        return (self.lock is not None and self.lock["writer"] == writer and self.lock["alive"]
                and self.clock - self.lock["heartbeat"] < self.stale_after)

    # ---------------------------------------------------------------- operations
    def op(self, name: str, a: dict):
        getattr(self, "op_" + name)(a)

    def op_lock_acquire(self, a):
        if self.lock and self.lock["writer"] != a["writer"] and self.lock["alive"] and self.clock - self.lock["heartbeat"] < self.stale_after:
            raise activation.Refused("LOCK_CONTENDED")
        takeover = self.lock is not None and self.lock["writer"] != a["writer"]
        self.epoch += 1
        self.lock = {"writer": a["writer"], "alive": True, "heartbeat": self.clock, "epoch": self.epoch}
        if takeover or self.site.state != "OPEN":
            self.site.state = "RECOVERING"          # a new writer must recover before any transition

    def op_lock_release(self, a):
        if self.lock and self.lock["writer"] == a["writer"]:
            self.lock = None

    def op_process_die(self, a):
        if self.lock and self.lock["writer"] == a["writer"]:
            self.lock["alive"] = False

    def op_clock_advance(self, a):
        self.clock += a["seconds"]

    def op_participant_lose(self, a):
        self.participant_up = False

    def op_participant_restore(self, a):
        self.participant_up = True
        if self.state() == "OPEN":
            self.participant_gen = self.site.pointers["KNOWLEDGE"]   # reloads the journal head before serving

    def op_transition(self, a):
        if not self._holder_valid(a["writer"]):
            raise activation.Refused("NOT_LOCK_HOLDER")
        if self.journal_corrupt:
            raise activation.Refused("JOURNAL_CORRUPT")
        if self.reader_state() != "HEALTHY":
            raise activation.Refused("EXCLUSIONS_UNAVAILABLE")
        if not self.participant_up:
            raise activation.Refused("PARTICIPANT_UNAVAILABLE")      # cannot quiesce: nothing journaled
        self.lock["heartbeat"] = self.clock

        def hook(step):
            if a.get("exclusion_at_step") == step:
                self.site.accept_exclusion(set(a["exclusion_items"]))
            if a.get("participant_lost_at") == step:
                self.participant_up = False
        try:
            self.site.transition(a["target"], a["to"], action=a.get("action", "ACTIVATE"), crash_after=a.get("crash_after"), hook=hook)
        finally:
            if self.site.state == "OPEN" and self.participant_up:
                self.participant_gen = self.site.pointers["KNOWLEDGE"]

    def op_recover(self, a):
        if not self._holder_valid(a["writer"]):
            raise activation.Refused("NOT_LOCK_HOLDER")
        if self.journal_corrupt:
            raise activation.Refused("JOURNAL_CORRUPT")
        self.site.recover()
        if self.participant_up:
            self.participant_gen = self.site.pointers["KNOWLEDGE"]

    def op_pin(self, a):
        if not self.serving():
            raise activation.Refused("NOT_SERVING")
        self.pins.append(self.site.pin())

    def op_unpin(self, a):
        p = self.pins.pop(a.get("index", 0))
        self.site.unpin(p)

    def op_respond(self, a):
        if self.reader_state() != "HEALTHY":
            raise activation.Refused("EXCLUSIONS_UNAVAILABLE")
        self.last_response = self.site.respond(self.pins[a.get("index", 0)], list(a["items"]))

    def op_accept_exclusion(self, a):
        if not self.store["present"] or not self.store["signature_ok"]:
            raise activation.Refused("EXCLUSIONS_UNAVAILABLE")
        self.site.accept_exclusion(set(a["items"]))

    def op_prune(self, a):
        self.site.prune()

    def op_backup(self, a):
        self.backups[a["name"]] = self.site.backup()

    def op_restore(self, a):
        if not self._holder_valid(a["writer"]):
            raise activation.Refused("NOT_LOCK_HOLDER")
        self.site.restore(self.backups[a["name"]])
        if self.participant_up:
            self.participant_gen = self.site.pointers["KNOWLEDGE"]

    def op_tear_journal_tail(self, a):
        if self.site.journal:
            self.site.journal.pop()                 # the unterminated last record is absent to the reader
        self.site.state = "RECOVERING"

    def op_corrupt_journal_middle(self, a):
        self.journal_corrupt = True
        self.site.state = "RECOVERING"

    def op_exclusion_store_remove(self, a):
        self.store["present"] = False

    def op_exclusion_store_restore(self, a):
        self.store.update(present=True, signature_ok=True)
        self.store_seq_override = None

    def op_exclusion_store_regress(self, a):
        self.store_seq_override = max(0, self.site.exclusions["seq"] - 1)

    def op_exclusion_signature_invalidate(self, a):
        self.store["signature_ok"] = False

    # ---------------------------------------------------------------- observable
    def observe(self, step: int, error) -> dict:
        s = self.site
        rs = self.reader_state()
        return {"step": step, "error": error, "knowledge": s.pointers["KNOWLEDGE"], "models": s.pointers["MODELS"],
                "views": s.db["views"], "state": self.state(), "serving": self.serving(),
                "journal_steps": [j["step"] for j in s.journal], "publication_rows": len(s.db["publication"]),
                "log_length": len(s.log), "active_exclusion_seq": s.applied.get(s.pointers["KNOWLEDGE"]),
                "store_seq": self.store_seq(), "installed": sorted(s.installed), "pins": len(self.pins),
                "temp_empty": not s.temp, "exclusion_reader": rs, "lock_epoch": self.epoch,
                "response": self.last_response}


def run_scenario(scn: dict) -> dict:
    h = Harness(scn["initial"])
    trace = [h.observe(0, None)]
    for i, st in enumerate(scn["steps"], 1):
        err = None
        try:
            h.op(st["op"], st["args"])
        except activation.Refused:
            err = "Refused"
        except activation.Crash:
            err = "Crash"
        if err != st["expect_error"]:
            raise AssertionError(f"{scn['scenario_id']} step {i} ({st['op']}): expected {st['expect_error']}, got {err}")
        trace.append(h.observe(i, err))
    return {"contract": "mimamsa-corpus-contract/2.1", "record_kind": "activation_scenario_outcomes",
            "scenario_id": scn["scenario_id"], "scenario_sha256": canonical.record_sha256(scn), "trace": trace}


def final_assertion_failures(scn: dict, outcomes: dict) -> list[str]:
    last = outcomes["trace"][-1]
    want = scn["assert_final"]
    names = {"knowledge": "knowledge", "models": "models", "serving": "serving", "installed": "installed",
             "log_length": "log_length", "last_response": "response", "temp_empty": "temp_empty"}
    return [f"{k}: expected {v}, got {last[names[k]]}" for k, v in want.items()
            if (sorted(v) if k == "installed" else v) != last[names[k]]]


def copy_scenario(s: dict) -> dict:
    return copy.deepcopy(s)
