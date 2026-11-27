// C14 S2 acceptance on the real 290-document sample: the semantics of audit journeys J13 (withdrawal enforcement,
// with the corrected /api/cite probe and positive/negative controls), J13b (open viewer, deep link) and J14 (lockout
// expiry, attempts during a lock, Admin unlock). Runs against a DISPOSABLE instance in test mode (lock shortened by
// Mimamsa:Test:LockSeconds). Observations are written to s2_acceptance.json; screenshots next to it.
//   B1_URL=http://127.0.0.1:5423 B1_PASSWORD=<admin/user password> B1_LOCK_SECONDS=20 node acceptance_s2.cjs <out-dir>
const fs = require("fs"), path = require("path");
const { chromium } = require("playwright");
const BASE = process.env.B1_URL, PW = process.env.B1_PASSWORD, LOCK = +(process.env.B1_LOCK_SECONDS || 20);
const OUT = path.resolve(process.argv[2] || "."); fs.mkdirSync(OUT, { recursive: true });
const DOC = "sc-1987-ranjit-thakur-1987insc285", DOC2 = "sc-1991-ex-havildar-rat-an-singh-1991insc300";
const res = { base: BASE, started: new Date().toISOString(), checks: [] };
const check = (id, what, ok, observed) => { res.checks.push({ id, what, pass: !!ok, observed }); console.log(`${ok ? "PASS" : "FAIL"} ${id} ${what}`); };

