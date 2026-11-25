"""Post-freeze integration fix (pre-integration review A5-01b): deterministic restricted-register provenance.

The frozen `common_c13.load_restricted()` (sha256 ec7fe04a…, not edited) labels its source by *where* it read the
register: `worktree:config/restricted_material.json` once staging carries the file, otherwise
`git:72fe7a75:config/restricted_material.json`. The bytes are the same either way, so every summary and manifest that
records the label changed after the merge although nothing else did.

`apply()` replaces `common_c13.load_restricted` in-process with a wrapper that reads the register exactly as before
and, **only when its bytes hash to the pinned register sha256**, reports the established label
`git:72fe7a75:config/restricted_material.json`. The label names the pinned register version; the sha256 proves the
bytes. If the register bytes differ from the pin, the real label and sha are reported unchanged, so every `--check`
fails loudly and the outputs must be rebuilt and reviewed. Identifiers and exclusion behaviour are untouched.
"""
from __future__ import annotations

import common_c13 as C

PINNED_LABEL = "git:%s:%s" % (C.RESTRICTED_CONFIG_COMMIT, C.RESTRICTED_CONFIG_PATH)
PINNED_SHA256 = "fc7ea07e62e7e41f348639973f19187540593e7b3237933758f64e865b95b2b6"
_original = C.load_restricted


def _pinned_load_restricted():
    shas, ids, paths, prov = _original()
    if prov.get("sha256") == PINNED_SHA256:
        prov = dict(source=PINNED_LABEL, sha256=PINNED_SHA256)
    return shas, ids, paths, prov


def apply():
    C.load_restricted = _pinned_load_restricted
    return C
