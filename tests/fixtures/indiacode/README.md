# SYNTHETIC pages — not captured from indiacode.nic.in

Everything in this folder was written by hand, from memory of how India Code pages are
laid out, because the live site could not be reached when the crawler was built.

- The handle numbers (`/handle/123456789/9999x`), file names, Act ID, dates in the
  subordinate-legislation rows and robots.txt rules are INVENTED for testing.
- The `.pdf` files are tiny placeholders, not the real documents.
- Nothing here may be copied into `data/` or used as a fact about the law.

To replace these with real pages: run
`python -m crawler discover --source indiacode --only act-army-1950 --record <dir>`
on a machine that can reach the site, or save the pages from a browser and list them in
an `index.json` (URL -> file). Then point `--replay` at that folder.
