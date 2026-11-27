// C15 WP5/WP6/WP7 journeys on the real offline sample: Commander workspace task areas, Document Studio (create, edit,
// version, cite, export), owner isolation, withdrawal of a cited source, and result density. Evidence screenshots
// (JPEG q70, DSF 1) are written to app/b1/evidence/c15_workspace/.
const path = require("path");
const fs = require("fs");
const { test, expect } = require("playwright/test");
const { login, search } = require("./helpers.cjs");

const OUT = path.resolve(__dirname, "..", "evidence", "c15_workspace");
fs.mkdirSync(OUT, { recursive: true });
async function evidence(page, name) { await page.waitForTimeout(300); await page.screenshot({ path: path.join(OUT, name + ".jpg"), type: "jpeg", quality: 70 }); }
test.use({ deviceScaleFactor: 1 });

async function apiPost(page, url, data) {
  const origin = new URL(page.url()).origin;
  const csrf = (await (await page.request.get("/api/session")).json()).csrf;
  return page.request.post(url, { headers: { "X-CSRF-Token": csrf, Origin: origin }, data });
}

const DOMAINS = ["disciplinary", "court-of-inquiry", "summary-of-evidence", "administrative-action", "service-pension", "forms"];

test("W-01 Commander workspace: every task area shows held provisions, safeguards, forms and questions, labelled as research aids", async ({ page }) => {
  await login(page);
  await page.click("#view-commander");
  await page.locator("#commander-workspace-link").click();
  await expect(page).toHaveURL(/\/c$/);
  await expect(page.locator(".ws-card")).toHaveCount(6);
  await expect(page.locator(".ws-label")).toContainText("not legal advice");
  await evidence(page, "w01-commander-areas-1920");
  for (const id of DOMAINS) {
    await page.goto(`/c/${id}`);
    await expect(page.locator(".ws-head h1")).toBeVisible();
    await expect(page.locator(".ws-label")).toContainText("Candidate / research aid — not legal advice");
    await expect(page.locator('[data-sect="questions"] .ws-questions li').first()).toBeVisible();
    const found = page.locator(".ws-prov:not(.unavailable)");
    expect(await found.count()).toBeGreaterThan(0);
    await expect(found.first().locator(".ws-excerpt")).toBeVisible();     // printed text from the held copy
    await expect(page.locator('[data-sect="forms"]')).toContainText("not a form registry", { ignoreCase: true });
    await evidence(page, `w01-commander-${id}-1920`);
  }
  // a provision link opens the Statutes view of that provision
  await page.goto("/c/disciplinary");
  await page.locator('.ws-prov[data-provision="Section 80"] .ws-prov-head a').click();
  await expect(page).toHaveURL(/\/s\/act-army-1950\/80$/);
  await page.click("#view-practitioner");
});

test("W-02 Studio: create, edit, save versions, view and restore an earlier version, export HTML and Markdown", async ({ page }) => {
  await login(page);
  await page.goto("/studio");
  await page.fill("#new-doc-title", "W-02 memo");
  await page.selectOption("#new-doc-template", "memo");
  await page.getByRole("button", { name: "Create" }).click();
  await expect(page).toHaveURL(/\/studio\/sd-/);
  await expect(page.locator(".ws-block")).toHaveCount(5);                  // generic memo skeleton
  await expect(page.locator(".ws-origin").first()).toHaveText("Template heading");
  await page.getByRole("button", { name: "Text", exact: true }).click();
  await page.locator(".ws-block").last().locator("textarea").fill("Facts noted by the author on 27 Nov.");
  await expect(page.locator(".ws-block").last().locator(".ws-origin")).toHaveText("You");
  await page.selectOption("#studio-state", "in_review");
  await page.locator("#studio-save").click();
  await expect(page.locator("#studio-versions li")).toHaveCount(2);
  await expect(page.locator(".ws-label")).toContainText("not legally approved");
  await evidence(page, "w02-studio-editor-1920");
  // earlier version: read-only view, then restore as a new version
  await page.locator('#studio-versions li[data-version="1"] a').click();
  await expect(page.locator("#studio-status")).toContainText("Viewing version 1 of 2");
  await expect(page.locator(".ws-block textarea, .ws-block input").first()).toBeDisabled();
  await page.getByRole("button", { name: "Restore version 1 as a new version" }).click();
  await expect(page.locator("#studio-versions li")).toHaveCount(3);
  // export
  for (const [sel, ext] of [["#export-html", "html"], ["#export-md", "md"]]) {
    const [dl] = await Promise.all([page.waitForEvent("download"), page.locator(sel).click()]);
    const file = await dl.path();
    const text = fs.readFileSync(file, "utf-8");
    expect(dl.suggestedFilename()).toMatch(new RegExp(`\\.${ext}$`));
    expect(text).toContain("Not legally approved");
    expect(text).toContain("W-02 memo");
  }
});

