# Dry run — 2026-11-22T14:02:28+00:00

2 source(s), 2 target(s) (2 still need URL discovery), 14 request(s) would be made from known URLs, 0 refused.

**Config warnings:**

- sources.indiacode has the robots-5xx exception (crawls if robots.txt answers 5xx)
- sources.indiacode has the robots-unreachable exception (crawls if robots.txt cannot be fetched)
- regs-army-1987 is targeted by both indiacode and mod (first hit wins)

## archive (phase 6, disabled)

Hosts: *.archive.org, archive.org  
State: 12 queued (12 due now, 0 in backoff), 0 fetched, 0 failed, 0 skipped  
Would fetch now: 12

Discovery: Digital Library of India items; record the archive.org item identifier in metadata.

- ⚠ marked verify: true; confirm URLs on the live site

| Kind | doc_id / name | URL | State | Action | Notes |
| --- | --- | --- | --- | --- | --- |
| target | act-indian-army-1911 |  | — | discover: resolve URL from listing/search (needs source module) | status_hint: superseded |
| target | book-manual-military-law |  | — | discover: resolve URL from listing/search (needs source module) | status_hint: superseded |
| queued | notif-army-rules-1954-sro-484 | https://archive.org/download/in.gazette.central.w.1954-11-27.103686/103686.pdf | queued | fetch document | category: rules; parent_doc_id: notif-army-rules-1954-sro-484 |
| queued | notif-army-rules-amdt-sro-116-1965 | https://archive.org/download/in.gazette.central.w.1965-04-10.81813/81813.pdf | queued | fetch document | category: notification; parent_doc_id: notif-army-rules-amdt-sro-116-1965 |
| queued | notif-army-rules-amdt-sro-215-1965 | https://archive.org/download/in.gazette.central.w.1965-07-03.79361/79361.pdf | queued | fetch document | category: notification; parent_doc_id: notif-army-rules-amdt-sro-215-1965 |
| queued | notif-army-rules-amdt-sro-188-1979 | https://archive.org/download/in.gazette.central.w.1979-07-28.46533/46533.pdf | queued | fetch document | category: notification; parent_doc_id: notif-army-rules-amdt-sro-188-1979 |
| queued | notif-army-rules-amdt-sro-216-1988 | https://archive.org/download/in.gazette.central.w.1988-09-17.28081/28081.pdf | queued | fetch document | category: notification; parent_doc_id: notif-army-rules-amdt-sro-216-1988 |
| queued | notif-army-rules-amdt-sro-17e-1993 | https://archive.org/download/in.gazette.central.e.1993-12-06.16490/16490.pdf | queued | fetch document | category: notification; parent_doc_id: notif-army-rules-amdt-sro-17e-1993 |
| queued | notif-army-rules-amdt-sro-8e-2003 | https://archive.org/download/in.gazette.central.e.2003-06-24.153/153.pdf | queued | fetch document | category: notification; parent_doc_id: notif-army-rules-amdt-sro-8e-2003 |
| queued | notif-army-rules-amdt-sro-17e-2019 | https://archive.org/download/in.gazette.central.e.2019-12-28.214956/214956.pdf | queued | fetch document | category: notification; parent_doc_id: notif-army-rules-amdt-sro-17e-2019 |
| queued | notif-army-rules-amdt-sro-6e-2022 | https://archive.org/download/in.gazette.central.e.2022-06-06.236353/236353.pdf | queued | fetch document | category: notification; parent_doc_id: notif-army-rules-amdt-sro-6e-2022 |
| queued | rules-adjustment-jurisdiction-1978-so-488 | https://archive.org/download/in.gazette.central.w.1978-02-25.48290/48290.pdf | queued | fetch document | category: rules; parent_doc_id: rules-adjustment-jurisdiction-1978-so-488 |
| queued | notif-adjustment-jurisdiction-amdt-so-4010-1986 | https://archive.org/download/in.gazette.central.w.1986-12-06.32435/32435.pdf | queued | fetch document | category: notification; parent_doc_id: notif-adjustment-jurisdiction-amdt-so-4010-1986 |
| queued | act-commanders-in-chief-change-designation-1955 | https://archive.org/download/in.gazette.e.1955.613/E-2210-1955-0031-101567.pdf | queued | fetch document | category: act; parent_doc_id: act-commanders-in-chief-change-designation-1955 |

## official_instruments (phase 2, disabled)

Hosts: indiacode.gov.in  
State: 2 queued (2 due now, 0 in backoff), 0 fetched, 0 failed, 0 skipped  
Would fetch now: 2

| Kind | doc_id / name | URL | State | Action | Notes |
| --- | --- | --- | --- | --- | --- |
| queued | act-air-force-army-laws-amendment-1975 | https://indiacode.gov.in/server/api/core/bitstreams/d4cb2142-ec1d-46ca-88b1-6ae2b9c603d7/content | queued | fetch document | category: act; parent_doc_id: act-air-force-army-laws-amendment-1975 |
| queued | act-army-amendment-1992 | https://indiacode.gov.in/server/api/core/bitstreams/7a05a1f5-506a-4e9c-afae-c2e4fc1e989e/content | queued | fetch document | category: act; parent_doc_id: act-army-amendment-1992 |

