// C14 B1 walkthrough: drives the real UI as a user and an Admin, recording observations, timings and screenshots.
// Observations, not an acceptance oracle: nothing here passes or fails the build. Non-destructive journeys run on
// B1_URL (the commissioned instance); withdrawal, lockout and service-kill journeys run only on B1_AUDIT_URL, an
// isolated instance over a cloned database (see WALKTHROUGH_REPORT.md §1).
//
//   set NODE_PATH=<dir>\node_modules  PLAYWRIGHT_BROWSERS_PATH=<dir>\browsers
//   set B1_URL=http://127.0.0.1:5199  B1_AUDIT_URL=http://127.0.0.1:5299  B1_PASSWORD=<password of admin and user>
//   set B1_STOP_AUDIT=<command that stops the audit instance>  B1_START_AUDIT=<command that starts it>
//   node walkthrough.cjs <out-dir>
const fs = require("fs");
const path = require("path");
const { execSync } = require("child_process");
const { chromium } = require("playwright");

const BASE = process.env.B1_URL || "http://127.0.0.1:5199";
const AUDIT = process.env.B1_AUDIT_URL || "http://127.0.0.1:5299";
const PW = process.env.B1_PASSWORD;
const OUT = path.resolve(process.argv[2] || "walkthrough-out");
const SHOTS = path.join(OUT, "screenshots");
fs.mkdirSync(SHOTS, { recursive: true });
const WITHDRAW_DOC = "sc-1987-ranjit-thakur-1987insc285";

const run = { started: new Date().toISOString(), base: BASE, audit: AUDIT, journeys: [] };
let J;
const ONLY = (process.env.B1_ONLY || "").split(",").filter(Boolean);
const want = (id) => !ONLY.length || ONLY.includes(id);
const journey = (id, title, instance = BASE) => { J = { id, title, instance, steps: [], screenshots: [] }; run.journeys.push(J); };
const obs = (step, observed) => J.steps.push({ step, observed });
async function step(name, fn) {
  try { const v = await fn(); if (v !== undefined) obs(name, v); }
  catch (e) { J.steps.push({ step: name, error: String(e.message || e).split("\n")[0].slice(0, 300) }); }
}
async function shot(page, name, full = false) {
  await page.waitForTimeout(350);
  const file = `${J.id}-${name}.jpg`;
  await page.screenshot({ path: path.join(SHOTS, file), type: "jpeg", quality: 70, fullPage: full });
  J.screenshots.push({ file, viewport: page.viewportSize() });
}
async function newPage(browser, vp = { width: 1920, height: 1080 }, base = BASE) {
  const ctx = await browser.newContext({ viewport: vp, baseURL: base, permissions: ["clipboard-read", "clipboard-write"] });
  const page = await ctx.newPage();
  page.on("console", (m) => { if (m.type() === "error") (J.console ||= []).push(m.text().slice(0, 200)); });
  return { ctx, page };
}
async function login(page, user, pass = PW) {
  await page.goto("/");
  await page.fill("#username", user);
  await page.fill("#password", pass);
  await page.click("form.login button[type=submit]");
  await page.locator("#research").waitFor({ timeout: 15000 });
}
async function search(page, q) {
  const t = Date.now();
  await page.fill("#q", q);
  await page.press("#q", "Enter");
  await page.waitForFunction(() => document.querySelector("#results-head")?.getAttribute("aria-busy") !== "true" && !document.querySelector("#results-list.dim"), null, { timeout: 15000 });
  await page.waitForTimeout(100);
  return Date.now() - t;
}
async function openFirstHit(page) {
  const t = Date.now();
  await page.locator(".hit").first().click();
  await page.locator(".pagewrap canvas").first().waitFor({ state: "visible", timeout: 20000 });
  return Date.now() - t;
}
const text = (page, sel, n = 600) => page.locator(sel).first().innerText({ timeout: 5000 }).then((s) => s.replace(/\s+/g, " ").trim().slice(0, n));
async function api(ctxOrReq, method, url, opts = {}) {
  const r = await ctxOrReq.fetch(url, { method, failOnStatusCode: false, maxRedirects: 0, ...opts });
  let body = ""; try { body = (await r.text()).slice(0, 160); } catch { /* binary */ }
  return { status: r.status(), body };
}
const a11y = (page) => page.evaluate(() => {
  const issues = [];
  for (const sel of ["header", "nav", "[role=search]", "main", "footer[role=contentinfo]"]) if (!document.querySelector(sel)) issues.push(`missing landmark ${sel}`);
  const named = (el) => (el.getAttribute("aria-label") || el.getAttribute("aria-labelledby") || el.getAttribute("title") || (el.labels && el.labels.length) || el.textContent.trim()).toString().length > 0;
  for (const el of document.querySelectorAll("button, a[href], input:not([type=hidden]), select, textarea, [role=tab]"))
    if (el.offsetParent !== null && !named(el)) issues.push(`unnamed ${el.tagName.toLowerCase()}.${el.className}`);
  return issues;
});

