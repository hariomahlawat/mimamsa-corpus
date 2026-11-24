"""Assembly of the C10 Hugging Face judicial-corpus audit outputs from the persisted extraction batches.

Deterministic: same batches + same pinned inputs -> byte-identical outputs. Every judgment metadata record, every judgment
source file and every excluded-log record receives an explicit disposition; the accounting identity is asserted.
"""
import csv, gzip, hashlib, io, json, re, subprocess
from collections import Counter, defaultdict
from pathlib import Path

import audit_judgments as AJ
import jextract as J

TITLE_SCREEN = re.compile(
    r"\b(?:army|air\s*force|indian\s+navy|naval|ministry\s+of\s+defen[cs]e|defen[cs]e|m\.?o\.?d\.?|"
    r"(?:ex[-\s.]*)?(?:sep|hav|nk|l/nk|sub|nb\s*sub|capt|maj|col|lt|brig|gen|sgt|cpl|jwo|mwo|cdr|cmde|wg\s*cdr|sqn\s*ldr|flt\s*lt|gp\s*capt)\.?\s|"
    r"ex[-\s.]*servicem[ae]n|ex[-\s.]*(?:sep|hav|nk|naik|subedar|sub|capt|maj|col|lt|sgt|cpl)\b|sepoy|havildar|naik|subedar|"
    r"brigadier|colonel|lt\.?\s*col|wing\s+commander|squadron\s+leader|flight\s+lieutenant|commodore|jawan|soldier|military|"
    r"cantonment|assam\s+rifles|border\s+security\s+force|\bbsf\b|\bcrpf\b|\bitbp\b|coast\s+guard|sainik|canteen\s+stores|"
    r"\bmes\b|military\s+engineer|ordnance|armed\s+forces)\b", re.I)


def csv_text(fields, rows):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fields, lineterminator="\n", extrasaction="ignore")
    w.writeheader()
    for r in rows:
        w.writerow({k: ("" if r.get(k) is None else r.get(k)) for k in fields})
    return buf.getvalue()


def jl(rows):
    return "".join(json.dumps(r, sort_keys=True, ensure_ascii=False) + "\n" for r in rows)


def jid(sha):
    return "J-" + sha[:16]


def norm_cit(s):
    return re.sub(r"[\s.\[\]()]", "", (s or "")).upper()


def load_batches(files):
    plan = AJ.batch_plan(files, 200)
    res, status = {}, []
    for i, shas in enumerate(plan):
        bp = AJ.WORK / f"batch_{i:04d}.jsonl"
        key = AJ.batch_key(shas)
        ok = False
        if bp.is_file():
            lines = bp.read_text(encoding="utf-8").splitlines()
            head = json.loads(lines[0])
            if head.get("input_key") == key and head.get("extractor") == J.EXTRACTOR_VERSION:
                ok = True
                for l in lines[1:]:
                    r = json.loads(l)
                    res[r["sha256"]] = r
        status.append(dict(batch=i, files=len(shas), input_key=key, complete=ok,
                           batch_sha256=hashlib.sha256(bp.read_bytes()).hexdigest() if ok else ""))
    return plan, res, status


