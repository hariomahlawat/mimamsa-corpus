// R2-N01 PDF.js protected bootstrap test. Usage: node run_protected.cjs <viteBase> <apiBase> <out.json>
// Independent observation: every network request the browser makes is captured with its headers and status.
const { chromium } = require("playwright");
const fs = require("fs");
const [base, api, out] = process.argv.slice(2);
const post = (path, token) => fetch(api + path, { method: "POST", headers: { Authorization: `Bearer ${token}` } }).then(async (r) => ({ status: r.status, body: await r.text() }));

async function run(browser, c) {
  const ctx = await browser.newContext();
  const page = await ctx.newPage();
  const net = [];
  page.on("requestfinished", async (req) => {
    if (!req.url().includes("/api/")) return;
    const resp = await req.response(); const sz = await req.sizes(); const h = req.headers();
    net.push({ url: req.url().replace(/copies\/[0-9a-f]{64}/, "copies/<sha>"), status: resp && resp.status(), range: h["range"] || null,
               auth: !!h["authorization"], bytes: sz.responseBodySize, t: Date.now() });
  });
  page.on("requestfailed", (req) => {
    if (!req.url().includes("/api/")) return;
    const h = req.headers();   // a cancelled/aborted request still records what was sent
    net.push({ url: req.url().replace(/copies\/[0-9a-f]{64}/, "copies/<sha>"), failed: req.failure() && req.failure().errorText,
               range: h["range"] || null, auth: !!h["authorization"], bytes: 0, t: Date.now() });
  });
  const t0 = Date.now();
  await page.goto(`${base}/?mode=protected&doc=${c.doc}&token=${c.token}&page=1&q=court`);
  await page.waitForFunction(() => window.__metrics && window.__metrics.done, null, { timeout: 120000 });
  const m = await page.evaluate(() => window.__metrics);
  const r = { label: c.label, first_page: { total_ms: m.total_ms, render_ms: m.render_ms, numPages: m.numPages, error: m.error || null, highlights: m.highlights },
              bytes_after_first_page: net.reduce((s, x) => s + (x.bytes || 0), 0), length: m.meta && m.meta.length };
  if (c.withdrawBefore) { r.withdraw = await post(`/admin/withdraw?doc=${c.doc}&sha=${m.meta.copy_sha256}`, "tok-admin"); r.fence_at = Date.now(); }
  if (c.goto) {
    r.goto = await page.evaluate(async (n) => await window.__goto(n), c.goto);
    await page.waitForTimeout(300);
  }
  r.metrics_ranges = (await page.evaluate(() => window.__metrics.ranges)) || [];
  r.transport_error = await page.evaluate(() => window.__metrics.transport_error || null);
  r.network = net;
  r.total_bytes = net.reduce((s, x) => s + (x.bytes || 0), 0);
  const rangeReqs = net.filter((x) => x.url.includes("/range"));
  r.summary = {
    requests: net.length, range_requests: rangeReqs.length, all_range_requests_authenticated: rangeReqs.every((x) => x.auth),
    all_range_requests_have_range_header: rangeReqs.every((x) => x.range), max_range_bytes: Math.max(0, ...rangeReqs.map((x) => x.bytes || 0)),
    any_request_without_range_to_pdf: net.some((x) => x.url.includes("/copies/") && !x.range),
    statuses: rangeReqs.reduce((o, x) => ((o[x.status] = (o[x.status] || 0) + 1), o), {}),
    post_fence_206: r.fence_at ? rangeReqs.filter((x) => x.t > r.fence_at && x.status === 206).length : null,
    fraction_of_file_fetched: r.length ? +(r.total_bytes / r.length).toFixed(4) : null, wall_ms: Date.now() - t0 };
  await ctx.close();
  return r;
}

(async () => {
  const browser = await chromium.launch();
  const cases = [
    { label: "46MB rules: first page then near-end jump (p47/47)", doc: "doc-big", token: "tok-alice", goto: 47 },
    { label: "BNSS 282 pages: first page then near-end jump (p280)", doc: "doc-bnss", token: "tok-alice", goto: 280 },
    { label: "unauthenticated viewer (forged token)", doc: "doc-big", token: "forged" },
    { label: "another user's session (bob, not granted)", doc: "doc-big", token: "tok-bob" },
    { label: "BNSS: withdraw between chunks, then jump to p270", doc: "doc-bnss", token: "tok-alice", goto: 270, withdrawBefore: true },
    { label: "unrelated eligible document after the withdrawal (positive control)", doc: "doc-big", token: "tok-alice", goto: 30 },
  ];
  const results = [];
  for (const c of cases) { const r = await run(browser, c); results.push(r); console.log(JSON.stringify({ label: r.label, first: r.first_page, goto: r.goto, summary: r.summary })); }
  await browser.close();
  fs.writeFileSync(out, JSON.stringify({ pdfjs_dist: require("./package.json").dependencies["pdfjs-dist"], playwright: require("playwright/package.json").version, results }, null, 1));
})();
