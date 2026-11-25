// Render one page of a (possibly very large) PDF with range loading, extract text items, and overlay
// highlight rectangles for a search term using the text-item transforms. Metrics go to window.__metrics.
import * as pdfjsLib from "pdfjs-dist";
import workerUrl from "pdfjs-dist/build/pdf.worker.min.mjs?url";

pdfjsLib.GlobalWorkerOptions.workerSrc = workerUrl;
const params = new URLSearchParams(location.search);
const file = params.get("file");
const pageNo = parseInt(params.get("page") || "1", 10);
const term = (params.get("q") || "court").toLowerCase();
const m = { file, pageNo, term };
const t0 = performance.now();

async function run() {
  const task = pdfjsLib.getDocument({ url: file, disableAutoFetch: true, disableStream: true, rangeChunkSize: 65536 });
  const doc = await task.promise;
  m.numPages = doc.numPages;
  m.open_ms = performance.now() - t0;
  const page = await doc.getPage(Math.min(pageNo, doc.numPages));
  const viewport = page.getViewport({ scale: 1.5 });
  const canvas = document.getElementById("c");
  canvas.width = viewport.width; canvas.height = viewport.height;
  const t1 = performance.now();
  await page.render({ canvasContext: canvas.getContext("2d"), viewport, canvas }).promise;
  m.render_ms = performance.now() - t1;
  const t2 = performance.now();
  const tc = await page.getTextContent();
  m.text_items = tc.items.length;
  m.text_ms = performance.now() - t2;
  // highlight: for each text item containing the term, compute the sub-rectangle by character proportion
  const overlay = document.getElementById("overlay");
  let hits = 0;
  for (const it of tc.items) {
    const s = (it.str || "").toLowerCase();
    let idx = s.indexOf(term);
    while (idx >= 0) {
      const tx = pdfjsLib.Util.transform(viewport.transform, it.transform);
      const fontH = Math.hypot(tx[2], tx[3]);
      const w = it.width * viewport.scale;
      const x = tx[4] + (w * idx) / s.length, wTerm = (w * term.length) / s.length;
      const div = document.createElement("div");
      div.className = "hl";
      Object.assign(div.style, { left: `${x}px`, top: `${tx[5] - fontH}px`, width: `${wTerm}px`, height: `${fontH}px` });
      overlay.appendChild(div);
      hits++; idx = s.indexOf(term, idx + term.length);
    }
  }
  m.highlights = hits;
  m.total_ms = performance.now() - t0;
  if (performance.memory) m.js_heap_mb = performance.memory.usedJSHeapSize / 2 ** 20;
  m.done = true;
}
run().catch((e) => { m.error = String(e); m.done = true; }).finally(() => { window.__metrics = m; });