(async () => {
  const browser = await chromium.launch();

  // ---------------------------------------------------------------- J01 authentication and session
  journey("J01", "Authentication, logout and session");
  if (want("J01")) { const { ctx, page } = await newPage(browser);
    await step("open sign-in page", async () => { await page.goto("/"); await page.locator("#username").waitFor(); await shot(page, "signin"); return await text(page, "main", 400); });
    await step("wrong password", async () => { await page.fill("#username", "user"); await page.fill("#password", "wrong-pass"); await page.click("form.login button[type=submit]"); await page.waitForTimeout(800); await shot(page, "wrong-password"); return await text(page, "main", 400); });
    await step("sign in as user", async () => { const t = Date.now(); await login(page, "user"); return `research shell visible after ${Date.now() - t} ms`; });
    await step("landing view (dashboard)", async () => { await shot(page, "landing-user"); return await text(page, "main", 900); });
    await step("session cookie flags", async () => (await ctx.cookies()).map((c) => ({ name: c.name, httpOnly: c.httpOnly, secure: c.secure, sameSite: c.sameSite, expires: c.expires })));
    await step("user menu", async () => { await page.locator("#usermenu button").first().click(); await shot(page, "user-menu"); return await text(page, "#usermenu", 300); });
    await step("sign out", async () => { await page.getByRole("menuitem", { name: "Sign out" }).click(); await page.waitForTimeout(600); await shot(page, "signed-out"); return await text(page, "main", 300); });
    await step("browser Back after sign-out", async () => { await page.goBack(); await page.waitForTimeout(800); await shot(page, "back-after-signout"); return { url: page.url(), researchVisible: await page.locator("#research").isVisible().catch(() => false), signInVisible: await page.locator("#username").isVisible().catch(() => false) }; });
    await step("deep link after sign-out", async () => { await page.goto("/d/act-army-1950?p=25"); await page.waitForTimeout(800); return { url: page.url(), signInVisible: await page.locator("#username").isVisible().catch(() => false) }; });
    await ctx.close(); }

  // ---------------------------------------------------------------- J02 navigation, workspaces, keyboard
  journey("J02", "Dashboard, navigation and keyboard");
  if (want("J02")) { const { ctx, page } = await newPage(browser);
    await login(page, "user");
    await step("workspace links (user)", async () => (await page.locator("#workspaces a").allInnerTexts()).map((s) => s.trim()));
    for (const [name, slug] of [["Statutes", "statutes"], ["Graph", "graph"], ["Studio", "studio"], ["Assistant", "assistant"]])
      await step(`open ${name}`, async () => { await page.locator("#workspaces a", { hasText: name }).first().click(); await page.waitForTimeout(700); await shot(page, slug); return await text(page, "main", 400); });
    await step("? shortcut help", async () => { await page.goto("/r"); await page.locator("#research").waitFor(); await page.locator("body").click({ position: { x: 5, y: 300 } }); await page.keyboard.press("?"); await page.waitForTimeout(500); await shot(page, "shortcut-help"); return (await page.locator("dialog[open]").count()) ? await text(page, "dialog[open]", 500) : "no dialog opened"; });
    await step("command palette (:)", async () => { await page.keyboard.press("Escape"); await page.keyboard.press("Shift+Semicolon"); await page.waitForTimeout(400); await shot(page, "command-palette"); return (await page.locator("dialog[open]").count()) ? await text(page, "dialog[open]", 400) : "no palette"; });
    await step("/ focuses search", async () => { await page.keyboard.press("Escape"); await page.locator("body").click({ position: { x: 5, y: 300 } }); await page.keyboard.press("/"); return await page.evaluate(() => document.activeElement?.id); });
    await step("first 15 Tab stops", async () => { await page.goto("/r"); await page.locator("#research").waitFor(); const stops = []; for (let i = 0; i < 15; i++) { await page.keyboard.press("Tab"); stops.push(await page.evaluate(() => { const e = document.activeElement; return `${e.tagName.toLowerCase()}${e.id ? "#" + e.id : ""} "${(e.getAttribute("aria-label") || e.textContent || e.value || "").trim().slice(0, 40)}"`; })); } return stops; });
    await step("a11y basics on landing", () => a11y(page));
    await ctx.close(); }

  // ---------------------------------------------------------------- J03 identifier search, viewer, PDF navigation
  journey("J03", "Statutory identifier search and PDF viewer");
  if (want("J03")) { const { ctx, page } = await newPage(browser);
    await login(page, "user");
    await step("search s.69 Army Act", async () => { const ms = await search(page, "s.69 Army Act"); await shot(page, "results"); return { ms, chips: await page.locator(".qchip").allInnerTexts(), head: await text(page, "#results-head", 200), hits: await page.locator(".hit").count(), groups: await page.locator(".rgroup").count() }; });
    await step("open first hit (time to first PDF canvas)", async () => { const ms = await openFirstHit(page); await shot(page, "document"); return { ms, dochead: await text(page, ".dochead", 400), toolbar: await text(page, "#toolbar", 300) }; });
    await step("highlight marks on the original", async () => ({ marks: await page.locator(".textLayer mark").count() }));
    await step("N next hit", async () => { await page.locator("#viewer").click({ position: { x: 20, y: 20 } }).catch(() => {}); await page.keyboard.press("n"); await page.waitForTimeout(400); return await text(page, ".hitcount", 60); });
    await step("go to page 30 via page box", async () => { const t = Date.now(); await page.fill("#pageinput", "30"); await page.press("#pageinput", "Enter"); await page.waitForTimeout(900); await shot(page, "page-30"); return { ms_incl_wait: Date.now() - t, pageInput: await page.inputValue("#pageinput") }; });
    await step("zoom in twice then fit width", async () => { await page.getByRole("button", { name: "Zoom in" }).click(); await page.getByRole("button", { name: "Zoom in" }).click(); await page.waitForTimeout(600); await shot(page, "zoomed"); await page.getByRole("button", { name: "Fit width" }).click(); return "done"; });
    await step("Text view (T)", async () => { await page.getByRole("button", { name: "Text", exact: true }).click(); await page.locator(".textview").waitFor({ timeout: 8000 }); await shot(page, "text-view"); return await text(page, ".textview", 400); });
    await step("Hindi Army Act text quality", async () => { await page.goto("/d/act-army-1950-hi?p=16"); await page.waitForTimeout(2500); await page.getByRole("button", { name: "Text", exact: true }).click().catch(() => {}); await page.waitForTimeout(1200); await shot(page, "hindi-text"); return await text(page, "#docpane", 300); });
    await ctx.close(); }

  // ---------------------------------------------------------------- J04 judgment, evidence, provenance, related
  journey("J04", "Judgment viewer, evidence status, provenance and cross-references");
  if (want("J04")) { const { ctx, page } = await newPage(browser);
    await login(page, "user");
    await step("search 2013 INSC 408", async () => ({ ms: await search(page, "2013 INSC 408"), first: await text(page, ".rgroup", 300) }));
    await step("open judgment", async () => { const ms = await openFirstHit(page); await shot(page, "judgment"); return { ms, dochead: await text(page, ".dochead", 700), axes: await page.locator("details.axis").count() }; });
    await step("context tabs available", async () => (await page.getByRole("tab").allInnerTexts()).map((s) => s.trim()));
    for (const tab of ["Evidence", "Provenance", "Cited/Citing", "Related", "Notes"])
      await step(`tab ${tab}`, async () => { const t = page.getByRole("tab", { name: tab }); if (!(await t.count())) return "tab not present"; await t.first().click(); await page.waitForTimeout(500); await shot(page, "tab-" + tab.replace(/\W/g, "").toLowerCase()); return await text(page, ".ctx-body", 700); });
    await step("party-name search ranks the judgment", async () => { await search(page, "Dharamvir Singh"); await shot(page, "party-name-search"); const ids = await page.locator(".rgroup").evaluateAll((els) => els.map((e) => e.dataset.doc)); return { rank: ids.indexOf("sc-2013-dharamvir-singh-2013insc408") + 1, firstThree: ids.slice(0, 3) }; });
    await ctx.close(); }

  // ---------------------------------------------------------------- J05 citation copy and exact page navigation
  journey("J05", "Citation copying and exact source-page navigation");
  if (want("J05")) { const { ctx, page } = await newPage(browser);
    await login(page, "user");
    let permalink = null;
    await step("open Army Act s.69 at its page", async () => { await search(page, "s.69 Army Act"); await openFirstHit(page); return await page.inputValue("#pageinput"); });
    await step("C copies legal citation", async () => { await page.getByRole("button", { name: /Copy citation/ }).click(); await page.waitForTimeout(400); return await page.evaluate(() => navigator.clipboard.readText()); });
    await step("Shift+C copies internal reference and permalink", async () => { await page.getByRole("button", { name: /Internal ref/ }).click(); await page.waitForTimeout(400); const c = await page.evaluate(() => navigator.clipboard.readText()); permalink = (c.match(/https?:\/\/\S+|\/cite\/\S+/) || [null])[0]; return c; });
    await step("permalink opens exact copy and page", async () => { if (!permalink) return "no permalink found in clipboard"; await page.goto(permalink.replace(/^https?:\/\/[^/]+/, "")); await page.locator(".pagewrap canvas").first().waitFor({ timeout: 20000 }); await shot(page, "permalink"); return { url: page.url(), page: await page.inputValue("#pageinput"), dochead: await text(page, ".dochead", 200) }; });
    await step("reload keeps document and page", async () => { await page.reload(); await page.locator(".pagewrap canvas").first().waitFor({ timeout: 20000 }); return { url: page.url(), page: await page.inputValue("#pageinput") }; });
    await ctx.close(); }

  // ---------------------------------------------------------------- J06 statutes, amendments, temporal applicability
  journey("J06", "Statutory provisions, amendments and temporal applicability");
  if (want("J06")) { const { ctx, page } = await newPage(browser);
    await login(page, "user");
    await step("Statutes workspace", async () => { await page.goto("/s"); await page.waitForTimeout(1500); await shot(page, "statutes-home"); return await text(page, "main", 900); });
    await step("Army Act s.75 (omitted 1992)", async () => { await page.goto("/s/act-army-1950/75"); await page.locator(".dochead").first().waitFor({ timeout: 15000 }); await page.waitForTimeout(1500); await shot(page, "army-act-s75"); return { head: await text(page, ".dochead", 300), a4: await text(page, "#a4strip", 600).catch(() => "no #a4strip"), asOfDisabled: await page.locator("#asof").isDisabled().catch(() => "no #asof") }; });
    await step("Army Act s.127 (omitted 1992)", async () => { await page.goto("/s/act-army-1950/127"); await page.locator(".dochead").first().waitFor({ timeout: 15000 }); await page.waitForTimeout(1200); await shot(page, "army-act-s127"); return { head: await text(page, ".dochead", 300), a4: await text(page, "#a4strip", 400).catch(() => "no #a4strip") }; });
    await step("IPC s.302 to BNS equivalence", async () => { await page.goto("/s/act-ipc-1860/302"); await page.locator(".dochead").first().waitFor({ timeout: 15000 }); await page.waitForTimeout(1200); await shot(page, "ipc-302"); return { head: await text(page, ".dochead", 300), a4: await text(page, "#a4strip", 400).catch(() => "no #a4strip"), mentionsBns: (await page.locator("main").innerText()).includes("Bharatiya Nyaya Sanhita") }; });
    await ctx.close(); }

  // ---------------------------------------------------------------- J07 ranking, filters, pagination, sorting
  journey("J07", "Search results, filters, pagination and sorting");
  if (want("J07")) { const { ctx, page } = await newPage(browser);
    await login(page, "user");
    await step("search court martial", async () => { const ms = await search(page, "court martial"); await shot(page, "results"); return { ms, head: await text(page, "#results-head", 250), shownHits: await page.locator(".hit").count(), groups: await page.locator(".rgroup").count() }; });
    await step("facet groups", async () => (await page.locator("#facets legend").allInnerTexts()).map((s) => s.trim()));
    await step("filter type = judgment", async () => { const box = page.locator("#facets fieldset.facet", { hasText: "Document type" }).locator("label", { hasText: /Judgment/i }).first(); await box.click(); await page.waitForFunction(() => !document.querySelector("#results-list.dim")); await page.waitForTimeout(400); await shot(page, "filtered-judgment"); return await text(page, "#results-head", 250); });
    await step("year range 2020-2026", async () => { await page.fill("#yf", "2020"); await page.fill("#yt", "2026"); await page.locator("#facets button", { hasText: "Apply" }).last().click(); await page.waitForFunction(() => !document.querySelector("#results-list.dim")); await page.waitForTimeout(400); await shot(page, "filtered-years"); return { head: await text(page, "#results-head", 250), url: page.url() }; });
    await step("pagination or load-more control", async () => ({ more: await page.locator("button", { hasText: /more|next page|load/i }).count(), pager: await page.locator("[aria-label*=agination], nav.pager").count() }));
    await step("sort control", async () => ({ sortControls: await page.locator("select, [aria-label*=ort], button", { hasText: /sort|newest|relevance|date/i }).count() }));
    await step("end of results list", async () => { await page.locator("#results-list").evaluate((e) => e.scrollTo(0, e.scrollHeight)); await page.waitForTimeout(400); await shot(page, "results-end"); return await page.locator("#results-list").evaluate((e) => e.lastElementChild?.innerText?.slice(0, 300)); });
    await step("deep link restores filters", async () => { const u = page.url(); await page.goto(u); await page.waitForTimeout(1500); return { url: u, head: await text(page, "#results-head", 200) }; });
    await ctx.close(); }

  // ---------------------------------------------------------------- J08 misspelling, ambiguity, empty, parser error
  journey("J08", "Misspellings, ambiguous and zero-result queries");
  if (want("J08")) { const { ctx, page } = await newPage(browser);
    await login(page, "user");
    for (const [q, slug] of [["court marshal", "misspelling"], ["Rule 22 Rules", "ambiguous"], ["xqzvbn plorktastic", "zero-result"], ["\"court martial NEAR/5", "parser-error"], ["section 302 IPC", "ipc-abbrev"]])
      await step(`query ${q}`, async () => { const ms = await search(page, q); await shot(page, slug); return { ms, chips: await page.locator(".qchip").allInnerTexts(), head: await text(page, "#results-head", 200), body: await text(page, "#results-list", 300) }; });
    await step("parser error: run as words", async () => { await search(page, "\"court martial NEAR/5"); const b = page.locator("#results-list button").first(); if (!(await b.count())) return "no action button"; const label = await b.innerText(); await b.click(); await page.waitForTimeout(800); return { button: label, head: await text(page, "#results-head", 200) }; });
    await ctx.close(); }

  // ---------------------------------------------------------------- J09 Commander view and theme
  journey("J09", "Commander view and dark theme");
  if (want("J09")) { const { ctx, page } = await newPage(browser);
    await login(page, "user");
    await step("Commander view search", async () => { await page.click("#view-commander"); await search(page, "summary of evidence"); await shot(page, "commander-results"); return { facets: (await page.locator("#facets legend").allInnerTexts()), hits: await page.locator(".hit").count() }; });
    await step("Commander document", async () => { await openFirstHit(page); await shot(page, "commander-document"); return await text(page, ".dochead", 300); });
    await step("dark theme", async () => { await page.click("#view-practitioner"); await page.locator("#usermenu button").first().click(); await page.getByRole("menuitem", { name: /theme/i }).click(); await search(page, "disability pension"); await openFirstHit(page); await shot(page, "dark-document"); return "dark theme applied"; });
    await ctx.close(); }

  // ---------------------------------------------------------------- J10 desktop layouts
  journey("J10", "Desktop layouts 1366x768, 1920x1080, 2560x1440");
  if (want("J10")) for (const vp of [{ width: 1366, height: 768 }, { width: 1920, height: 1080 }, { width: 2560, height: 1440 }]) {
    const { ctx, page } = await newPage(browser, vp);
    await login(page, "user");
    await step(`${vp.width} results`, async () => { await search(page, "disability pension invalided"); await shot(page, `${vp.width}-results`); return await page.evaluate(() => ({ overflowX: document.documentElement.scrollWidth > innerWidth, resultsW: document.querySelector("#results-list")?.getBoundingClientRect().width | 0, hitsVisible: [...document.querySelectorAll(".hit")].filter((e) => { const r = e.getBoundingClientRect(); return r.top >= 0 && r.bottom <= innerHeight; }).length })); });
    await step(`${vp.width} document`, async () => { await openFirstHit(page); await shot(page, `${vp.width}-document`); return await page.evaluate(() => { const d = document.querySelector("#docpane")?.getBoundingClientRect(); const c = document.querySelector(".pagewrap canvas")?.getBoundingClientRect(); return { overflowX: document.documentElement.scrollWidth > innerWidth, docpaneW: d?.width | 0, pageCanvasW: c?.width | 0, viewportW: innerWidth }; }); });
    await step(`${vp.width} a11y basics`, () => a11y(page));
    await ctx.close();
  }

  // ---------------------------------------------------------------- J11 access control (read-only probes on BASE)
  journey("J11", "Access control and unauthorised access");
  if (want("J11")) { const { ctx, page } = await newPage(browser);
    const anon = ctx.request;
    for (const u of ["/api/session", "/api/search?q=army", "/api/documents/act-army-1950", "/api/documents/act-army-1950/text", "/api/statutes", "/api/admin/overview", "/api/v2/documents/act-army-1950/pdf-meta", "/api/cite?doc=act-army-1950&sha=e47a4265813e&page=25"])
      await step(`anonymous GET ${u}`, () => api(anon, "GET", BASE + u));
    await step("path traversal on document id", () => api(anon, "GET", BASE + "/api/documents/..%2f..%2fSITE_CONFIG.json"));
    await login(page, "user");
    await step("user GET /api/admin/overview", () => api(ctx.request, "GET", BASE + "/api/admin/overview"));
    await step("user opens /admin in the UI", async () => { await page.goto("/admin"); await page.waitForTimeout(800); await shot(page, "user-admin-forbidden"); return await text(page, "main", 300); });
    await step("user POST withdraw (with Origin, no CSRF token)", () => api(ctx.request, "POST", BASE + "/api/admin/withdraw", { headers: { Origin: BASE, "Content-Type": "application/json" }, data: { doc_id: "x", reason: "probe" } }));
    await step("Range beyond file on protected original", async () => { const meta = await api(ctx.request, "GET", BASE + "/api/v2/documents/act-army-1950/pdf-meta"); return { meta: meta.status, metaBody: meta.body }; });
    await ctx.close(); }

  // ---------------------------------------------------------------- J12 Administration (audit instance)
  journey("J12", "Administrator functions", AUDIT);
  if (want("J12")) { const { ctx, page } = await newPage(browser, undefined, AUDIT);
    await login(page, "admin");
    await step("admin workspace links", async () => (await page.locator("#workspaces a").allInnerTexts()).map((s) => s.trim()));
    await step("Administration overview", async () => { await page.getByRole("link", { name: "Administration" }).click(); await page.locator(".cards").waitFor(); await shot(page, "overview", true); return await text(page, "main", 1200); });
    await step("admin POST withdraw with wrong Origin", () => api(ctx.request, "POST", AUDIT + "/api/admin/withdraw", { headers: { Origin: "http://evil.example", "Content-Type": "application/json" }, data: { doc_id: WITHDRAW_DOC, reason: "probe" } }));
    await step("admin POST withdraw without CSRF token", () => api(ctx.request, "POST", AUDIT + "/api/admin/withdraw", { headers: { Origin: AUDIT, "Content-Type": "application/json" }, data: { doc_id: WITHDRAW_DOC, reason: "probe" } }));
    await ctx.close(); }

  // ---------------------------------------------------------------- J13 withdrawal enforcement (audit instance)
  journey("J13", "Document withdrawal and enforcement across access routes", AUDIT);
  if (want("J13")) { const admin = await newPage(browser, undefined, AUDIT); const user = await newPage(browser, undefined, AUDIT);
    await login(user.page, "user"); await login(admin.page, "admin");
    let permalink = null, copy = null;
    await step("user opens the document before withdrawal", async () => { await search(user.page, "Ranjit Thakur"); const ids = await user.page.locator(".rgroup").evaluateAll((els) => els.map((e) => e.dataset.doc)); await user.page.goto(`/d/${WITHDRAW_DOC}`); await user.page.locator(".pagewrap canvas").first().waitFor({ timeout: 20000 }); await user.page.getByRole("button", { name: /Internal ref/ }).click(); await user.page.waitForTimeout(300); const c = await user.page.evaluate(() => navigator.clipboard.readText()); permalink = (c.match(/\/cite\/\S+/) || [null])[0]; // Correction (Codex PR #64 review): the copy hash is taken from the full metadata JSON (not a truncated body) and
      // cross-checked against the permalink, so the /api/cite probe below sends a real hash.
      const d = await (await user.ctx.request.get(AUDIT + `/api/documents/${WITHDRAW_DOC}`)).json(); copy = d.copy.sha256.slice(0, 12);
      const fromLink = permalink ? permalink.split("/")[4] : null; await shot(user.page, "before-withdrawal-viewer");
      return { searchRank: ids.indexOf(WITHDRAW_DOC) + 1, permalink, copy12: copy, permalinkCopy12: fromLink, copiesAgree: copy === fromLink }; });
    const citeState = async () => { const r = await user.ctx.request.get(AUDIT + `/api/cite?doc=${WITHDRAW_DOC}&sha=${copy}&page=1`); let j = {}; try { j = await r.json(); } catch { /* none */ } return { status: r.status(), state: j.state ?? null, doc_id: j.doc_id ?? null, page: j.page ?? null }; };
    await step("CONTROL+ before withdrawal: /api/cite with the real copy hash", citeState);
    await step("CONTROL+ before withdrawal: document and pdf-meta", async () => ({ document: (await api(user.ctx.request, "GET", AUDIT + `/api/documents/${WITHDRAW_DOC}`)).status, pdfMeta: (await api(user.ctx.request, "GET", AUDIT + `/api/v2/documents/${WITHDRAW_DOC}/pdf-meta`)).status }));
    await step("CONTROL- before withdrawal: /api/cite with a malformed hash", async () => { const r = await user.ctx.request.get(AUDIT + `/api/cite?doc=${WITHDRAW_DOC}&sha=undefined&page=1`); let j = {}; try { j = await r.json(); } catch { /* none */ } return { status: r.status(), state: j.state ?? null }; });
    await step("withdraw via the Admin UI while searches run", async () => {
      await admin.page.goto("/admin"); await admin.page.locator("#withdraw-form").waitFor();
      await admin.page.fill("#wd-doc", WITHDRAW_DOC); await admin.page.fill("#wd-reason", "C14 walkthrough audit: enforcement test on an isolated database copy");
      await admin.page.locator("#withdraw-form button[type=submit]").click(); await admin.page.locator("dialog[open]").waitFor(); await shot(admin.page, "confirm-dialog");
      const lat = []; const load = (async () => { for (let i = 0; i < 20; i++) { const t = Date.now(); await user.ctx.request.get(AUDIT + "/api/search?q=court%20martial%20pension"); lat.push(Date.now() - t); } })();
      const t = Date.now(); await admin.page.locator("dialog[open] .btn-primary").click(); await admin.page.waitForTimeout(800); const wms = Date.now() - t; await load;
      await shot(admin.page, "after-withdrawal", true);
      return { withdrawClickToRefreshMs: wms, concurrentSearchMs: { n: lat.length, max: Math.max(...lat), median: lat.sort((a, b) => a - b)[lat.length >> 1] }, toast: await text(admin.page, "#toast", 120).catch(() => "") };
    });
    await step("open viewer after withdrawal", async () => { await user.page.locator("#viewer").click({ position: { x: 30, y: 30 } }).catch(() => {}); await user.page.keyboard.press("PageDown"); await user.page.waitForTimeout(2500); await shot(user.page, "open-viewer-after"); return await text(user.page, "#docpane", 300); });
    await step("search no longer lists it", async () => { await user.page.goto("/r"); await search(user.page, "Ranjit Thakur"); const ids = await user.page.locator(".rgroup").evaluateAll((els) => els.map((e) => e.dataset.doc)); return { present: ids.includes(WITHDRAW_DOC) }; });
    await step("deep link", async () => { await user.page.goto(`/d/${WITHDRAW_DOC}`); await user.page.waitForTimeout(1500); await shot(user.page, "deep-link"); return await text(user.page, "main", 300); });
    await step("citation permalink", async () => { if (!permalink) return "no permalink captured"; await user.page.goto(permalink); await user.page.waitForTimeout(1500); await shot(user.page, "permalink"); return await text(user.page, "main", 300); });
    for (const u of [`/api/documents/${WITHDRAW_DOC}`, `/api/documents/${WITHDRAW_DOC}/text`, `/api/documents/${WITHDRAW_DOC}/citation`, `/api/v2/documents/${WITHDRAW_DOC}/pdf-meta`])
      await step(`user GET ${u}`, () => api(user.ctx.request, "GET", AUDIT + u));
    await step("after withdrawal: /api/cite with the same real copy hash", citeState);
    await step("admin still sees it in search?", async () => { const r = await api(admin.ctx.request, "GET", AUDIT + "/api/search?q=Ranjit%20Thakur"); return { status: r.status, mentions: r.body.includes(WITHDRAW_DOC) }; });
    await step("undo withdrawal available in UI", async () => ({ restoreControls: await admin.page.locator("button", { hasText: /restore|reinstate|undo/i }).count() }));
    await admin.ctx.close(); await user.ctx.close(); }

  // ---------------------------------------------------------------- J14 lockout (audit instance)
  journey("J14", "Account lockout", AUDIT);
  if (want("J14")) { const { ctx, page } = await newPage(browser, undefined, AUDIT);
    await step("five wrong passwords then the right one", async () => { const codes = []; for (let i = 0; i < 5; i++) codes.push((await api(ctx.request, "POST", AUDIT + "/api/login", { headers: { Origin: AUDIT, "Content-Type": "application/json" }, data: { username: "user", password: "wrong-" + i } })).status); const ok = await api(ctx.request, "POST", AUDIT + "/api/login", { headers: { Origin: AUDIT, "Content-Type": "application/json" }, data: { username: "user", password: PW } }); return { wrong: codes, correctAfterLock: ok.status, message: ok.body }; });
    await step("unknown user gives the same message", async () => (await api(ctx.request, "POST", AUDIT + "/api/login", { headers: { Origin: AUDIT, "Content-Type": "application/json" }, data: { username: "no-such-user", password: "x" } })).body);
    await step("locked account in the UI", async () => { await page.goto("/"); await page.fill("#username", "user"); await page.fill("#password", PW); await page.click("form.login button[type=submit]"); await page.waitForTimeout(800); await shot(page, "locked"); return await text(page, "main", 300); });
    await ctx.close(); }

  // ---------------------------------------------------------------- J15 service loss and recovery (audit instance)
  journey("J15", "Error handling and service recovery", AUDIT);
  if (want("J15") && process.env.B1_STOP_AUDIT && process.env.B1_START_AUDIT) {
    const { ctx, page } = await newPage(browser, undefined, AUDIT);
    await login(page, "admin");
    await step("document open before outage", async () => { await search(page, "court martial"); await openFirstHit(page); return "open"; });
    await step("stop service", async () => { execSync(process.env.B1_STOP_AUDIT, { stdio: "ignore", shell: "powershell.exe" }); await page.waitForTimeout(1500); await search(page, "pension").catch(() => {}); await page.waitForTimeout(3000); await shot(page, "outage"); return { degraded: await text(page, "#degraded", 200).catch(() => "(hidden)"), main: await text(page, "main", 200) }; });
    await step("restart service and wait for recovery", async () => { const t = Date.now(); execSync(process.env.B1_START_AUDIT, { stdio: "ignore", shell: "powershell.exe" }); for (let i = 0; i < 240; i++) { await page.waitForTimeout(250); if (!(await page.locator("main").innerText().catch(() => "Connection to the server lost")).includes("Connection to the server lost")) break; } await page.waitForTimeout(1500); await shot(page, "recovered"); return { recoveredWithinMs: Date.now() - t, signInShown: await page.locator("#username").isVisible().catch(() => false), main: await text(page, "main", 200) }; });
    await ctx.close();
  } else obs("skipped", "B1_STOP_AUDIT/B1_START_AUDIT not set");

  await browser.close();
  run.finished = new Date().toISOString();
  run.journeys = run.journeys.filter((j) => want(j.id));
  fs.writeFileSync(path.join(OUT, ONLY.length ? `walkthrough_observations_${ONLY.join("_")}.json` : "walkthrough_observations.json"), JSON.stringify(run, null, 1));
  console.log(`${run.journeys.length} journeys, ${run.journeys.reduce((n, j) => n + j.screenshots.length, 0)} screenshots, ${run.journeys.reduce((n, j) => n + j.steps.filter((s) => s.error).length, 0)} step errors`);
})();