test("W-03 Reader: a copy-pinned citation and quotation of s.69 Army Act go into a new Studio document", async ({ page }) => {
  await login(page);
  await search(page, "s.69 Army Act");
  await page.locator(".hit").first().click();
  await expect(page.locator(".pagewrap canvas").first()).toBeVisible();
  await page.locator("#add-to-studio").click();
  await expect(page.locator("dialog[open]")).toContainText("Copy-pinned citation");
  await page.fill("#studio-new-title", "W-03 s.69 research");
  await expect(page.locator("#studio-quote")).toBeChecked();
  await page.locator("dialog[open] .btn-primary").click();
  await expect(page.locator("#toast")).toContainText("Added to Studio");
  await page.goto("/studio");
  await page.locator("#studio-docs a", { hasText: "W-03 s.69 research" }).click();
  const q = page.locator('.ws-block.corpus[data-type="quote"]');
  await expect(q.locator(".ws-origin")).toHaveText("From the library");
  await expect(q.locator(".ws-excerpt")).toContainText("Civil offences");
  await expect(q.locator(".ws-cite")).toContainText("The Army Act, 1950");
  await expect(q).toContainText("Open cited page");
  await evidence(page, "w03-studio-quote-from-reader-1920");
});

test("W-04 Owner isolation: another user cannot open a Studio document through the UI or the API", async ({ page, browser }) => {
  await login(page);
  const r = await apiPost(page, "/api/studio/documents", { title: "W-04 private", template: "blank" });
  expect(r.status()).toBe(201);
  const id = (await r.json()).id;
  const other = await browser.newPage();
  await login(other, "admin");                                     // Admin capacity gives no Studio access
  await other.goto(`/studio/${id}`);
  await expect(other.locator(".error-state")).toContainText("No such document in your Studio");
  expect((await other.request.get(`/api/studio/documents/${id}`)).status()).toBe(404);
  expect((await other.request.get(`/api/studio/documents/${id}/export?format=md`)).status()).toBe(404);
  await expect(other.locator("body")).not.toContainText("W-04 private");
  await evidence(other, "w04-owner-isolation-1920");
});

test("W-05 A cited source is withdrawn: the open Studio page shows 'Source no longer available' and keeps the author's text", async ({ page, browser }) => {
  const user = await browser.newPage();
  await login(user);
  const meta = await (await user.request.get("/api/v2/documents/act-navy-1957/pdf-meta")).json();
  const created = await (await apiPost(user, "/api/studio/documents", { title: "W-05 navy citation", template: "blank" })).json();
  expect((await apiPost(user, `/api/studio/documents/${created.id}/append`, { blocks: [
    { type: "text", origin: "user", text: "Author's analysis that must survive." },
    { type: "citation", doc_id: "act-navy-1957", copy: meta.copy_sha256.slice(0, 12), page: 3 }] })).status()).toBe(200);
  await user.goto(`/studio/${created.id}`);
  await expect(user.locator('.ws-block.corpus .ws-cite')).toContainText("Navy Act");
  await login(page, "admin");
  expect((await apiPost(page, "/api/admin/withdraw", { doc_id: "act-navy-1957", reason: "C15 W-05 studio citation" })).status()).toBe(200);
  try {
    await expect(user.locator(".ws-block.corpus [data-unavailable]")).toHaveText("Source no longer available in this installation.", { timeout: 30_000 });
    await expect(user.locator(".ws-block.corpus")).not.toContainText("Navy Act");
    await expect(user.locator(".ws-block textarea").first()).toHaveValue("Author's analysis that must survive.");
    await evidence(user, "w05-studio-citation-withdrawn-1920");
  } finally {
    expect((await apiPost(page, "/api/admin/reinstate", { doc_id: "act-navy-1957", reason: "C15 W-05 restore after test" })).status()).toBe(200);
  }
});

