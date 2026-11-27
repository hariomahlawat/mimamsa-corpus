// C14 follow-up probe (audit instance only): what an already-open viewer and a deep link show after withdrawal.
// node withdrawal_open_viewer.cjs <out-dir>   (env: B1_AUDIT_URL, B1_PASSWORD, NODE_PATH, PLAYWRIGHT_BROWSERS_PATH)
const fs = require("fs"), path = require("path");
const { chromium } = require("playwright");
const AUDIT = process.env.B1_AUDIT_URL || "http://127.0.0.1:5299", PW = process.env.B1_PASSWORD;
const DOC = "sc-1991-ex-havildar-rat-an-singh-1991insc300";
const OUT = path.resolve(process.argv[2] || "."); const SH = path.join(OUT, "screenshots");
const res = { doc: DOC, steps: [] }; const log = (k, v) => res.steps.push({ step: k, observed: v });
(async () => {
  const b = await chromium.launch();
  const mk = async () => { const c = await b.newContext({ viewport: { width: 1920, height: 1080 }, baseURL: AUDIT }); const p = await c.newPage(); return { c, p }; };
  const login = async (p, u) => { await p.goto("/"); await p.fill("#username", u); await p.fill("#password", PW); await p.click("form.login button[type=submit]"); await p.locator("#research").waitFor(); };
  const u = await mk(), a = await mk(); await login(u.p, process.env.B1_AUDIT_READER || "user"); await login(a.p, "admin");
  const rangeStatus = []; u.p.on("response", (r) => { if (r.url().includes("/api/v2/documents/")) rangeStatus.push(`${r.status()} ${r.url().split("/api/v2/documents/")[1].slice(0, 60)}`); });
  await u.p.goto(`/d/${DOC}`); await u.p.locator(".pagewrap canvas").first().waitFor({ timeout: 20000 });
  const n = await u.p.locator(".pagewrap canvas").count(); log("before: rendered page canvases", n);
  const csrf = (await (await a.c.request.get(AUDIT + "/api/session")).json()).csrf;
  const w = await a.c.request.post(AUDIT + "/api/admin/withdraw", { headers: { Origin: AUDIT, "X-CSRF-Token": csrf, "Content-Type": "application/json" }, data: { doc_id: DOC, reason: "C14 audit probe: open viewer behaviour (isolated copy)" } });
  log("withdraw API", `${w.status()} ${(await w.text()).slice(0, 120)}`);
  rangeStatus.length = 0;
  await u.p.fill("#pageinput", "6"); await u.p.press("#pageinput", "Enter"); await u.p.waitForTimeout(3000);
  await u.p.screenshot({ path: path.join(SH, "J13b-open-viewer-page6-after-withdrawal.jpg"), type: "jpeg", quality: 70 });
  log("after: go to page 6 in the open viewer — protected range responses", rangeStatus.slice(0, 8));
  log("after: notice in document pane", (await u.p.locator("#docpane").innerText()).replace(/\s+/g, " ").slice(0, 400));
  log("after: page 1 canvas still displayed", await u.p.locator(".pagewrap canvas").first().isVisible().catch(() => false));
  await u.p.goto(`/d/${DOC}`); await u.p.waitForTimeout(2000);
  await u.p.screenshot({ path: path.join(SH, "J13b-deep-link-after-withdrawal.jpg"), type: "jpeg", quality: 70 });
  log("deep link: toast", await u.p.locator("#toast").innerText().catch(() => "(none)"));
  log("deep link: main", (await u.p.locator("main").innerText()).replace(/\s+/g, " ").slice(0, 300));
  await b.close();
  fs.writeFileSync(path.join(OUT, "withdrawal_open_viewer.json"), JSON.stringify(res, null, 1));
  console.log(JSON.stringify(res, null, 1));
})();
