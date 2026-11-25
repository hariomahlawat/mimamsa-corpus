# V4 full-corpus run compared with frozen V3 (output counts only, not correctness)

Judgments excluded from the V4 development run (H-OUT-C13 and copies): 325, dropped from both columns.

| Measure | V3 | V4 |
| --- | --- | --- |
| rows | 13004 | 13002 |
| judgments | 3611 | 3611 |
| printed_disposal row_answered | 9212 | 9322 |
| printed_disposal judgment_any_answered | 3103 | 3180 |
| substantive_result row_answered | 6824 | 6971 |
| substantive_result judgment_any_answered | 2573 | 2686 |
| abstain ONLY_QUOTED_DISPOSITION_LANGUAGE_FOUND | 51 | 45 |
| abstain NO_OPERATIVE_CUE_IN_FINAL_PART | 107 | 61 |
| abstain EXTENT_QUALIFIED_ALLOWANCE_ALLOWED_OR_PARTLY_ALLOWED_UNDETERMINED | 1 | 0 |

Judgment-level printed coverage by court:

| Court | V3 | V4 |
| --- | --- | --- |
| (none) | 0/4 | 0/4 |
| Allahabad High Court | 233/264 | 233/264 |
| High Court of Delhi | 1383/1564 | 1408/1564 |
| High Court of Jammu and Kashmir | 297/360 | 326/360 |
| High Court of Punjab and Haryana | 978/1137 | 990/1137 |
| Supreme Court of India | 212/282 | 223/282 |

V4 printed labels: {"dismissed": 4015, "OUTCOME_UNVERIFIED": 3680, "disposed_of_with_directions": 2887, "partly_allowed": 768, "allowed": 711, "disposed_of": 388, "transferred": 320, "dismissed_as_withdrawn": 157, "not_final": 48, "set_aside_and_remanded": 12, "dismissed_in_default": 7, "remanded": 6, "dismissed_as_infructuous": 3}

V3 printed labels: {"dismissed": 3988, "OUTCOME_UNVERIFIED": 3792, "disposed_of_with_directions": 3053, "partly_allowed": 772, "allowed": 695, "disposed_of": 258, "transferred": 213, "dismissed_as_withdrawn": 156, "not_final": 49, "set_aside_and_remanded": 12, "dismissed_in_default": 7, "remanded": 6, "dismissed_as_infructuous": 3}

V4 confidence tiers (answered rows): {"high": 2570, "low": 494, "medium": 6313}

V4 notes: {"TRANSFER_DIRECTION_IN_OPERATIVE_PART": 73, "EXTENT_LIMITING_WORDS_READ_AS_PARTLY_ALLOWED": 9, "EXTENT_PHRASE_WITH_LIMITATION_IN_OPERATIVE_PART": 9, "EXTENT_PHRASE_REFERS_TO_DIRECTIONS_QUASHING_IMPUGNED_DECISIONS_NONE_REFUSED": 2, "ALLOWED_IN_TERMS_OF_FRESH_DECISION_DIRECTION": 1}
