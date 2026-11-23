# D4. Coverage impact assessment

Method: the Cycle 5 builder (`SOURCE-LIBRARY-C5/tools/build_registers.py`) is re-run with the D2 proposals added to the Cycle 4 register **in memory only**. The classification rules are unchanged. A test proves the committed Cycle 5 registers are unaffected.

| Measure | Previous (Cycle 5, as merged) | Proposed (if D2 were incorporated) |
| --- | --- | --- |
| Documented-primary copies | 12 | 44 |
| Sources with a documented-primary copy | 12 | 42 |
| Authentication-pending copies | 1 | 1 |
| KB citation items: exact / partial / missing | 42 / 652 / 366 | 42 / 652 / 366 |
| KB records: all / some / no exact | 10 / 30 / 618 | 10 / 30 / 618 |
| Cases (53): exact / partial / missing | 6 / 7 / 40 | 13 / 0 / 40 |

**Why the KB figures do not move:**
- The KB crosswalk cites the Army Act, Army Rules, AFT Act, BNSS and BSA by provision. Their held copies are the 1954 Gazette (already primary) and government compilations, which are not in scope.
- The amendment Gazettes and judgments in scope are not cited with provision locators in the WS-D items.
- The KB cannot gain exact anchors until Gazette texts of the Acts are acquired (C6-02), or until the KB citation locators are linked to the amendment instruments. The second is a separate, reviewed WS-D change.

**The case gain (6 → 13)** comes entirely from the seven SC case records listed in D1.

Nothing here is incorporated, and nothing changes legal status.
