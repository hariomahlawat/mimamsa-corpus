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
    page.on("response", async (r) => {
      if (r.url().includes("/pdf/")) {
        requests++; if (r.status() === 206) ranged++;
        const len = parseInt((await r.allHeaders())["content-length"] || "0", 10); bytes += len;
      }
    });
    const url = `${base}/?file=/pdf/${encodeURIComponent(c.file)}&page=${c.page}&q=${encodeURIComponent(c.q)}`;
    const t = Date.now();
    await page.goto(url);
    await page.waitForFunction(() => window.__metrics && window.__metrics.done, null, { timeout: 120000 });
    const m = await page.evaluate(() => window.__metrics);
    m.wall_ms = Date.now() - t; m.pdf_requests = requests; m.pdf_206 = ranged; m.pdf_bytes_fetched = bytes;
    m.file_bytes = c.bytes; m.label = c.label;
    if (c.screenshot) await page.screenshot({ path: c.screenshot });
    results.push(m); console.log(JSON.stringify(m));
    await ctx.close();
  }
  await browser.close();
  fs.writeFileSync(out, JSON.stringify(results, null, 1));
})();
