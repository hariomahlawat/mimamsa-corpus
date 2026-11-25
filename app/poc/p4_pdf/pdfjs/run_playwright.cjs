// Playwright driver for the PDF.js PoC. Usage: node run_playwright.cjs <baseUrl> <cases.json> <out.json>
const { chromium } = require("playwright");
const fs = require("fs");
(async () => {
  const [base, casesPath, out] = process.argv.slice(2);
  const cases = JSON.parse(fs.readFileSync(casesPath, "utf8"));
  const browser = await chromium.launch();
  const results = [];
  for (const c of cases) {
    const ctx = await browser.newContext();
    const page = await ctx.newPage();
    let bytes = 0, requests = 0, ranged = 0;
    const pending = [];
    page.on("requestfinished", (req) => {
      if (req.url().includes("/pdf")) {
        pending.push((async () => {
          const resp = await req.response(); const sz = await req.sizes();
          requests++; if (resp && resp.status() === 206) ranged++;
          bytes += sz.responseBodySize;               // bytes actually received, not Content-Length
        })());
      }
    });
    const fileUrl = c.url || `/pdf/${encodeURIComponent(c.file)}`;
    const url = `${base}/?file=${encodeURIComponent(fileUrl)}&page=${c.page}&q=${encodeURIComponent(c.q)}${c.auth ? `&auth=${c.auth}` : ""}`;
    const t = Date.now();
    await page.goto(url);
    await page.waitForFunction(() => window.__metrics && window.__metrics.done, null, { timeout: 120000 });
    const m = await page.evaluate(() => window.__metrics);
    await page.waitForTimeout(300); await Promise.all(pending);
    m.wall_ms = Date.now() - t; m.pdf_requests = requests; m.pdf_206 = ranged; m.pdf_bytes_fetched = bytes;
    m.file_bytes = c.bytes; m.label = c.label;
    if (c.screenshot) await page.screenshot({ path: c.screenshot });
    results.push(m); console.log(JSON.stringify(m));
    await ctx.close();
  }
  await browser.close();
  fs.writeFileSync(out, JSON.stringify(results, null, 1));
})();
