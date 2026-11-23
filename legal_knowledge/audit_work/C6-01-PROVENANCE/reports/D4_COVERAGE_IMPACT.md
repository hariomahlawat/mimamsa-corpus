# D4. Coverage impact assessment

**Method:**
- The Cycle 5 builder is re-run with the D2 proposals added to the Cycle 4 register **in memory only**.
- The simulation switches off the Cycle 5 holding-state consistency check (`check_holding_vs_copies`), because the frozen Cycle 5 master still labels those sources `*_PROVENANCE_UNDOCUMENTED`. Real incorporation would **not** relabel or edit Cycle 5: it would use the overlay design (`addendum/INTEGRATION_ARCHITECTURE.md`, revision 2), where source states are derived in a separate package with the consistency rule on (final review R-02; Fable F-05/F-06).
- 4 non-primary proposals are included in the simulation but have no effect: the Cycle 4 rule has no NON_PRIMARY_* class (R-03).
- The classification rules are unchanged.
- A test proves the committed Cycle 5 registers are unaffected.

| Measure | Previous (Cycle 5, as merged) | Proposed (if D2 were incorporated) |
| --- | --- | --- |
| Documented-primary copies | 12 | 40 |
| Sources with a documented-primary copy | 12 | 40 |
| Authentication-pending copies | 1 | 1 |
| KB citation items: exact / partial / missing | 42 / 652 / 366 | 42 / 652 / 366 |
| KB records: all / some / no exact | 10 / 30 / 618 | 10 / 30 / 618 |
| Cases (53): exact / partial / missing | 6 / 7 / 40 | 13 / 0 / 40 |

**Why the KB figures do not move:**
- KB citations resolve to the Army Act, Army Rules, AFT Act, BNSS and BSA. Their held copies are the 1954 Gazette (already primary) and government compilations, none of which are in scope.
- The amendment Gazettes and judgments in scope carry no provision locators in the WS-D items.

**The case gain** comes entirely from the seven SC case records in D1.

Nothing is incorporated, and nothing changes legal status.
