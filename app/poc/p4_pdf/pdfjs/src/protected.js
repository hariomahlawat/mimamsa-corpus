// Protected bootstrap (R2-N01 / Serving §10): no URL is ever given to PDF.js, so it cannot issue an unbounded
// GET. 1) bounded authorized metadata request; 2) PDFDataRangeTransport that fetches only explicit single
// ranges <= max_range, authenticated per request, pinned to the exact copy sha256; 503 (no credit) is retried
// with backoff; 401/404 (withdrawn / not authorized) destroys the document and shows a withdrawn state.
import * as pdfjsLib from "pdfjs-dist";

export async function openProtected(docId, token, metrics) {
  const auth = { Authorization: `Bearer ${token}` };
  const metaResp = await fetch(`/api/v2/documents/${encodeURIComponent(docId)}/pdf-meta`, { headers: auth, cache: "no-store" });
  if (!metaResp.ok) throw new Error(`meta ${metaResp.status}`);
  const meta = await metaResp.json();
  metrics.meta = meta;
  metrics.ranges = [];
  let task = null;
  const transport = new pdfjsLib.PDFDataRangeTransport(meta.length, null);
  const fetchRange = async (a, b) => {
    for (let attempt = 0; attempt < 30; attempt++) {
      const t = performance.now();
      const r = await fetch(`/api/v2/documents/${encodeURIComponent(docId)}/copies/${meta.copy_sha256}/range`,
                            { headers: { ...auth, Range: `bytes=${a}-${b}` }, cache: "no-store" });
      metrics.ranges.push({ a, b, status: r.status, ms: Math.round(performance.now() - t) });
      if (r.status === 206) {
        const buf = new Uint8Array(await r.arrayBuffer());
        if (buf.length !== b - a + 1 || r.headers.get("content-range") !== `bytes ${a}-${b}/${meta.length}`) throw new Error("bad 206");
        return buf;
      }
      if (r.status === 503) { await new Promise((res) => setTimeout(res, 50 * (attempt + 1))); continue; }
      metrics.withdrawn = r.status === 404 || r.status === 401;
      throw new Error(`range ${r.status}`);
    }
    throw new Error("credit unavailable");
  };
  transport.requestDataRange = (begin, end) => {
    (async () => {
      try {
        // split into supported ranges (never more than max_range per HTTP request), then hand PDF.js the
        // exact requested span in ONE onDataRange call (PDF.js expects one delivery per requested range)
        const out = new Uint8Array(end - begin);
        for (let a = begin; a < end; a += meta.max_range) {
          const b = Math.min(end, a + meta.max_range) - 1;
          out.set(await fetchRange(a, b), a - begin);
        }
        transport.onDataRange(begin, out);
      } catch (e) {
        metrics.transport_error = String(e);
        if (task) task.destroy();          // invalidate viewer state; already received bytes are outside recall
      }
    })();
  };
  task = pdfjsLib.getDocument({ range: transport, length: meta.length, rangeChunkSize: meta.chunk,
                                disableAutoFetch: true, disableStream: true });
  return task;
}
