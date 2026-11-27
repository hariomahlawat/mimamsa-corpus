// C14 S1 evidence: density measurement (same method as the walkthrough audit J10) and screenshots of the new search
// behaviour on the real sample. node capture.cjs <base-url> <password> <out-dir>   (user account "user")
const fs = require("fs"), path = require("path");
const { chromium } = require("playwright");
const [base, pw, out] = process.argv.slice(2);
fs.mkdirSync(out, { recursive: true });
(async () => {
  const b = await chromium.launch(); const res = {};
  const page = async (vp) => { const c = await b.newContext({ viewport: vp, baseURL: base }); const p = await c.newPage();
    await p.goto("/"); await p.fill("#username", "user"); await p.fill("#password", pw); await p.click("form.login button[type=submit]");
    await p.locator("#research").waitFor(); return p; };
  const search = async (p, q) => { await p.fill("#q", q); await p.press("#q", "Enter");
    await p.waitForFunction(() => document.querySelector("#results-head")?.getAttribute("aria-busy") !== "true" && !document.querySelector("#results-list.dim")); await p.waitForTimeout(300); };
  for (const vp of [{ width: 1366, height: 768 }, { width: 1920, height: 1080 }, { width: 2560, height: 1440 }]) {
    const p = await page(vp);
    await search(p, "disability pension invalided");
    res[`${vp.width}x${vp.height}`] = await p.evaluate(() => ({
      hitsFullyVisible: [...document.querySelectorAll(".hit")].filter((e) => { const r = e.getBoundingClientRect(); return r.top >= 0 && r.bottom <= innerHeight; }).length,
      groupsStartingInView: [...document.querySelectorAll(".rgroup")].filter((e) => e.getBoundingClientRect().top < innerHeight).length,
      overflowX: document.documentElement.scrollWidth > innerWidth }));
    await p.screenshot({ path: path.join(out, `density-${vp.width}.jpg`), type: "jpeg", quality: 70 });
    await p.context().close();
  }
  const p = await page({ width: 1920, height: 1080 });
  for (const [q, f] of [["section 302 IPC", "alias-ipc"], ["s.69 Army Act", "editions-nested"], ["Dharamvir Singh", "case-name"], ["(2013) 7 SCC 316", "citation-not-held"], ["court marshal", "suggestion"], ["court martial", "pager"]]) {
    await search(p, q);
    if (f === "pager") await p.locator("#results-list").evaluate((e) => e.scrollTo(0, e.scrollHeight));
    await p.screenshot({ path: path.join(out, `${f}.jpg`), type: "jpeg", quality: 70 });
  }
  await p.selectOption("#service", "army"); await search(p, "punishments a commanding officer can award");
  await p.screenshot({ path: path.join(out, "service-army.jpg"), type: "jpeg", quality: 70 });
  await b.close();
  fs.writeFileSync(path.join(out, "density.json"), JSON.stringify(res, null, 1));
  console.log(JSON.stringify(res));
})();
