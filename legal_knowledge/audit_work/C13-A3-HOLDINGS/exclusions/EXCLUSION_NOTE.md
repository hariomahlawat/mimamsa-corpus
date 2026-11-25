# Fresh-set exclusion (H-HOLD-C13)

- Source: branch `claude/c13-a0-eval` at `5e07e010`, `outputs/holdouts/H-HOLD-C13/SAMPLE.csv` (75) and `RESERVE.csv` (38).
  Only the `judgment_key`, `rep_sha256` and `rep_doc_id` columns were read (via `git show`). These files carry no
  `judgment_id` column, so keys were mapped to judgment_ids through A0's `outputs/frame/FRAME_RECORDS.csv`, reading only
  its `judgment_key`, `judgment_id`, `sha256` and `doc_id` columns. 113 keys -> 111 judgment_ids (2 keys have no
  judgment_id in the frame); no further corpus judgment_id shares a copy sha256.
- `EXCLUDE_H_HOLD_C13.txt` is passed as `--exclude-ids` to training and to every extraction run. Excluded ids
  produce no items (`text_status = EXCLUDED`).
- Overlap with the sets C13-A3 trained or developed on (C12 reference 30, C11 GT 56, C12 adjudication sample,
  C12 dev hand-check, opinion gold 15): **none**.
- Prior contact, reported for completeness: before the list was available, two scope-wide automated scans
  (opinion-role counts, and a count of separate-opinion cue words) processed all 280 SC-scope texts, which include
  28 of the 111 fresh judgment_ids. Two fresh ids (J-163622030094768d, J-abc2b50b1f2ee0c4) appeared in the cue-scan
  printout as "id, 1 opinion, cue word 'dissent'". No text of any fresh judgment was read or displayed, and no rule
  was written from them. The 28 also appear (as ordinary rows) in the C12 scope output that C13 replaces.