def build(repo):
    metas, files = AJ.enumerate_all(repo)
    plan, res, bstatus = load_batches(files)
    by_sha_meta = defaultdict(list)
    for m in metas:
        by_sha_meta[m.get("sha256")].append(m)
    cases = [json.loads(l) for l in AJ.git(repo, "cat-file", "blob", f"{AJ.STAGING}:{AJ.CASES}").decode().splitlines() if l.strip()]
    copyreg = {r["sha256"]: r for r in csv.DictReader(io.StringIO(AJ.git(repo, "cat-file", "blob", f"{AJ.STAGING}:{AJ.COPY_REG}").decode()))}
    out, rows = {}, {}

    # ---------------- copy register (one row per distinct judgment file)
    copy_rows = []
    for sha in sorted(files):
        f, r = files[sha], res.get(sha)
        disp = ("PROCESSED" if r and r.get("extraction") == "PROCESSED" else
                "PROCESSED_TRUNCATED_COPY" if r and r.get("extraction") == "PROCESSED_TRUNCATED_COPY" else
                "PROCESSED_UNREADABLE_PDF" if r and r.get("extraction") == "PROCESSED_UNREADABLE_PDF" else
                "INCOMPLETE_COPY_TRUNCATED" if r and r.get("extraction") == "INCOMPLETE_COPY_TRUNCATED" else
                "NOT_PROCESSED_BYTES_UNAVAILABLE" if (r and r.get("integrity") == "NOT_AVAILABLE") or f["byte_source"] == "NOT_AVAILABLE" else
                "NOT_PROCESSED_HASH_MISMATCH" if r and r.get("integrity") == "SHA256_MISMATCH" else "NOT_YET_PROCESSED")
        bver = ("GITHUB_RAW_DATA_REHASHED_EQUALS_HF_DECLARED" if r and r.get("integrity") == "SHA256_MATCH" and f["byte_source"] == "github_raw_data" else
                "WORKING_STORE_REHASHED_EQUALS_HF_SIDECAR" if r and r.get("integrity") == "SHA256_MATCH" else
                "NOT_CHECKED" if disp.startswith("NOT_") else r.get("integrity", "") if r else "")
        copy_rows.append(dict(judgment_id=jid(sha), sha256=sha, bytes=f["bytes"], location=f["location"], path=f["path"],
                              byte_source=f["byte_source"], source_document_verification=bver, hf_bytes="NOT_CHECKED",
                              metadata_records=len(by_sha_meta.get(sha, [])), c5_copy_register=copyreg.get(sha, {}).get("copy_id", ""),
                              pages=(r or {}).get("pages", ""), text_extraction=(r or {}).get("text_extraction", ""),
                              pdf_status=(r or {}).get("pdf_status", ""), disposition=disp))
    rows["copy"] = copy_rows

    # ---------------- per-record metadata audit
    meta_rows = []
    for m in sorted(metas, key=lambda x: x["doc_id"]):
        sha = m.get("sha256")
        r = res.get(sha) or {}
        mc = [x for x in (AJ.J.norm_case_string(c) for c in (m.get("case_numbers") or [])) if x]
        tc = r.get("case_numbers_text_p1_3") or []
        core = lambda k: "-".join(k.split("-")[1:]) if k else ""
        if not mc:
            cstat = "NOT_AVAILABLE_IN_METADATA"
        elif not tc:
            cstat = "NOT_FOUND_IN_TEXT" if r else "NOT_VERIFIED"
        else:
            # a metadata number absent from the candidates is NOT_CONFIRMED_IN_TEXT (extraction is incomplete for long cause
            # lists and unusual formats); it is not reported as a contradiction
            cstat = "MATCH" if any(core(a) == core(b) for a in mc for b in tc) else "NOT_CONFIRMED_IN_TEXT"
        dt = r.get("decision_date_candidates") or []
        other = r.get("dates_text") or []
        idate = m.get("issue_date")
        if not idate:
            dstat = "NOT_AVAILABLE_IN_METADATA"
        elif idate in dt:
            dstat = "MATCH"
        elif dt:
            dstat = "DIFFERS"
        elif idate in other:
            dstat = "MATCH_WEAK_LABEL_ONLY"
        else:
            dstat = "NOT_FOUND_IN_TEXT" if r.get("extraction") == "PROCESSED" else "NOT_VERIFIED"
        nc = m.get("neutral_citation")
        tins = [norm_cit(x) for x in (r.get("citations") or {}).get("neutral_INSC", [])]
        nstat = ("NOT_AVAILABLE_IN_METADATA" if not nc else "MATCH" if norm_cit(nc) in tins else "NOT_FOUND_IN_TEXT" if r else "NOT_VERIFIED")
        missing = [k for k in ("case_numbers", "issue_date", "court", "parties", "judges") if not m.get(k)]
        contra = []
        if dstat == "DIFFERS":
            contra.append("issue_date not among dates printed in the text")
        if cstat == "NOT_CONFIRMED_IN_TEXT":
            contra.append("metadata case number not confirmed among case numbers read from the opening text (not a contradiction)")
        om, ot = (m.get("outcome") or ""), (r.get("outcome_candidate") or "")
        if om and ot and ot != "NOT_FOUND" and om != ot:
            contra.append(f"crawler outcome '{om}' differs from text outcome candidate '{ot}' (the text candidate is the less reliable; review)")
        if len(by_sha_meta.get(sha, [])) > 1:
            contra.append(f"source file shared with {len(by_sha_meta[sha]) - 1} other record(s) (common judgment or duplicate)")
        meta_rows.append(dict(doc_id=m["doc_id"], judgment_id=jid(sha) if sha else "", sha256=sha, court=m.get("court"),
                              bench=m.get("bench"), title=m.get("title"), case_numbers_meta=";".join(m.get("case_numbers") or []),
                              case_numbers_text_p1_3=";".join(tc), case_number_status=cstat, issue_date_meta=idate,
                              decision_date_candidates=";".join(dt), other_dates_in_text=";".join(other), date_status=dstat, neutral_citation_meta=nc, neutral_citation_status=nstat,
                              parties_petitioner=";".join((m.get("parties") or {}).get("petitioner") or []),
                              parties_respondent=";".join((m.get("parties") or {}).get("respondent") or []),
                              judges=";".join(m.get("judges") or []), outcome_meta=m.get("outcome"),
                              outcome_text_candidate=r.get("outcome_candidate", ""), missing_metadata=";".join(missing),
                              contradictions=" | ".join(contra), source_url=m.get("source_url"),
                              audit_disposition="AUDITED_AUTOMATED" if r.get("extraction") == "PROCESSED" else
                              "AUDITED_AUTOMATED_SOURCE_TRUNCATED" if r.get("extraction") == "PROCESSED_TRUNCATED_COPY" else
                              "AUDITED_METADATA_ONLY_PDF_UNREADABLE" if r.get("extraction") == "PROCESSED_UNREADABLE_PDF" else
                              "AUDITED_METADATA_ONLY_SOURCE_TRUNCATED" if r.get("extraction") == "INCOMPLETE_COPY_TRUNCATED" else "NOT_PROCESSED",
                              verification="AUTOMATED_NOT_LEGALLY_VERIFIED"))
    rows["meta"] = meta_rows

    # ---------------- distinct-judgment research records (relevance, issues, holdings)
    rel_rows, issues, holds = [], [], []
    for sha in sorted(files):
        r = res.get(sha)
        ms = by_sha_meta.get(sha, [])
        title = ms[0].get("title") if ms else ""
        if not r or r.get("extraction") not in ("PROCESSED", "PROCESSED_TRUNCATED_COPY"):
            rel_rows.append(dict(judgment_id=jid(sha), sha256=sha, court=ms[0].get("court") if ms else "", title=title,
                                 relevance_class="RELEVANCE_UNCERTAIN_REVIEW",
                                 reason="not processed: " + ((r or {}).get("extraction") or (r or {}).get("pdf_error") or "bytes unavailable"),
                                 direct_terms="", admin_terms="", general_terms="", method="AUTOMATED_RULES"))
            continue
        sc = dict(r.get("relevance_scores") or {})
        # the topic tagger also counts the Tribunal's abbreviation (AFT), which the service-term count misses
        sc["admin"] = sc.get("admin", 0) + (r.get("topics") or {}).get("aft_jurisdiction", 0)
        cls, why = J.classify_relevance(sc, r.get("text_extraction"), title)
        rel_rows.append(dict(judgment_id=jid(sha), sha256=sha, court=ms[0].get("court") if ms else "", title=title,
                             relevance_class=cls, reason=why, direct_terms=sc.get("direct"), admin_terms=sc.get("admin"),
                             general_terms=sc.get("general"), method="AUTOMATED_RULES"))
        issues.append(dict(judgment_id=jid(sha), sha256=sha, doc_ids=sorted(m["doc_id"] for m in ms),
                           statutes=r.get("statutes"), topics=r.get("topics"), citations=r.get("citations"),
                           status="AUTOMATED_CANDIDATE_NOT_VERIFIED"))
        holds.append(dict(judgment_id=jid(sha), sha256=sha, doc_ids=sorted(m["doc_id"] for m in ms),
                          outcome_candidate=r.get("outcome_candidate"), outcome_conflict=r.get("outcome_conflict"),
                          outcome_page=r.get("outcome_page"), outcome_evidence=r.get("outcome_evidence"),
                          propositions=r.get("propositions"), status="AUTOMATED_CANDIDATE_NOT_VERIFIED"))
    rows["rel"] = rel_rows

    # ---------------- duplicates and versions
    dups = []
    for sha, ms in sorted(by_sha_meta.items()):
        if sha and len(ms) > 1:
            dups.append(dict(group_id=f"DUP-FILE-{sha[:12]}", kind="ONE_FILE_MANY_RECORDS", judgment_ids=jid(sha), sha256s=sha,
                             doc_ids=";".join(sorted(m["doc_id"] for m in ms))[:2000], count=len(ms),
                             interpretation="common judgment disposing of connected matters, or duplicate record; review",
                             automated=True))
    by_case = defaultdict(set)
    by_nc = defaultdict(set)
    for m in metas:
        for c in (m.get("case_numbers") or []):
            k = J.norm_case_string(c)
            if k:
                by_case[(m.get("court"), k)].add(m.get("sha256"))
        if m.get("neutral_citation"):
            by_nc[norm_cit(m["neutral_citation"])].add(m.get("sha256"))
    for (court, k), shas in sorted(by_case.items(), key=lambda x: (str(x[0][0]), x[0][1])):
        if len(shas) > 1:
            dups.append(dict(group_id=f"DUP-CASE-{hashlib.sha256((str(court) + k).encode()).hexdigest()[:12]}",
                             kind="SAME_CASE_NUMBER_DIFFERENT_FILES", judgment_ids=";".join(sorted(jid(s) for s in shas if s)),
                             sha256s=";".join(sorted(s for s in shas if s)), doc_ids=f"{court} {k}", count=len(shas),
                             interpretation="possible later order, corrected or alternate copy of the same case; version review",
                             automated=True))
    for k, shas in sorted(by_nc.items()):
        if len(shas) > 1:
            dups.append(dict(group_id=f"DUP-NC-{k}", kind="SAME_NEUTRAL_CITATION_DIFFERENT_FILES",
                             judgment_ids=";".join(sorted(jid(s) for s in shas if s)), sha256s=";".join(sorted(s for s in shas if s)),
                             doc_ids=k, count=len(shas), interpretation="identity review (same citation, different bytes)", automated=True))
    for sha in sorted(files):
        r = res.get(sha) or {}
        if r.get("corrected_marker"):
            dups.append(dict(group_id=f"VER-CORR-{sha[:12]}", kind="CORRECTION_MARKER_ON_FIRST_PAGES", judgment_ids=jid(sha),
                             sha256s=sha, doc_ids=";".join(sorted(m["doc_id"] for m in by_sha_meta.get(sha, []))), count=1,
                             interpretation="a correction, corrigendum or modification word appears on pp.1-2; confirm whether this is a corrected version",
                             automated=True))
    rows["dup"] = dups

    # ---------------- relationships: judgment-to-judgment citations resolved via metadata citations; curated-case matches
    cit_index = defaultdict(set)
    for m in metas:
        for c in [m.get("neutral_citation")] + list(m.get("reported_citations") or []):
            if c:
                cit_index[norm_cit(c)].add(m.get("sha256"))
    rels = []
    for sha in sorted(files):
        r = res.get(sha) or {}
        seen = set()
        for kind, lst in sorted((r.get("citations") or {}).items()):
            for c in lst:
                k = norm_cit(c)
                for t in sorted(cit_index.get(k, set())):
                    if t and t != sha and (t, k) not in seen:
                        seen.add((t, k))
                        rels.append(dict(source_judgment_id=jid(sha), relation="CITES", target=jid(t), citation=c, citation_kind=kind,
                                         method="AUTOMATED_CITATION_MATCH", status="AUTOMATED_NOT_VERIFIED"))
    case_idx = []
    for c in cases:
        cits = [norm_cit(x) for x in re.split(r";", c.get("reporter_citation") or "") if x.strip()]
        case_idx.append((c, cits))
    for m in sorted(metas, key=lambda x: x["doc_id"]):
        keys = [norm_cit(m.get("neutral_citation"))] + [norm_cit(x) for x in (m.get("reported_citations") or [])]
        keys = [k for k in keys if k]
        for c, cits in case_idx:
            how = ""
            if keys and set(keys) & set(cits):
                how = "citation"
            elif m.get("issue_date") and m.get("issue_date") == c.get("decision_date") and "Supreme" in (m.get("court") or "") and "Supreme" in (c.get("court") or ""):
                mk = {"-".join((J.norm_case_string(x) or "").split("-")[1:]) for x in (m.get("case_numbers") or [])}
                ck = {f"{a}-{b}" for a, b in re.findall(r"(\d{1,6})\s*(?:of|/)\s*((?:19|20)\d{2})", c.get("case_number") or "")}
                if mk & ck:
                    how = "decision date + case number"
            if how:
                rels.append(dict(source_judgment_id=jid(m.get("sha256") or ""), relation="MATCHES_CURATED_CASE", target=c["id"],
                                 citation=m["doc_id"], citation_kind=how, method="DETERMINISTIC_KEY_MATCH", status="AUTOMATED_NOT_VERIFIED"))
    rows["rel2"] = rels
    curated_hit = {x["source_judgment_id"] for x in rels if x["relation"] == "MATCHES_CURATED_CASE"}

    # ---------------- verification queue (high-risk / high-impact first)
    hi_topics = {"court_martial", "aft_jurisdiction", "writ_against_aft_order", "statutory_complaint", "disability_pension",
                 "dismissal_discharge_termination", "reinstatement", "natural_justice"}
    relmap = {x["judgment_id"]: x for x in rel_rows}
    metamap = defaultdict(list)
    for x in meta_rows:
        metamap[x["judgment_id"]].append(x)
    queue = []
    for sha in sorted(files):
        j = jid(sha)
        r = res.get(sha) or {}
        reasons, score = [], 0
        court = (by_sha_meta.get(sha) or [{}])[0].get("court", "") or files[sha]["location"]
        if "Supreme" in str(court) or files[sha]["location"] == "HF_LEGAL_KNOWLEDGE_ONLY":
            score += 3; reasons.append("Supreme Court / curated judgment")
        if relmap[j]["relevance_class"] == "DIRECT_MILITARY_LAW":
            score += 2; reasons.append("direct military law")
        t = set((r.get("topics") or {}).keys()) & hi_topics
        if t:
            score += len(t); reasons.append("high-impact topics: " + ",".join(sorted(t)))
        if j in curated_hit:
            score += 3; reasons.append("matches a curated Mimamsa case")
        if r.get("outcome_conflict"):
            score += 2; reasons.append("conflicting outcome phrases")
        if r.get("outcome_candidate") == "NOT_FOUND":
            score += 1; reasons.append("outcome not found")
        if any(x["date_status"] == "DIFFERS" for x in metamap[j]):
            score += 2; reasons.append("metadata date differs from text")
        if any(x["case_number_status"] == "NOT_CONFIRMED_IN_TEXT" for x in metamap[j]):
            score += 1; reasons.append("case number not confirmed in text")
        if any("crawler outcome" in x["contradictions"] for x in metamap[j]):
            score += 1; reasons.append("crawler outcome differs from text candidate")
        if r.get("extraction") == "PROCESSED_TRUNCATED_COPY":
            score += 3; reasons.append("stored copy truncated (later pages missing)")
        elif r.get("extraction") != "PROCESSED":
            score += 3; reasons.append("not processed / unreadable")
        if r.get("text_extraction") in ("NO_TEXT_LAYER", "PARTIAL_TEXT_LAYER"):
            score += 1; reasons.append(str(r.get("text_extraction")))
        if len(by_sha_meta.get(sha, [])) > 1:
            score += 1; reasons.append("file shared by several records")
        queue.append(dict(judgment_id=j, sha256=sha, court=court, title=(by_sha_meta.get(sha) or [{}])[0].get("title", ""),
                          priority_score=score, reasons="; ".join(reasons), relevance_class=relmap[j]["relevance_class"],
                          independent_review="NOT_REVIEWED"))
    reviewed = {}
    for f in sorted((AJ.PKG / "review").glob("review_*.csv")):
        for rv in csv.DictReader(io.StringIO(f.read_text(encoding="utf-8"))):
            reviewed[rv["judgment_id"]] = (f"REVIEWED ({f.stem}): identity {rv['identity_result']}, outcome {rv['outcome_result']}, "
                                           f"relevance {rv['relevance_result']}")
    for q in queue:
        q["independent_review"] = reviewed.get(q["judgment_id"], "NOT_REVIEWED")
    queue.sort(key=lambda x: (-x["priority_score"], x["judgment_id"]))
    for i, q in enumerate(queue, 1):
        q["rank"] = i
    rows["queue"] = queue

    # ---------------- excluded log: explicit disposition per record + title re-screen
    exc_lines = AJ.git(repo, "cat-file", "blob", f"{AJ.RAW}:data/excluded_judgments.jsonl").decode().splitlines()
    exc_rows, exc_by = [], Counter()
    for l in exc_lines:
        e = json.loads(l)
        flag = bool(TITLE_SCREEN.search(e.get("title") or ""))
        disp = "EXCLUDED_FILE_NOT_RETAINED_RESCREEN_CANDIDATE" if flag else "EXCLUDED_FILE_NOT_RETAINED"
        exc_rows.append(dict(doc_id=e["doc_id"], sha256=e["sha256"], court=e["court"], decided=e["decided"], title=e["title"],
                             reason=e["reason"], title_rescreen="MILITARY_OR_SERVICE_TERM_IN_TITLE" if flag else "", disposition=disp))
        exc_by[(e["court"], (e.get("decided") or "")[:4], disp)] += 1
    exc_rows.sort(key=lambda x: x["doc_id"])

    # ---------------- master inventory
    master = []
    for x in copy_rows:
        master.append(dict(item_id="FILE:" + x["sha256"], collection="SOURCE_FILE", identifier=x["path"], judgment_id=x["judgment_id"],
                           sha256=x["sha256"], court="", year="", disposition=x["disposition"]))
    for x in meta_rows:
        master.append(dict(item_id="RECORD:" + x["doc_id"], collection="METADATA_RECORD", identifier=x["doc_id"], judgment_id=x["judgment_id"],
                           sha256=x["sha256"], court=x["court"], year=(x["issue_date_meta"] or "")[:4], disposition=x["audit_disposition"]))
    for x in master:
        if x["collection"] == "SOURCE_FILE":
            ms = by_sha_meta.get(x["sha256"]) or []
            x["court"] = ms[0].get("court", "") if ms else "HF legal_knowledge (curated)"
            x["year"] = (ms[0].get("issue_date") or "")[:4] if ms else ""
    master.append(dict(item_id="EXCLUDED_LOG:data/excluded_judgments.jsonl", collection="EXCLUDED_LOG", identifier="data/excluded_judgments.jsonl",
                       judgment_id="", sha256="", court="(120,185 records; see HF_JUDGMENT_EXCLUDED_DISPOSITIONS.csv.gz)", year="",
                       disposition=f"{len(exc_rows)} records, each with an explicit disposition"))

    # ---------------- accounting
    acct = Counter(x["disposition"] for x in copy_rows)
    acct_meta = Counter(x["audit_disposition"] for x in meta_rows)
    processed = acct.get("PROCESSED", 0)
    unresolved = sum(v for k, v in acct.items() if k != "PROCESSED")
    assert processed + unresolved == len(copy_rows) == len(files), "file accounting identity failed"
    assert sum(acct_meta.values()) == len(meta_rows) == len(metas), "record accounting identity failed"
    assert len(exc_rows) == len(exc_lines), "excluded accounting identity failed"
    continuation = [dict(judgment_id=x["judgment_id"], sha256=x["sha256"], path=x["path"], disposition=x["disposition"],
                         needed=("bytes (HF download or working copy)" if "BYTES" in x["disposition"] else
                                 "OCR or repair" if "UNREADABLE" in x["disposition"] else
                                 "a complete copy (re-acquisition needs approval)" if "TRUNCATED" in x["disposition"] else "rerun extraction"))
                    for x in copy_rows if x["disposition"] != "PROCESSED"]

    out["HF_JUDGMENT_MASTER_INVENTORY.csv"] = csv_text(["item_id", "collection", "identifier", "judgment_id", "sha256", "court", "year", "disposition"],
                                                       sorted(master, key=lambda x: (x["collection"], x["item_id"])))
    out["HF_JUDGMENT_COPY_REGISTER.csv"] = csv_text(list(copy_rows[0].keys()), copy_rows)
    out["HF_JUDGMENT_METADATA_AUDIT.csv"] = csv_text(list(meta_rows[0].keys()), meta_rows)
    out["HF_JUDGMENT_RELEVANCE.csv"] = csv_text(list(rel_rows[0].keys()), rel_rows)
    out["HF_JUDGMENT_LEGAL_ISSUES.jsonl"] = jl(issues)
    out["HF_JUDGMENT_HOLDINGS.jsonl"] = jl(holds)
    out["HF_JUDGMENT_DUPLICATES.csv"] = csv_text(["group_id", "kind", "judgment_ids", "sha256s", "doc_ids", "count", "interpretation", "automated"], dups)
    out["HF_JUDGMENT_RELATIONSHIPS.csv"] = csv_text(["source_judgment_id", "relation", "target", "citation", "citation_kind", "method", "status"], rels)
    out["HF_JUDGMENT_VERIFICATION_QUEUE.csv"] = csv_text(["rank", "judgment_id", "sha256", "court", "title", "priority_score", "reasons",
                                                          "relevance_class", "independent_review"], queue)
    out["CONTINUATION_MANIFEST.csv"] = csv_text(["judgment_id", "sha256", "path", "disposition", "needed"], continuation)
    out["BATCH_STATUS.csv"] = csv_text(["batch", "files", "input_key", "complete", "batch_sha256"], bstatus)
    exc_csv = csv_text(["doc_id", "sha256", "court", "decided", "title", "reason", "title_rescreen", "disposition"], exc_rows).encode("utf-8")
    gz = io.BytesIO()
    with gzip.GzipFile(fileobj=gz, mode="wb", mtime=0, filename="") as g:
        g.write(exc_csv)
    binary = {"HF_JUDGMENT_EXCLUDED_DISPOSITIONS.csv.gz": gz.getvalue()}
    stats = dict(
        metadata_records=len(metas), source_files=len(files), distinct_judgments=len(files),
        files_by_location=dict(Counter(f["location"] for f in files.values())),
        file_dispositions=dict(sorted(acct.items())),
        files_rehashed_equal_to_hf_declared=sum(1 for x in copy_rows if "REHASHED_EQUALS" in x["source_document_verification"]), record_dispositions=dict(sorted(acct_meta.items())),
        excluded_records=len(exc_rows), excluded_dispositions=dict(Counter(x["disposition"] for x in exc_rows)),
        excluded_csv_sha256=hashlib.sha256(exc_csv).hexdigest(),
        relevance=dict(sorted(Counter(x["relevance_class"] for x in rel_rows).items())),
        date_status=dict(sorted(Counter(x["date_status"] for x in meta_rows).items())),
        case_number_status=dict(sorted(Counter(x["case_number_status"] for x in meta_rows).items())),
        neutral_citation_status=dict(sorted(Counter(x["neutral_citation_status"] for x in meta_rows).items())),
        outcome=dict(sorted(Counter(str(h["outcome_candidate"]) for h in holds).items())),
        outcome_conflicts=sum(1 for h in holds if h["outcome_conflict"]),
        text_extraction=dict(sorted(Counter(str(x["text_extraction"]) for x in copy_rows).items())),
        duplicates=dict(sorted(Counter(x["kind"] for x in dups).items())),
        relationships=dict(sorted(Counter(x["relation"] for x in rels).items())),
        curated_cases_matched=len({x["target"] for x in rels if x["relation"] == "MATCHES_CURATED_CASE"}),
        propositions=sum(len(h["propositions"] or []) for h in holds),
        courts=dict(sorted(Counter(str(x["court"]) for x in meta_rows).items())),
        years=dict(sorted(Counter((x["issue_date_meta"] or "unknown")[:4] for x in meta_rows).items())),
        excluded_by_court=dict(sorted(Counter(e["court"] for e in exc_rows).items())),
        batches_complete=sum(1 for b in bstatus if b["complete"]), batches=len(bstatus),
        independently_reviewed=len(reviewed),
        outcome_both_present=sum(1 for x in meta_rows if x["outcome_meta"] and x["outcome_text_candidate"] not in ("", None, "NOT_FOUND")),
        outcome_crawler_vs_text_differs=sum(1 for x in meta_rows if "crawler outcome" in x["contradictions"]), sc_records_without_case_number=sum(1 for x in meta_rows if "Supreme" in str(x["court"]) and not x["case_numbers_meta"]))
    return out, binary, stats
