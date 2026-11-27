# Freeze addendum for V4 (post-freeze, documentation only; `outputs/FREEZE_V4.json` is not edited)

Written after the GA4 blind evaluation and the pre-integration review (findings A2-03, A2-05). The frozen extractor tools,
their hashes (`FREEZE_V4.json`) and all outputs and predictions are unchanged.

| Item | Value |
| --- | --- |
| Freeze commit | `9cdd5008` (`c13-extract-v4/1.0.0`, tool fingerprint `37642e7b…`) |
| Holdout registration ancestry | `git merge-base --is-ancestor f1d61f71 9cdd5008` passes (also verified independently by GA4) |
| Scored predictions file | `predictions_H-OUT-C13/PREDICTIONS_OUTCOME_V4_H-OUT-C13.csv`, sha256 `45c5a3321d22e2948e2783c2ba6a6857d51f1c705e7b90993ddc3a68ad239b69`, 300 items, 480 rows |
| Prediction converter (post-freeze addition, A2-03) | `tools/predict_holdout_v4.py`; `--check` rebuilds the file above from `raw/OUTCOMES_V4.csv` and `ITEM_POINTERS.csv` byte for byte. It performs no extraction and is not one of the frozen tool files. sha256 `f40d030901577373b69e1d2fa96259844cb5a71f688d8774a683c544df177886`. |
| `exclusion_list_sha256` in FREEZE_V4.json | `d1169093…` is `extract_v4.exclusion_key()`: the sha256 of the 331 sorted ids joined by newlines. The file `EXCLUDE_IDS_H-OUT-C13.txt` itself (with its comment header) has sha256 `87227665…`. |
| Blind result | NOT_MET on all four targets (RESULTS_C13.md section 1.2, `claude/c13-eval` `20a4e55d`) |