// Codex review of PR #75: with unsaved edits, a policy change refreshes library blocks in place keyed by their full
// reference, so two citations to different paragraphs of one page stay distinct and are saved unchanged.
test("W-05b citations to two paragraphs of one page survive an in-place refresh with unsaved edits", async ({ page, browser }) => {
  const user = await browser.newPage();
  await login(user);
  const meta = await (await user.request.get("/api/v2/documents/act-navy-1957/pdf-meta")).json();
  const copy = meta.copy_sha256.slice(0, 12);
  const created = await (await apiPost(user, "/api/studio/documents", { title: "W-05b two paragraphs", template: "blank" })).json();
  expect((await apiPost(user, `/api/studio/documents/${created.id}/append`, { blocks: [
    { type: "text", origin: "user", text: "Analysis." },
    { type: "citation", doc_id: "act-navy-1957", copy, page: 3, para: "10" },
    { type: "citation", doc_id: "act-navy-1957", copy, page: 3, para: "11" }] })).status()).toBe(200);
  await user.goto(`/studio/${created.id}`);
  await expect(user.locator(".ws-block.corpus")).toHaveCount(2);
  await user.locator(".ws-block textarea").first().fill("Analysis, edited and not yet saved.");
  await login(page, "admin");
  // an unrelated withdrawal changes the policy epoch; the open editor refreshes its library blocks in place
  expect((await apiPost(page, "/api/admin/withdraw", { doc_id: "ref-bprd-comparison-bns-ipc", reason: "C15 W-05b policy change" })).status()).toBe(200);
  try {
    await user.waitForTimeout(12_000);                                        // one poll interval
    await expect(user.locator(".ws-block textarea").first()).toHaveValue("Analysis, edited and not yet saved.");
    const [resp] = await Promise.all([user.waitForResponse((r) => r.url().includes(`/api/studio/documents/${created.id}/save`)), user.locator("#studio-save").click()]);
    expect(resp.status()).toBe(200);
    const saved = await (await user.request.get(`/api/studio/documents/${created.id}`)).json();
    expect(saved.blocks.filter((b) => b.type === "citation").map((b) => b.para)).toEqual(["10", "11"]);
  } finally {
    expect((await apiPost(page, "/api/admin/reinstate", { doc_id: "ref-bprd-comparison-bns-ipc", reason: "C15 W-05b restore after test" })).status()).toBe(200);
  }
});

