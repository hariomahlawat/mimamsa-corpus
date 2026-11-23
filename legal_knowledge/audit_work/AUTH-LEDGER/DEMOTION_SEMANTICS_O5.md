# O-5: when should a withdrawal or demotion take effect? (analysis and recommendation; no change implemented)

**Current behaviour (rule 1, AUTH-LEDGER-02).** Every ledger version is staged until its BIND line verifies. This covers ADD, CORRECTION and WITHDRAW alike. A WITHDRAW for cause, for example after an authentication record proves false, therefore leaves the earlier PROVENANCE_DOCUMENTED row effective until a second PR adds the BIND line.

**The risk.** Between discovery and binding, the effective register keeps evidence the project knows to be invalid, and any crosswalk anchor resting on it stays EXACT_ANCHOR. Staging protects against unreviewed *promotion*. Applied to *demotion*, it protects nothing, because a demotion is never less safe than the status quo.

**Constraints:**
- An unreviewed actor must not be able to use "emergency demotion" to suppress legitimate evidence silently. Suppression is a harm too: it removes anchors.
- Every effective state must stay reproducible from the manifest and git history.
- Rule 1 history must not change: past `--as-of N` outputs are pinned.

## Options
| Option | Effect | Assessment |
| --- | --- | --- |
| O5-A Keep staging for everything (current) | known-invalid evidence stays effective until bound | simplest; worst for false-positive exposure |
| O5-B Apply WITHDRAW and demoting CORRECTION immediately at recording; keep staging for ADD and promoting CORRECTION | removes known-invalid evidence at once; promotion still needs binding | **recommended**, with the safeguards below |
| O5-C A non-ledger "quarantine" flag the reader honours | fast, but outside the hash chain | rejected: not auditable as a ledger event |

## Recommended procedure (O5-B), if the owner approves it as a new activation-policy version
1. **Versioned semantics.** Add a manifest field `activation_policy: 2`, present from the first line that uses it. Lines without it keep policy 1, the current behaviour. The reader applies policy 2 only from that line onward, so earlier `--as-of` outputs are unchanged.
2. **Which entries qualify.**
   - WITHDRAW with `withdrawal_reason` in {`EVIDENCE_REVOKED`, `CONTRADICTION`, `CLASSIFICATION_ERROR`}.
   - CORRECTION whose resulting state is AUTHENTICATION_PENDING.

   Anything that adds or raises a status stays staged.
3. **Records still required.** A decision record and an independent review record, pinned as now, plus `demotion_basis:` naming the evidence that shows the earlier authentication false. A demotion without a review record stays staged.
4. **Binding still follows.** The BIND line is still added after the merge, and the transition log marks the demotion `APPLIED_PENDING_BINDING` until then. If the BIND line never verifies, the demotion is not undone: the row stays demoted, and the failure is reported for review. Failing safe means keeping the lower status.
5. **Tests required before activation:**
   - policy 1 history is unchanged;
   - an immediate demotion takes effect at `--as-of N`;
   - a promotion in the same version stays staged;
   - a demotion without a review record stays staged;
   - a demotion whose BIND line later fails stays demoted and is reported;
   - a demotion cannot carry an ADD in the same entry;
   - crosswalk anchors drop when the supporting copy is demoted.

**Owner decision O-5.** Adopt O5-B as activation policy 2 (recommended), or keep O5-A. No code implementing policy 2 is written in Cycle 8.