(async () => {
  const b = await chromium.launch();
  const mk = async () => { const c = await b.newContext({ viewport: { width: 1920, height: 1080 }, baseURL: BASE, permissions: ["clipboard-read", "clipboard-write"] }); return { c, p: await c.newPage() }; };
  const login = async (p, u, pass = PW) => { await p.goto("/"); await p.fill("#username", u); await p.fill("#password", pass); await p.click("form.login button[type=submit]"); await p.locator("#research").waitFor(); };
  const shot = (p, n) => p.screenshot({ path: path.join(OUT, n), type: "jpeg", quality: 70 });
  const cite = async (ctx, doc, sha) => { const r = await ctx.request.get(`/api/cite?doc=${doc}&sha=${sha}&page=1`); return { status: r.status(), state: (await r.json()).state }; };
  const u = await mk(), a = await mk(); await login(u.p, "user"); await login(a.p, "admin");
  const csrf = (await (await a.c.request.get("/api/session")).json()).csrf;

  // ---- J13: positive and negative controls, then enforcement on every route
  const meta = await (await u.c.request.get(`/api/documents/${DOC}`)).json(); const sha12 = meta.copy.sha256.slice(0, 12);
  check("J13-C+", "/api/cite with the real copy hash before withdrawal is ELIGIBLE", (await cite(u.c, DOC, sha12)).state === "CITED_COPY_ELIGIBLE", await cite(u.c, DOC, sha12));
  check("J13-C-", "/api/cite with a malformed hash is UNAVAILABLE even before withdrawal (negative control)", (await cite(u.c, DOC, "undefined")).state === "CITED_COPY_UNAVAILABLE", await cite(u.c, DOC, "undefined"));
  await u.p.goto(`/d/${DOC}?p=1`); await u.p.locator(".pagewrap canvas").first().waitFor({ timeout: 20000 });
  await shot(u.p, "s2-j13-before.jpg");
  await a.p.goto("/admin"); await a.p.locator("#withdraw-form").waitFor();
  await a.p.fill("#wd-doc", DOC); await a.p.fill("#wd-reason", "C14 S2 acceptance (disposable database)");
  await a.p.getByRole("button", { name: "Withdraw…" }).click(); await a.p.locator("dialog[open]").waitFor();
  const dialogText = await a.p.locator("dialog[open]").innerText();
  check("J13-D", "dialog states what is covered and how open viewers are treated", dialogText.includes("Pages already on a reader's screen are cleared") && !dialogText.includes("Open viewers are cut off"), dialogText.replace(/\s+/g, " ").slice(0, 400));
  await shot(a.p, "s2-j13-dialog.jpg");
  const t0 = Date.now(); await a.p.locator("dialog[open] .btn-primary").click();
  // J13b: the reader does nothing; the open viewer is cleared by the epoch poll
  let cleared = false;
  try { await u.p.locator(".docempty[data-invalidated]").waitFor({ timeout: 20000 }); cleared = true; } catch { /* recorded below */ }
  const clearedMs = Date.now() - t0;
  check("J13b-V", "an open viewer is cleared without reader action (page, header and evidence gone)", cleared && (await u.p.locator(".pagewrap canvas").count()) === 0 && (await u.p.locator(".dochead").count()) === 0, { clearedWithinMs: clearedMs });
  await shot(u.p, "s2-j13b-viewer-cleared.jpg");
  check("J13-CITE", "/api/cite with the same real hash after withdrawal is UNAVAILABLE", (await cite(u.c, DOC, sha12)).state === "CITED_COPY_UNAVAILABLE", await cite(u.c, DOC, sha12));
  const routes = {};
  for (const r of [`/api/documents/${DOC}`, `/api/documents/${DOC}/text`, `/api/v2/documents/${DOC}/pdf-meta`]) routes[r] = (await u.c.request.get(r)).status();
  check("J13-API", "document, text and pdf-meta refuse the withdrawn document", Object.values(routes).every((s) => s === 404), routes);
  const sr = await (await u.c.request.get("/api/search?q=Ranjit%20Thakur")).text();
  check("J13-S", "search no longer lists it", !sr.includes(DOC), null);
  await u.p.goto(`/d/${DOC}?p=1`); await u.p.waitForTimeout(1500);
  check("J13b-DL", "a deep link shows the notice", (await u.p.locator(".docempty").innerText()).includes("This document is not available in this installation."), null);
  await shot(u.p, "s2-j13b-deep-link.jpg");

  // ---- J13b second document: the reader acts (goes to another page) and the tab is cleared at once
  await u.p.goto(`/d/${DOC2}?p=1`); await u.p.locator(".pagewrap canvas").first().waitFor({ timeout: 20000 });
  const w2 = await a.c.request.post("/api/admin/withdraw", { headers: { "X-CSRF-Token": csrf }, data: { doc_id: DOC2, reason: "C14 S2 acceptance, reader action" } });
  const t1 = Date.now(); await u.p.fill("#pageinput", "3"); await u.p.press("#pageinput", "Enter");
  let cleared2 = false; try { await u.p.locator(".docempty[data-invalidated]").waitFor({ timeout: 12000 }); cleared2 = true; } catch { /* recorded */ }
  check("J13b-ACT", "the reader's next action clears the withdrawn document", w2.status() === 200 && cleared2, { clearedWithinMs: Date.now() - t1 });

  // ---- reinstatement with renewed verification
  const ri = await a.c.request.post("/api/admin/reinstate", { headers: { "X-CSRF-Token": csrf }, data: { doc_id: DOC, reason: "C14 S2 acceptance: reinstate" } });
  const rij = await ri.json();
  check("RI", "reinstatement re-verifies and restores the document", ri.status() === 200 && (await u.c.request.get(`/api/documents/${DOC}`)).status() === 200 && (await cite(u.c, DOC, sha12)).state === "CITED_COPY_ELIGIBLE", rij);

  // ---- J14: lockout ends LOCK seconds after the 5th failure, whatever is tried during the lock
  const anon = await b.newContext({ baseURL: BASE });
  const L = (pw) => anon.request.post("/api/login", { data: { username: "user", password: pw } }).then((r) => r.status());
  const wrong = []; for (let i = 0; i < 5; i++) wrong.push(await L("wrong-" + i));
  const lockedAt = Date.now();
  const during = [];
  for (const at of [3000, Math.round(LOCK * 500), LOCK * 1000 - 3000]) { await new Promise((r) => setTimeout(r, Math.max(0, lockedAt + at - Date.now()))); during.push({ atMs: at, correct: await L(PW), wrong: await L("still-wrong") }); }
  await new Promise((r) => setTimeout(r, Math.max(0, lockedAt + LOCK * 1000 + 800 - Date.now())));
  const afterLock = await L(PW);
  check("J14-EXP", `the lock ends ${LOCK} s after the 5th failure despite attempts during the lock`, wrong.every((s) => s === 401) && during.every((d) => d.correct === 401) && afterLock === 200, { wrong, during, afterLockMs: Date.now() - lockedAt, afterLock });
  for (let i = 0; i < 5; i++) await L("wrong-again-" + i);
  const lockedAgain = await L(PW);
  const un = await a.c.request.post("/api/admin/unlock", { headers: { "X-CSRF-Token": csrf }, data: { username: "user", reason: "C14 S2 acceptance: unlock" } });
  check("J14-UNL", "Admin unlock with a reason ends a lock at once", lockedAgain === 401 && un.status() === 200 && (await L(PW)) === 200, { lockedAgain, unlock: un.status() });
  const audit = await (await a.c.request.get("/api/admin/audit?limit=200")).json();
  const actions = [...new Set(audit.rows.map((r) => r.action))].sort();
  check("AUD", "audit log records the events and no password text", ["lockout", "login_refused_locked", "unlock", "withdraw", "reinstate"].every((x) => actions.includes(x)) && !JSON.stringify(audit).includes("wrong-") && !JSON.stringify(audit).includes(PW), actions);
  await a.p.goto("/admin"); await a.p.locator("#audit-table").waitFor(); await shot(a.p, "s2-admin-withdrawals-accounts-audit.jpg");
  await a.p.screenshot({ path: path.join(OUT, "s2-admin-full.jpg"), type: "jpeg", quality: 70, fullPage: true });

  await b.close();
  res.finished = new Date().toISOString();
  res.summary = { pass: res.checks.filter((c) => c.pass).length, fail: res.checks.filter((c) => !c.pass).length };
  fs.writeFileSync(path.join(OUT, "s2_acceptance.json"), JSON.stringify(res, null, 1));
  console.log(JSON.stringify(res.summary));
})();