// Codex review of PR #75: typing that starts while a policy refresh of a clean editor is in flight is kept (the dirty
// state is checked after the fetch). The refresh's document request is held until the author has typed.
test("W-05c typing during an in-flight policy refresh is not discarded", async ({ page, browser }) => {
  const user = await browser.newPage();
  await login(user);
  const created = await (await apiPost(user, "/api/studio/documents", { title: "W-05c in-flight refresh", template: "blank" })).json();
  expect((await apiPost(user, `/api/studio/documents/${created.id}/append`, { blocks: [{ type: "text", origin: "user", text: "Saved text." }] })).status()).toBe(200);
  await user.goto(`/studio/${created.id}`);
  const box = user.locator(".ws-block textarea").first();
  await expect(box).toHaveValue("Saved text.");
  let release; const gate = new Promise((r) => { release = r; });
  await user.route((u) => u.pathname === `/api/studio/documents/${created.id}`, async (route) => { await gate; await route.continue(); });
  await login(page, "admin");
  expect((await apiPost(page, "/api/admin/withdraw", { doc_id: "ref-bprd-comparison-bns-ipc", reason: "C15 W-05c policy change" })).status()).toBe(200);
  try {
    await user.waitForRequest((r) => new URL(r.url()).pathname === `/api/studio/documents/${created.id}`, { timeout: 25_000 });
    await box.fill("Typed while the refresh was in flight.");
    release();
    await user.waitForTimeout(1500);
    await expect(user.locator(".ws-block textarea").first()).toHaveValue("Typed while the refresh was in flight.");
    await expect(user.locator("#studio-status")).toContainText("unsaved changes");
  } finally {
    release();
    expect((await apiPost(page, "/api/admin/reinstate", { doc_id: "ref-bprd-comparison-bns-ipc", reason: "C15 W-05c restore after test" })).status()).toBe(200);
  }
});

test("W-06 Commander questions go into a Studio document as automated suggestions", async ({ page }) => {
  await login(page);
  await page.goto("/c/court-of-inquiry");
  await page.getByRole("button", { name: "Add these questions to a Studio document" }).click();
  await page.fill("#studio-new-title", "W-06 CoI questions");
  await page.locator("dialog[open] .btn-primary").click();
  await expect(page.locator("#toast")).toContainText("Added to Studio");
  await page.goto("/studio");
  await page.locator("#studio-docs a", { hasText: "W-06 CoI questions" }).click();
  const qs = page.locator('.ws-block[data-type="question"]');
  await expect(qs.first()).toBeVisible();                                  // count() does not wait for the document to render
  expect(await qs.count()).toBeGreaterThan(2);
  await expect(qs.first().locator(".ws-origin")).toHaveText("Automated suggestion");
  await qs.first().locator("textarea").fill("Edited by the author.");
  await expect(qs.first().locator(".ws-origin")).toHaveText("You");          // an edited suggestion becomes the author's text
  await evidence(page, "w06-commander-questions-in-studio-1920");
});

for (const [vp, min] of [[{ width: 1366, height: 768 }, 3], [{ width: 1920, height: 1080 }, 5], [{ width: 2560, height: 1440 }, 7]]) {
  test(`W-07 result density at ${vp.width}x${vp.height}: at least ${min} results fully visible`, async ({ page }) => {
    await page.setViewportSize(vp);
    await login(page);
    await search(page, "disability pension invalided");
    await page.waitForTimeout(300);
    const n = await page.evaluate(() => [...document.querySelectorAll(".hit")].filter((e) => { const r = e.getBoundingClientRect(); return r.top >= 0 && r.bottom <= innerHeight && r.width > 0; }).length);
    fs.writeFileSync(path.join(OUT, `density-${vp.width}.json`), JSON.stringify({ viewport: `${vp.width}x${vp.height}`, hitsFullyVisible: n }));
    expect(n).toBeGreaterThanOrEqual(min);
    expect(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)).toBe(false);
    await evidence(page, `w07-density-${vp.width}`);
  });
}

// C15 integration: Commander provisions open the SAME legal knowledge graph and research assessment as the
// Practitioner view (no separate knowledge or reasoning path).
test("C15-INT-01 a Commander provision opens the shared legal knowledge graph", async ({ page }) => {
  await login(page);
  await page.goto("/c/disciplinary");
  const link = page.locator(".ws-prov a.ws-graph").first();
  await expect(link).toBeVisible();
  const href = await link.getAttribute("href");
  expect(href).toMatch(/^\/g\?doc=[^&]+&section=[^&]+$/);
  await link.click();
  await expect(page).toHaveURL(/\/g\?doc=/);
  await expect(page.locator("#g-body")).toBeVisible();
  await expect(page.locator("#g-body table.data, #g-body .notice").first()).toBeVisible({ timeout: 15_000 });
  await expect(page.locator("#g-body")).not.toContainText("later milestone");
});
