// Protected original viewer (R2-N01 path, refactored from app/poc/p4_pdf/pdfjs/src/protected.js):
// 1) bounded authorised metadata request pinned to the exact copy; 2) PDFDataRangeTransport that fetches only explicit
// single ranges <= max_range, authenticated per request (session cookie), pinned to the copy sha256; 503 (no credit)
// is retried with backoff; 401/404 (withdrawn or not authorised) destroys the document and reports "unavailable".
// PDF.js is bundled offline (/vendor/pdfjs, pdfjs-dist 6.5.438); eval and scripting are off; no URL is given to PDF.js.
import * as pdfjs from "/vendor/pdfjs/pdf.min.mjs";

pdfjs.GlobalWorkerOptions.workerSrc = "/vendor/pdfjs/pdf.worker.min.mjs";

export class ProtectedViewer {
  constructor(host, { docId, copy, onState }) {
    this.host = host; this.docId = docId; this.copy = copy; this.onState = onState || (() => {});
    this.metrics = { ranges: [], meta: null, transport_error: null, withdrawn: false };
    this.doc = null; this.task = null; this.page = 1; this.scale = null; this.renderSeq = 0; this.destroyed = false;
    this.terms = []; this.ocr = false;
  }

  async open() {
    const q = this.copy ? `?copy=${encodeURIComponent(this.copy)}` : "";
    const r = await fetch(`/api/v2/documents/${encodeURIComponent(this.docId)}/pdf-meta${q}`, { cache: "no-store", credentials: "same-origin" });
    if (r.status === 404 || r.status === 401) { this.metrics.withdrawn = true; this.onState("unavailable"); return false; }
    if (!r.ok) throw new Error(`meta ${r.status}`);
    const meta = await r.json();
    this.metrics.meta = meta;
    const transport = new pdfjs.PDFDataRangeTransport(meta.length, null);
    const fetchRange = async (a, b) => {
      for (let attempt = 0; attempt < 30; attempt++) {
        if (this.destroyed) throw new Error("destroyed");
        const t = performance.now();
        const resp = await fetch(`/api/v2/documents/${encodeURIComponent(this.docId)}/copies/${meta.copy_sha256}/range`,
          { headers: { Range: `bytes=${a}-${b}`, ...(window.__mimamsaTestFail ? { "X-Mimamsa-Test-Fail": window.__mimamsaTestFail } : {}) }, cache: "no-store", credentials: "same-origin" });
        this.metrics.ranges.push({ a, b, status: resp.status, ms: Math.round(performance.now() - t) });
        if (resp.status === 206) {
          const buf = new Uint8Array(await resp.arrayBuffer());
          if (buf.length !== b - a + 1 || resp.headers.get("content-range") !== `bytes ${a}-${b}/${meta.length}`) throw new Error("bad 206");
          return buf;
        }
        if (resp.status === 503) { await new Promise((res) => setTimeout(res, 50 * (attempt + 1))); continue; }
        if (resp.status === 404 || resp.status === 401) { this.metrics.withdrawn = true; throw new Error("unavailable"); }
        throw new Error(`range ${resp.status}`);
      }
      throw new Error("credit unavailable");
    };
    transport.requestDataRange = (begin, end) => {
      (async () => {
        try {
          const out = new Uint8Array(end - begin);
          for (let a = begin; a < end; a += meta.max_range) {
            const b = Math.min(end, a + meta.max_range) - 1;
            out.set(await fetchRange(a, b), a - begin);
          }
          transport.onDataRange(begin, out);
        } catch (e) {
          this.metrics.transport_error = String(e.message || e);
          this.onState(this.metrics.withdrawn ? "unavailable" : "failed", this.metrics.transport_error);
          this.destroy();
        }
      })();
    };
    this.task = pdfjs.getDocument({
      range: transport, length: meta.length, rangeChunkSize: meta.chunk, disableAutoFetch: true, disableStream: true,
      isEvalSupported: false, enableXfa: false, cMapUrl: "/vendor/pdfjs/cmaps/", cMapPacked: true,
      standardFontDataUrl: "/vendor/pdfjs/standard_fonts/", wasmUrl: "/vendor/pdfjs/wasm/", iccUrl: "/vendor/pdfjs/iccs/",
    });
    try { this.doc = await this.task.promise; }
    catch (e) { if (!this.destroyed) this.onState(this.metrics.withdrawn ? "unavailable" : "failed", String(e.message || e)); return false; }
    this.onState("ready", this.doc.numPages);
    return true;
  }

  get numPages() { return this.doc ? this.doc.numPages : 0; }

