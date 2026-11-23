# Cycle 5 discovery brief (shared by discovery agents)

Project: Mimamsa, an offline Indian military-law knowledge base. Goal: find WHERE authoritative copies of specified publications exist, and their identity. DISCOVERY ONLY.

## Hard rules
- DO NOT download any document binary (PDF/DOC/ZIP/image). For a binary URL use only an HTTP HEAD request: `curl -sSI -L --max-time 40 -A "$UA" URL`. Never use WebFetch/curl GET on a .pdf/.doc/.zip URL.
- GET is allowed only for HTML listing/search pages, robots.txt, and JSON/XML metadata APIs (e.g. https://archive.org/advancedsearch.php, https://archive.org/metadata/<id>, India Code search pages).
- UA: `Mimamsa-legal-research-discovery/1.0 (non-commercial research; read-only)` . Do not put any email or personal name in requests.
- Before the first request to a host, GET its /robots.txt and obey it. At most one request every 2 seconds per host (sleep 2 between calls).
- NEVER contact aftjabalpur.in or any AFT bare-IP HTTP address. Do not bypass CAPTCHA, logins or paywalls; never disable TLS verification (no -k). If a site needs CAPTCHA/login, record BLOCKED_ACCESS and stop on that site.
- Do not use commercial legal databases (Indian Kanoon, SCC Online, Manupatra, Casemine) as evidence. Scribd/slideshare copies may be recorded only as THIRD_PARTY_TRANSCRIPTION/UNKNOWN candidates, never as authoritative.
- Log EVERY network request (including robots.txt and HEAD) as a TSV line to your log file: `utc_time<TAB>method<TAB>url<TAB>http_status<TAB>bytes_or_content_length<TAB>purpose`.
- Never invent page numbers, dates, editions or text. Quote identity evidence verbatim from the listing page/metadata/HEAD. If not found, say NOT_FOUND with what you searched; if you did not check, NOT_CHECKED.
- Do not edit anything in any git repository. Write only your two output files.

## Output CSV (UTF-8, header exactly):
candidate_id,publication,edition_or_version,issuing_authority,publication_type,url_or_identifier,host,carrier_class,check_method,http_status,content_type,content_length,last_modified,identity_evidence,discovery_state,access_restriction,notes,checked_at_utc

- publication_type: STATUTE | SUBORDINATE_LEGISLATION | REGULATION | ADMINISTRATIVE_INSTRUCTION | MANUAL | GAZETTE_NOTIFICATION | JUDICIAL | SECONDARY_COMMENTARY | CATALOGUE_RECORD
- carrier_class: ISSUING_AUTHORITY | GOVERNMENT_HOSTED_COPY | THIRD_PARTY_ARCHIVAL_FACSIMILE | THIRD_PARTY_TRANSCRIPTION | SECONDARY | LIBRARY_CATALOGUE | UNKNOWN
- check_method: SEARCH_RESULT_ONLY | LISTING_PAGE_FETCHED | HEAD_ONLY | METADATA_API
- discovery_state: FOUND_CANDIDATE | NOT_FOUND | NOT_CHECKED | BLOCKED_ACCESS | RESTRICTED_MARKING_SUSPECTED
- One row per (publication edition x location). Also add NOT_FOUND rows for important targets you searched without success, naming where you searched in notes.

Return to the coordinator: a short summary (<=300 words) of key findings, blockers and the paths of your two files.
