"""P4: compare PDF text extraction libraries. Each (library, pdf) runs in a fresh child process so peak RSS
and time are isolated.

python -I bench_extract.py run <pdf_list.json> <vocab.txt> <out.json>
python -I bench_extract.py child <lib> <pdf> <max_pages>        (internal)
"""
import json, os, re, resource, subprocess, sys, time, unicodedata
from collections import Counter
from pathlib import Path

LIBS = ["pypdfium2", "pdfminer", "pdfplumber", "pymupdf"]
HIGHLIGHT = "court"   # a word to locate on page 1 for highlight-rectangle feasibility


def child(lib, pdf, max_pages):
    t0 = time.perf_counter()
    pages, nwords_boxes, rects = [], 0, None
    if lib == "pypdfium2":
        import pypdfium2 as pdfium
        doc = pdfium.PdfDocument(pdf)
        n = min(len(doc), max_pages)
        for i in range(n):
            tp = doc[i].get_textpage(); pages.append(tp.get_text_range())
        t_text = time.perf_counter() - t0
        tp = doc[0].get_textpage()
        nwords_boxes = tp.count_chars()          # per-char boxes available via get_charbox(i)
        _ = [tp.get_charbox(i) for i in range(min(nwords_boxes, 2000))]
        s = tp.search(HIGHLIGHT, match_case=False); m = s.get_next()
        rects = None if not m else [tp.get_rect(j) for j in range(tp.count_rects(m[0], m[1]))][:2]
    elif lib == "pdfminer":
        from pdfminer.high_level import extract_pages
        from pdfminer.layout import LTTextContainer, LTChar
        n = 0
        for i, layout in enumerate(extract_pages(pdf, maxpages=max_pages)):
            txt = "".join(el.get_text() for el in layout if isinstance(el, LTTextContainer))
            pages.append(txt); n += 1
            if i == 0:
                for el in layout:
                    if isinstance(el, LTTextContainer):
                        for line in el:
                            for ch in getattr(line, "_objs", []):
                                if isinstance(ch, LTChar): nwords_boxes += 1
        t_text = time.perf_counter() - t0
        rects = "chars with bbox available (LTChar); phrase search must be implemented by the caller"
    elif lib == "pdfplumber":
        import pdfplumber
        with pdfplumber.open(pdf) as doc:
            n = min(len(doc.pages), max_pages)
            for i in range(n):
                pages.append(doc.pages[i].extract_text() or "")
            t_text = time.perf_counter() - t0
            w = doc.pages[0].extract_words(); nwords_boxes = len(w)
            hits = doc.pages[0].search(HIGHLIGHT, regex=False, case=False)
            rects = [[h["x0"], h["top"], h["x1"], h["bottom"]] for h in hits[:2]]
    elif lib == "pymupdf":
        import pymupdf
        doc = pymupdf.open(pdf)
        n = min(len(doc), max_pages)
        for i in range(n):
            pages.append(doc[i].get_text())
        t_text = time.perf_counter() - t0
        nwords_boxes = len(doc[0].get_text("words"))
        rects = [list(r) for r in doc[0].search_for(HIGHLIGHT)[:2]]
    print(json.dumps({"pages": pages, "t_text_s": t_text, "t_total_s": time.perf_counter() - t0,
                      "page1_boxes": nwords_boxes, "page1_highlight_rects": rects,
                      "child_peak_rss_mb": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024}))


def quality(pages, vocab):
    text = "\n".join(pages)
    toks = re.findall(r"[A-Za-z]{2,}", text)
    deva = sum(1 for ch in text if "ऀ" <= ch <= "ॿ")
    pua = sum(1 for ch in text if "" <= ch <= "")
    cid = len(re.findall(r"\(cid:\d+\)", text))
    letters = sum(1 for ch in text if ch.isalpha())
    return dict(chars=len(text), pages_with_text=sum(1 for p in pages if len(p.strip()) > 50), pages=len(pages),
                latin_tokens=len(toks), dict_word_rate=round(sum(t.lower() in vocab for t in toks) / max(1, len(toks)), 4),
                devanagari_share=round(deva / max(1, letters), 4), private_use_chars=pua, cid_tokens=cid,
                replacement_chars=text.count("�"))


def bag_f1(a, b):
    ca, cb = Counter(re.findall(r"\w+", a.lower())), Counter(re.findall(r"\w+", b.lower()))
    inter = sum((ca & cb).values())
    if not ca or not cb: return 0.0
    p, r = inter / sum(ca.values()), inter / sum(cb.values())
    return round(2 * p * r / (p + r), 4) if p + r else 0.0


def run(pdf_list, vocab_path, out):
    items = json.loads(Path(pdf_list).read_text())
    vocab = set(Path(vocab_path).read_text().split())
    res = []
    for it in items:
        texts = {}
        for lib in LIBS:
            t = time.perf_counter()
            try:
                p = subprocess.run([sys.executable, "-I", __file__, "child", lib, it["path"], str(it.get("max_pages", 400))],
                                   capture_output=True, timeout=900)
                if p.returncode != 0:
                    res.append(dict(doc=it["doc_id"], category=it["category"], lib=lib, error=p.stderr.decode()[-300:])); continue
                j = json.loads(p.stdout)
            except subprocess.TimeoutExpired:
                res.append(dict(doc=it["doc_id"], category=it["category"], lib=lib, error="timeout 900s")); continue
            texts[lib] = "\n".join(j["pages"])
            r = dict(doc=it["doc_id"], category=it["category"], lib=lib, bytes=os.path.getsize(it["path"]),
                     t_text_s=round(j["t_text_s"], 3), s_per_page=round(j["t_text_s"] / max(1, len(j["pages"])), 4),
                     wall_incl_import_s=round(time.perf_counter() - t, 3), child_peak_rss_mb=round(j["child_peak_rss_mb"], 1),
                     page1_boxes=j["page1_boxes"], page1_highlight_rects=j["page1_highlight_rects"], **quality(j["pages"], vocab))
            res.append(r)
            print(it["doc_id"], lib, r["t_text_s"], r["chars"], r["dict_word_rate"], flush=True)
        # agreement with the other libraries (bag-of-words F1); no library is ground truth
        for r in res:
            if r["doc"] == it["doc_id"] and "error" not in r:
                others = [bag_f1(texts[r["lib"]], texts[o]) for o in texts if o != r["lib"]]
                r["mean_bow_f1_vs_others"] = round(sum(others) / len(others), 4) if others else None
    Path(out).write_text(json.dumps({"loadavg": os.getloadavg(), "results": res}, indent=1))


if __name__ == "__main__":
    if sys.argv[1] == "child":
        child(sys.argv[2], sys.argv[3], int(sys.argv[4]))
    else:
        run(*sys.argv[2:5])