  async render(pageNo, { terms, ocr } = {}) {
    if (!this.doc || this.destroyed) return;
    if (terms) this.terms = terms;
    if (ocr !== undefined) this.ocr = ocr;
    this.page = Math.max(1, Math.min(this.doc.numPages, pageNo));
    const seq = ++this.renderSeq;
    const host = this.host;
    const width = Math.max(320, host.clientWidth - 48);
    let page;
    try { page = await this.doc.getPage(this.page); } catch (e) { if (!this.destroyed) this.onState("failed", String(e.message || e)); return; }
    if (seq !== this.renderSeq || !host.isConnected) return;
    host.replaceChildren();
    const legend = document.createElement("div");
    legend.className = "pdf-legend";
    const sw = (cls, text) => { const s = document.createElement("span"); const k = document.createElement("span"); k.className = "sw " + cls; s.append(k, text); return s; };
    legend.append(sw("sw-search", "Search hit (from the PDF text layer)"));
    if (this.ocr) legend.append(sw("sw-ocr", "Highlight from OCR-derived text: approximate"));
    const idn = document.createElement("span"); idn.textContent = `Original bytes · copy ${this.metrics.meta.copy_sha256.slice(0, 12)} · physical page ${this.page} of ${this.doc.numPages}`;
    legend.append(idn);
    host.append(legend);
    const wrap = document.createElement("div");
    wrap.className = "pagewrap";
    host.append(wrap);
    const ph = document.createElement("div"); ph.className = "placeholder"; ph.textContent = `Loading page ${this.page}…`;
    const base = page.getViewport({ scale: 1 });
    const scale = this.scale || Math.min(2.5, width / base.width);
    const vp = page.getViewport({ scale });
    wrap.style.width = `${Math.floor(vp.width)}px`; wrap.style.height = `${Math.floor(vp.height)}px`;
    wrap.style.setProperty("--total-scale-factor", String(scale));
    wrap.style.setProperty("--scale-round-x", "1px"); wrap.style.setProperty("--scale-round-y", "1px");
    wrap.append(ph);
    const ratio = window.devicePixelRatio || 1;
    const canvas = document.createElement("canvas");
    canvas.width = Math.floor(vp.width * ratio); canvas.height = Math.floor(vp.height * ratio);
    canvas.style.width = `${Math.floor(vp.width)}px`; canvas.style.height = `${Math.floor(vp.height)}px`;
    canvas.setAttribute("role", "img");
    canvas.setAttribute("aria-label", `Original page ${this.page} of ${this.doc.numPages}. The page text is available to screen readers in the text layer and in the Text view.`);
    try {
      await page.render({ canvas, canvasContext: canvas.getContext("2d"), viewport: vp, transform: ratio !== 1 ? [ratio, 0, 0, ratio, 0, 0] : null }).promise;
    } catch (e) { if (!this.destroyed && seq === this.renderSeq) this.onState("failed", String(e.message || e)); return; }
    if (seq !== this.renderSeq || !host.isConnected) return;
    ph.remove();
    wrap.prepend(canvas);
    const tl = document.createElement("div");
    tl.className = "textLayer" + (this.ocr ? " ocr" : "");
    wrap.append(tl);
    try {
      const layer = new pdfjs.TextLayer({ textContentSource: await page.getTextContent(), container: tl, viewport: vp });
      await layer.render();
      this.marks = markTerms(layer.textDivs, this.terms);
    } catch { this.marks = 0; }
    this.onState("rendered", this.page);
  }

  invalidate() { this.renderSeq++; }

  setScale(s) { this.scale = s; return this.render(this.page); }

  destroy() {
    this.destroyed = true;
    try { this.task && this.task.destroy(); } catch { /* ignore */ }
    this.doc = null;
  }
}

function markTerms(divs, terms) {
  const words = [...new Set((terms || []).filter((t) => t && t.length > 1))];
  if (!words.length) return 0;
  const esc = words.map((w) => w.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).sort((a, b) => b.length - a.length);
  const rx = new RegExp(`(?<![\\p{L}\\p{N}\\p{M}])(?:${esc.join("|")})(?![\\p{L}\\p{N}\\p{M}])`, "giu");
  let n = 0;
  for (const div of divs) {
    const text = div.textContent;
    rx.lastIndex = 0;
    if (!rx.test(text)) continue;
    rx.lastIndex = 0;
    const frag = document.createDocumentFragment();
    let pos = 0;
    for (const m of text.matchAll(rx)) {
      frag.append(text.slice(pos, m.index));
      const mk = document.createElement("mark"); mk.textContent = m[0]; frag.append(mk);
      pos = m.index + m[0].length; n++;
    }
    frag.append(text.slice(pos));
    div.replaceChildren(frag);
  }
  return n;
}
