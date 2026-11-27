// C14 integration: results fully visible per viewport on the running instance (same probe as audit J10).
// node density_check.cjs   (env: B1_URL, B1_PASSWORD, NODE_PATH, PLAYWRIGHT_BROWSERS_PATH)
const { chromium } = require("playwright");
const BASE = process.env.B1_URL || "http://127.0.0.1:5199";
(async () => {
  const b = await chromium.launch(); const out = [];
  for (const vp of [{ width: 1366, height: 768 }, { width: 1920, height: 1080 }, { width: 2560, height: 1440 }]) {
    const p = await (await b.newContext({ viewport: vp, baseURL: BASE })).newPage();
    await p.goto("/"); await p.fill("#username", "user"); await p.fill("#password", process.env.B1_PASSWORD); await p.click("form.login button[type=submit]");
    await p.locator("#research").waitFor();
    await p.fill("#q", "disability pension invalided"); await p.press("#q", "Enter");
    await p.waitForFunction(() => document.querySelector("#results-head")?.getAttribute("aria-busy") !== "true" && !document.querySelector("#results-list.dim"));
    await p.waitForTimeout(400);
    out.push({ viewport: `${vp.width}x${vp.height}`, ...(await p.evaluate(() => ({
      hitsFullyVisible: [...document.querySelectorAll(".hit")].filter((e) => { const r = e.getBoundingClientRect(); return r.top >= 0 && r.bottom <= innerHeight && r.width > 0; }).length,
      groupsStartingInView: [...document.querySelectorAll(".rgroup")].filter((e) => { const r = e.getBoundingClientRect(); return r.top >= 0 && r.top < innerHeight; }).length,
      overflowX: document.documentElement.scrollWidth > innerWidth }))) });
    await p.screenshot({ path: `${__dirname}/density-${vp.width}.jpg`, type: "jpeg", quality: 70 });
  }
  await b.close(); console.log(JSON.stringify(out, null, 1));
  require("fs").writeFileSync(`${__dirname}/density_check.json`, JSON.stringify(out, null, 1));
})();
