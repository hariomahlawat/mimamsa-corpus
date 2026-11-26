// UX journeys from docs/architecture/reviews/c13-assurance/retrieval-ux.md (UX-01..UX-19) and app/design workflows
// (W-01..W-13), run on the synthetic SYN site. Each test name starts with its UX id. Where a journey has parts B1 does
// not implement, the test asserts what B1 does implement and the unimplemented part is recorded in
// docs/architecture/b1/B1_PROTOTYPE.md with status "Not implemented" (never counted as passed).
const { test, expect } = require("playwright/test");
const { login, search, shot, a11yBasics, darkPixelsUnderFirstMark } = require("./helpers.cjs");

// Tests run in file order on one worker (UX-09 withdraws the canary and therefore runs last).

const RET07 = "Can someone challenge a hearing when nobody told them the allegation beforehand?";

test("UX-01 W-01 situation words: filter by type, open operative passage, same access in Commander view", async ({ page }) => {
  await login(page);
  await search(page, RET07);
  await expect(page.locator("[data-testid=runline]")).toContainText("Lexical");
  await expect(page.locator("[data-testid=runline]")).toContainText("semantic search not part of B1");
  await page.getByLabel(/^Judgment/).check();
  await page.waitForFunction(() => !document.querySelector("#results-list.dim"));
  const types = await page.locator(".rgroup-meta > span:first-child").allTextContents();
  expect(types.length).toBeGreaterThan(0);
  expect(new Set(types)).toEqual(new Set(["Judgment"]));
  const countPractitioner = await page.locator(".results-count strong").textContent();
  await page.locator(".hit", { hasText: "written charge beforehand" }).first().click();
  await expect(page.locator("#pageinput")).toHaveValue("7");
  await expect(page.locator(".pdf-legend")).toContainText("physical page 7");
  await page.click("#view-commander");
  await expect(page.locator("body")).toHaveClass(/commander/);
  await page.waitForFunction(() => !document.querySelector("#results-list.dim"));
  await expect(page.locator(".results-count strong")).toHaveText(countPractitioner);
  await shot(page, "syn-01-commander-view.png");
  await page.click("#view-practitioner");
});

test("UX-02 W-02 identifiers first, parsed chips, restorable deep link, malformed query needs explicit choice", async ({ page, context }) => {
  await login(page);
  await search(page, "s.17 Bracken Service Act");
  await expect(page.locator(".qchip").first()).toContainText("Section 17");
  await expect(page.locator(".hit").first()).toContainText("Section 17. Authorised pause");
  await expect(page.locator(".hit", { hasText: "Section 117" })).toHaveCount(0);
  await search(page, "OA 411/2021");
  await expect(page.locator(".qchip").first()).toContainText("Case number · OA 411/2021");
  await expect(page.locator(".hit").first()).toContainText("OA 411/2021 allowed");
  await expect(page.locator(".hit", { hasText: "OA 411/2022" })).toHaveCount(0);
  await page.getByLabel(/^Judgment/).check();
  await page.waitForFunction(() => !document.querySelector("#results-list.dim"));
  const url = page.url();
  expect(url).toContain("type=judgment");
  const p2 = await context.newPage();
  await p2.goto(url);
  await expect(p2.locator("#q")).toHaveValue("OA 411/2021");
  await expect(p2.getByLabel(/^Judgment/)).toBeChecked();
  await expect(p2.locator(".hit").first()).toContainText("OA 411/2021 allowed");
  await p2.close();
  await page.getByLabel(/^Judgment/).uncheck();
  await page.waitForFunction(() => !document.querySelector("#results-list.dim"));
  await search(page, 'exact:("summary of evidence" AND (BHT OR tribunal)');
  await expect(page.locator(".error-state")).toContainText("Opening parenthesis is not closed");
  await expect(page.locator(".parse-echo .caret")).toHaveText("(");
  await expect(page.locator("#q")).toHaveValue('exact:("summary of evidence" AND (BHT OR tribunal)');
  await shot(page, "syn-02-parser-error.png");
  await page.getByRole("button", { name: "Search the words without operators" }).click();
  await expect(page.locator("[data-testid=runline]")).toContainText("words only");
  await expect(page.locator(".hit").first()).toBeVisible();
});

test("UX-03 W-03 open passage, hit navigation, legal citation and internal reference are separate", async ({ page }) => {
  await login(page);
  await search(page, "furnish OR distinguish");
  await page.locator(".hit", { hasText: "written charge beforehand" }).first().click();
  await expect(page.locator(".hitcount")).toContainText("hit 2 of 2");      // hits are in page order: p.6 quotation, p.7 operative
  await page.locator("#viewer").click();
  await page.keyboard.press("Shift+N");
  await expect(page.locator(".hitcount")).toContainText("hit 1 of 2");
  await expect(page.locator("#pageinput")).toHaveValue("6");
  await page.keyboard.press("n");
  await expect(page.locator(".hitcount")).toContainText("hit 2 of 2");
  await expect(page.locator("#pageinput")).toHaveValue("7");
  await page.keyboard.press("c");
  await expect.poll(() => page.evaluate(() => window.__mimamsaLastCopy)).toBe(
    "Vale v. Lark, 2021 BRSYN 21 (Fictional Bracken Tribunal, 15 September 2021), para 12 (metadata not verified)");
  await page.keyboard.press("Shift+C");
  await expect.poll(() => page.evaluate(() => window.__mimamsaLastCopy))
    .toMatch(/^\[syn-j-allow · copy [0-9a-f]{12} · p\.7 · R13-syn-fixture-20261125-00000002\] \/cite\//);
  await page.keyboard.press("t");
  await expect(page.locator(".textview")).toBeVisible();
  await expect(page.locator(".textview .psg.target")).toContainText("written charge beforehand");
  await expect(page.locator(".pg-divider").first()).toContainText("Page");
  await shot(page, "syn-03-text-view-page-markers.png");
});

test("UX-04 W-04 seven separate axes in order, provenance with full hash; Admin sees publication actor", async ({ page }) => {
  await login(page);
  await page.goto("/d/syn-j-allow?p=7");
  await expect(page.locator(".dochead h1")).toContainText("Vale v. Lark");
  const axes = await page.locator("details.axis .axis-name").allTextContents();
  expect(axes).toEqual(["Source integrity", "Source authenticity", "Evidence fidelity", "Legal applicability", "Legal approval", "Publication", "Dependency freshness"]);
  await expect(page.locator(".ctx")).not.toContainText("Verified ✓");
  await page.getByRole("tab", { name: "Provenance" }).click();
  await expect(page.locator(".copybox code")).toHaveText(/^[0-9a-f]{64}$/);
  await expect(page.locator(".ctx-body")).not.toContainText("site import (B1 build)");
  await page.getByRole("button", { name: /reader · User/ }).click();
  await page.getByRole("menuitem", { name: "Sign out" }).click();
  await page.fill("#username", "admin"); await page.fill("#password", "admin-password-1");
  await page.click("form.login button[type=submit]");
  await expect(page.locator("#research")).toBeVisible();
  await page.goto("/d/syn-j-allow?p=7");
  await page.getByRole("tab", { name: "Provenance" }).click();
  await expect(page.locator(".ctx-body")).toContainText("site import (B1 build)");
});

test("UX-05 W-05 candidate outcomes per proceeding, labelled, 'not evaluated' when unmeasured", async ({ page }) => {
  await login(page);
  await page.goto("/d/syn-j-allow?p=7");
  const strip = page.locator(".proceedings");
  await expect(strip).toContainText("OA 411/2021");
  await expect(strip).toContainText("OA 412/2021");
  await expect(strip.locator(".prow", { hasText: "OA 411/2021" })).toContainText("allowed");
  await expect(strip.locator(".prow", { hasText: "OA 412/2021" })).toContainText("dismissed");
  await expect(strip.locator(".chip-candidate").first()).toHaveText("Candidate");
  await expect(strip).toContainText("not evaluated");
  await strip.getByRole("button", { name: "Details" }).first().click();
  await expect(page.locator("dialog")).toContainText("AUTOMATED_CANDIDATE_NOT_VERIFIED");
  await expect(page.locator("dialog")).toContainText("not evaluated");
  await shot(page, "syn-05-candidate-outcome.png");
  await page.keyboard.press("Escape");
});

test("UX-06 W-06 statutes TOC to a rule, as-of closed with gate, temporal chain not established", async ({ page }) => {
  await login(page);
  await page.goto("/s");
  await page.getByRole("link", { name: /Bracken Hearing Rules/ }).click();
  await expect(page.locator(".toc")).toContainText("8(3)(a)");
  await page.locator(".toc a", { hasText: "8(3)(a)" }).click();
  await expect(page.locator("#asof")).toBeDisabled();
  await expect(page.locator("#asof-why")).toContainText("Temporal chain not established");
  await expect(page.locator("#asof-why")).toContainText("Legal Reviewer");
  await expect(page.locator("#pageinput")).toHaveValue("4");
  await page.locator(".toc a", { hasText: "8(3)(b)" }).click();
  await expect(page.locator("#pageinput")).toHaveValue("5");
  await shot(page, "syn-06-statute-rule-gate.png");
});

test("UX-10 W-13 closed gate explains appointment and approvals and links back to research", async ({ page }) => {
  await login(page);
  await page.getByRole("link", { name: "Assistant" }).click();
  await expect(page.locator(".gate")).toContainText("No Legal Reviewer is appointed and AUTH-LEDGER is at version 0");
  await expect(page.locator(".gate")).toContainText("never shows sample or example outputs");
  await expect(page.locator("#banner")).toContainText("Not legally verified");
  await page.getByRole("link", { name: "Return to research search" }).click();
  await expect(page).toHaveURL(/\/r$/);
});

test("UX-11 truncated copy carries an explicit warning", async ({ page }) => {
  await login(page);
  await page.goto("/d/syn-j-reject-short?p=1");
  await expect(page.locator(".dochead")).toContainText("Truncated at source");
  await expect(page.locator(".dochead")).toContainText("Missing pages are not evidence");
});

test("UX-12 citation across releases opens the cited copy and page; current edition is a separate action", async ({ page, request }) => {
  await login(page);
  const map = require(process.env.B1_SYN_MAP || require("path").join(process.env.B1_SYN_SITE, "..", "fixture_map.json"));
  const old = map.j_allow_r1_copy;
  await page.goto(`/cite/R13-syn-fixture-20261125-00000001/syn-j-allow/${old.slice(0, 12)}/6`);
  await expect(page.locator(".dochead .notice")).toContainText("This copy is not the current edition in the library.");
  await expect(page.locator(".pdf-legend")).toContainText(`copy ${old.slice(0, 12)} · physical page 6 of 6`);
  await expect(page.locator("#pageinput")).toHaveValue("6");
  await shot(page, "syn-12-cited-copy-not-current.png");
  await page.getByRole("button", { name: "Open current edition" }).click();
  await expect(page.locator(".pdf-legend")).toContainText(`copy ${map.j_allow_r2_copy.slice(0, 12)}`);
  await page.goto(`/cite/R13-syn-fixture-20261125-00000002/syn-j-allow/${"a".repeat(12)}/6`);
  await expect(page.locator("[data-cite-state]")).toHaveText("The cited copy is not available in this installation.");
});

test("ASR-E06 reload keeps the cited earlier edition: page navigation and reload never substitute the current copy", async ({ page }) => {
  await login(page);
  const map = require(process.env.B1_SYN_MAP || require("path").join(process.env.B1_SYN_SITE, "..", "fixture_map.json"));
  const old = map.j_allow_r1_copy;
  await page.goto(`/cite/R13-syn-fixture-20261125-00000001/syn-j-allow/${old.slice(0, 12)}/6`);
  await expect(page.locator(".pdf-legend")).toContainText(`copy ${old.slice(0, 12)} · physical page 6 of 6`);
  await page.locator("#pageinput").fill("5"); await page.locator("#pageinput").press("Enter");
  await expect(page.locator(".pdf-legend")).toContainText(`copy ${old.slice(0, 12)} · physical page 5 of 6`);
  expect(page.url()).toContain(`copy=${old.slice(0, 12)}`);
  await page.reload();
  await expect(page.locator(".pdf-legend")).toContainText(`copy ${old.slice(0, 12)} · physical page 5 of 6`);
  await expect(page.locator(".dochead .notice")).toContainText("This copy is not the current edition in the library.");
  await page.goto(`/d/syn-j-allow?p=2&copy=${"a".repeat(12)}`);
  await expect(page.locator("[data-cite-state]")).toHaveText("The cited copy is not available in this installation.");
  await expect(page.locator(".pagewrap")).toHaveCount(0);
});

test("Session expiry clears the previous user's research context before another user signs in", async ({ page, context }) => {
  await login(page);
  await search(page, "OA 411/2021");
  await page.locator(".hit").first().click();
  await expect(page.locator(".pagewrap canvas")).toBeVisible();
  await context.clearCookies();                                   // the session is no longer valid
  await page.fill("#q", "lanterns"); await page.press("#q", "Enter");
  await expect(page.locator("form.login")).toBeVisible();
  await expect(page.locator("form.login .err")).toContainText("session has ended");
  await page.fill("#username", "admin"); await page.fill("#password", "admin-password-1");
  await page.click("form.login button[type=submit]");
  await expect(page.locator("#research")).toBeVisible();
  await expect(page.locator("#q")).toHaveValue("");
  await expect(page.locator(".tab")).toHaveCount(0);
  await expect(page.locator(".hit")).toHaveCount(0);
  await expect(page.locator(".pagewrap")).toHaveCount(0);
  expect(await page.evaluate(() => [window.__mimamsaViewer, window.__mimamsaLastCopy])).toEqual([null, null]);
});

test("UX-13 impossible filters give a published-scope empty state with recovery; no-edge caveat", async ({ page }) => {
  await login(page);
  await search(page, "notice");
  await page.getByLabel(/^Rules/).check();
  await page.waitForFunction(() => !document.querySelector("#results-list.dim"));
  await page.fill("#yf", "1900"); await page.fill("#yt", "1901");
  await page.getByRole("button", { name: "Apply" }).click();
  await expect(page.locator(".empty h2")).toHaveText("No published documents match");
  await expect(page.locator(".empty")).toContainText("not evidence that no authority exists");
  await shot(page, "syn-13-empty-state.png");
  await page.getByRole("button", { name: "Remove year filter" }).first().click();
  await expect(page.locator(".hit").first()).toBeVisible();
  await page.goto("/d/syn-v-other?p=1");
  await page.getByRole("tab", { name: "Cited/Citing" }).click();
  await expect(page.locator(".ctx-body")).toContainText("No extracted links. This does not mean there is no related or adverse authority.");
});

test("UX-14 a late first query never overwrites the second; disconnection blanks views and recovers", async ({ page, context }) => {
  await login(page);
  await page.route(/\/api\/search\?q=tribunal/, async (route) => { await new Promise((r) => setTimeout(r, 1500)); await route.continue(); });
  await page.fill("#q", "tribunal"); await page.press("#q", "Enter");
  await page.waitForTimeout(150);
  await search(page, "lanterns");
  await page.waitForTimeout(1800);
  await expect(page.locator(".hit").first()).toContainText("lanterns");
  await expect(page.locator("#q")).toHaveValue("lanterns");
  await page.unroute(/\/api\/search\?q=tribunal/);
  await page.locator(".hit").first().click();
  await context.setOffline(true);
  await page.fill("#q", "notice"); await page.press("#q", "Enter");
  await expect(page.locator("#degraded")).toContainText("Connection to the server lost");
  await expect(page.locator("main")).toContainText("Open views have been cleared");
  await expect(page.locator(".textview, .pagewrap")).toHaveCount(0);
  await context.setOffline(false);
  await expect(page.locator("#research")).toBeVisible({ timeout: 20_000 });
});

test("UX-15 a failed original range shows an explicit failure, labelled text fallback and retry of the same copy", async ({ page }) => {
  await login(page);
  await page.goto("/r");
  await page.evaluate(() => { window.__mimamsaTestFail = "range"; });
  await search(page, "lanterns");
  await page.locator(".hit").first().click();
  await expect(page.locator(".error-state")).toContainText("The original could not be displayed in the browser");
  await expect(page.locator(".error-state")).toContainText("No derived or substitute file is shown");
  await shot(page, "syn-15-original-failed.png");
  await page.getByRole("button", { name: "Show the Text view" }).click();
  await expect(page.locator(".textview")).toContainText("Extracted text (automated, not verified)");
  await page.getByRole("button", { name: "Original", exact: true }).click();
  await page.getByRole("button", { name: "Retry the original" }).click();
  await expect(page.locator(".pagewrap canvas")).toBeVisible();
});

test("UX-16 keyboard-only path, help dialog focus return, landmarks and names, screen-reader mode", async ({ page }) => {
  await login(page);
  await page.keyboard.press("/");
  await expect(page.locator("#q")).toBeFocused();
  await page.keyboard.type("summary of evidence");
  await page.keyboard.press("Enter");
  await page.waitForFunction(() => document.querySelectorAll(".hit").length > 0);
  await page.keyboard.press("Escape");
  await expect(page.locator("#results-list")).toBeFocused();
  await page.keyboard.press("j");
  await expect(page.locator(".hit[aria-selected=true]")).toHaveCount(1);
  const outline = await page.evaluate(() => getComputedStyle(document.activeElement).outlineStyle + " " + getComputedStyle(document.activeElement).outlineWidth);
  expect(outline).toContain("2px");
  await page.keyboard.press("Enter");
  await expect(page.locator(".dochead h1")).toBeVisible();
  await page.locator("#viewer").focus();
  await page.keyboard.press("e");
  await expect(page.locator("#ctx-tab-evidence")).toBeFocused();
  await page.keyboard.press("ArrowRight");
  await expect(page.locator("#ctx-tab-provenance")).toBeFocused();
  await page.locator("#viewer").focus();
  await page.keyboard.press("?");
  await expect(page.locator("dialog[open]")).toContainText("Keyboard shortcuts");
  await page.keyboard.press("Escape");
  await expect(page.locator("dialog[open]")).toHaveCount(0);
  await expect(page.locator("#viewer")).toBeFocused();
  expect(await a11yBasics(page)).toEqual([]);
  await page.getByRole("button", { name: /reader · User/ }).click();
  await page.getByRole("menuitemcheckbox").click();
  await page.locator("#viewer").focus();
  await page.keyboard.press("t");
  await expect(page.locator(".textview")).toHaveCount(0);       // single keys off in screen-reader mode
});

test("UX-17 status is glyph plus text, never colour alone; candidate banner on every view", async ({ page }) => {
  await login(page);
  await page.goto("/d/syn-j-allow?p=7");
  const cand = page.locator(".chip-candidate").first();
  await expect(cand).toHaveText(/Candidate/);
  expect(await cand.evaluate((e) => getComputedStyle(e, "::before").content)).toBe('"○"');
  for (const p of ["/r", "/s", "/assistant", "/d/syn-s-act?p=2"]) {
    await page.goto(p);
    await expect(page.locator("#banner")).toContainText("Research and candidate data. Not legally verified.");
    await expect(page.locator("#banner")).toContainText("AUTH-LEDGER v0");
  }
});

test("UX-19 Hindi OCR page: retrieved with OCR and low-confidence labels; text marked search-only", async ({ page }) => {
  await login(page);
  await search(page, "सुनवाई से पहले लिखित सूचना");
  const first = page.locator(".hit").first();
  await expect(first).toContainText("सुनवाई");
  await expect(first.locator(".chip-warning").first()).toHaveText("OCR");
  await first.click();
  await page.keyboard.press("t");
  await expect(page.locator(".textview")).toContainText("OCR text: for search only. Quote from the original page.");
  await expect(page.locator(".textview")).toContainText("Low OCR confidence");
  await shot(page, "syn-19-ocr-text-labels.png");
});

test("UX-09 W-10 Admin withdraws the canary; deep link, search and citation all respect it at once", async ({ page, browser }) => {
  const user = await browser.newPage();
  await login(user);
  await user.goto("/d/syn-v-withdrawn?p=1");
  await expect(user.locator(".dochead h1")).toContainText("Withdrawal canary");
  const sha = (await user.evaluate(() => window.__mimamsaViewer?.metrics?.meta?.copy_sha256)) || "";
  await login(page, "admin");
  await page.getByRole("link", { name: "Administration" }).click();
  await page.fill("#wd-doc", "syn-v-withdrawn");
  await page.fill("#wd-reason", "Synthetic canary withdrawal (UX-09)");
  await page.getByRole("button", { name: "Withdraw…" }).click();
  await expect(page.locator("dialog")).toContainText("not legal approval");
  await page.locator("dialog").getByRole("button", { name: "Withdraw" }).click();
  await expect(page.locator("table.data")).toContainText("Synthetic canary withdrawal (UX-09)");
  await shot(page, "syn-09-admin-withdrawal.png");
  await user.reload();
  await expect(user.locator(".docempty")).toContainText("This document is not available in this installation.");
  await user.goto("/r?q=exact%3Aviolet-plume-canary");
  await expect(user.locator(".empty h2")).toHaveText("No published documents match");
  if (sha) {
    await user.goto(`/cite/R13-syn-fixture-20261125-00000002/syn-v-withdrawn/${sha.slice(0, 12)}/1`);
    await expect(user.locator("[data-cite-state]")).toHaveText("The cited copy is not available in this installation.");
  }
  const reader = await user.request.get("/api/admin/overview");
  expect(reader.status()).toBe(403);
});

test("F05 a document identifier pins one representative passage; only passages containing it are labelled Identifier", async ({ page }) => {
  await login(page);
  await search(page, "2021 BRSYN 12");
  await expect(page.locator(".hit .chip", { hasText: "Document match" }).first()).toBeVisible();
  const idHits = page.locator(".hit", { has: page.locator(".chip", { hasText: /^Identifier$/ }) });
  for (const t of await idHits.allTextContents()) expect(t).toContain("2021 BRSYN 12");
  expect(await page.locator(".hit").count()).toBeLessThanOrEqual(4);
});

test("F04 search highlights on the original keep the glyphs legible", async ({ page }) => {
  await login(page);
  await search(page, "decision-maker records");
  await page.locator(".hit").first().click();
  await expect(page.locator(".pagewrap canvas")).toBeVisible();
  await expect(page.locator(".textLayer mark").first()).toBeVisible();
  expect(await darkPixelsUnderFirstMark(page)).toBeGreaterThan(10);
});

test("F01 withdrawal covers the earlier edition: cited copy and its byte ranges become unavailable", async ({ page, browser }) => {
  const map = require(process.env.B1_SYN_MAP || require("path").join(process.env.B1_SYN_SITE, "..", "fixture_map.json"));
  const old = map.j_allow_r1_copy;
  const user = await browser.newPage();
  await login(user);
  const before = await user.request.get(`/api/v2/documents/syn-j-allow/copies/${old}/range`, { headers: { Range: "bytes=0-99" } });
  expect(before.status()).toBe(206);
  await login(page, "admin");
  await page.getByRole("link", { name: "Administration" }).click();
  await page.fill("#wd-doc", "syn-j-allow");
  await page.fill("#wd-reason", "F01 regression: earlier edition must go too");
  await page.getByRole("button", { name: "Withdraw…" }).click();
  await expect(page.locator("dialog")).toContainText("including earlier editions");
  await page.locator("dialog").getByRole("button", { name: "Withdraw" }).click();
  await expect(page.locator("table.data")).toContainText("F01 regression");
  await user.goto(`/cite/R13-syn-fixture-20261125-00000001/syn-j-allow/${old.slice(0, 12)}/6`);
  await expect(user.locator("[data-cite-state]")).toHaveText("The cited copy is not available in this installation.");
  const after = await user.request.get(`/api/v2/documents/syn-j-allow/copies/${old}/range`, { headers: { Range: "bytes=0-99" } });
  expect(after.status()).toBe(404);
  const meta = await user.request.get(`/api/v2/documents/syn-j-allow/pdf-meta?copy=${old}`);
  expect(meta.status()).toBe(404);
});

// ------------------------------------------------------------------ C14 S2 safety journeys (run last, in this order)
async function adminCsrf(page) { return (await (await page.request.get("/api/session")).json()).csrf; }

test("C14-S2-01 F05 a withdrawal clears a viewer that is already open, without any reader action", async ({ page, browser }) => {
  const user = await browser.newPage();
  await login(user);
  await user.goto("/d/syn-h-manual?p=1");
  await expect(user.locator(".pagewrap canvas").first()).toBeVisible();
  await expect(user.locator(".dochead")).toBeVisible();
  await login(page, "admin");
  await page.getByRole("link", { name: "Administration" }).click();
  await page.fill("#wd-doc", "syn-h-manual");
  await page.fill("#wd-reason", "C14 S2 open-viewer invalidation");
  await page.getByRole("button", { name: "Withdraw…" }).click();
  await expect(page.locator("dialog")).toContainText("Pages already on a reader's screen are cleared");
  await expect(page.locator("dialog")).toContainText("No byte-identical copy of this document is held under another document id.");
  await page.locator("dialog").getByRole("button", { name: "Withdraw" }).click();
  await expect(page.locator("table.data")).toContainText("C14 S2 open-viewer invalidation");
  // the reader does nothing: the epoch poll (10 s) clears the page, the header and the evidence
  await expect(user.locator(".docempty[data-invalidated]")).toContainText("This document is not available in this installation.", { timeout: 20_000 });
  await expect(user.locator(".pagewrap canvas")).toHaveCount(0);
  await expect(user.locator(".dochead")).toHaveCount(0);
  await shot(user, "c14-s2-01-viewer-cleared.png");
});

test("C14-S2-02 F05 a deep link to a withdrawn document shows the notice", async ({ page }) => {
  await login(page);
  await page.goto("/d/syn-h-manual?p=1");
  await expect(page.locator(".docempty")).toContainText("This document is not available in this installation.");
  await expect(page.locator(".pagewrap canvas")).toHaveCount(0);
});

test("C14-S2-03 reinstatement needs a reason, re-verifies, and makes the document available again", async ({ page, browser }) => {
  await login(page, "admin");
  await page.getByRole("link", { name: "Administration" }).click();
  const row = page.locator("table.data tr", { hasText: "syn-h-manual" }).first();
  await row.getByRole("button", { name: "Reinstate…" }).click();
  await expect(page.locator("dialog")).toContainText("verifies again");
  await page.locator("dialog").getByRole("button", { name: "Reinstate" }).click();
  await expect(page.locator("dialog .err")).toContainText("A reason");
  await page.fill("#ri-reason", "C14 S2 reinstatement after review");
  await page.locator("dialog").getByRole("button", { name: "Reinstate" }).click();
  await expect(page.locator("table.data")).toContainText("Reinstated");
  await expect(page.locator("table.data")).toContainText("re-hashed");
  const user = await browser.newPage();
  await login(user);
  await user.goto("/d/syn-h-manual?p=1");
  await expect(user.locator(".pagewrap canvas").first()).toBeVisible();
});

test("C14-S2-04 a protected transfer in progress when the document is withdrawn is refused at handoff", async ({ page, browser }) => {
  const user = await browser.newPage();
  await login(user);
  const meta = await (await user.request.get("/api/v2/documents/syn-j-reject/pdf-meta")).json();
  const url = `/api/v2/documents/syn-j-reject/copies/${meta.copy_sha256}/range`;
  const pull = () => user.evaluate(async (u) => {
    const r = await fetch(u, { headers: { Range: "bytes=0-99", "X-Mimamsa-Test-Pause": "before-enter" }, cache: "no-store" });
    return { status: r.status, bytes: (await r.arrayBuffer()).byteLength };
  }, url);
  expect(await pull()).toEqual({ status: 206, bytes: 100 });          // control: completes when nothing happens
  await login(page, "admin");
  const csrf = await adminCsrf(page);
  const inFlight = pull();                                               // admitted, credit reserved, paused before handoff
  await page.waitForTimeout(1200);
  const w = await page.request.post("/api/admin/withdraw", { headers: { "X-CSRF-Token": csrf }, data: { doc_id: "syn-j-reject", reason: "C14 S2 in-flight transfer" } });
  expect(w.status()).toBe(200);
  expect(await inFlight).toEqual({ status: 404, bytes: 0 });            // no byte of the withdrawn original is handed over
  const r = await page.request.post("/api/admin/reinstate", { headers: { "X-CSRF-Token": csrf }, data: { doc_id: "syn-j-reject", reason: "C14 S2 restore fixture state" } });
  expect(r.status()).toBe(200);
});

test("C14-S2-05 F15 lockout, Admin unlock with a reason, and the audit log", async ({ page, browser }) => {
  const anon = await browser.newContext({ baseURL: test.info().project.use.baseURL });
  for (let i = 0; i < 5; i++) expect((await anon.request.post("/api/login", { data: { username: "locktest", password: "wrong-password-xx" } })).status()).toBe(401);
  const user = await browser.newPage();
  await user.goto("/");
  await user.fill("#username", "locktest"); await user.fill("#password", "locktest-password-1");
  await user.click("form.login button[type=submit]");
  await expect(user.locator("form.login .err")).toContainText("not correct, or the account is locked");
  await login(page, "admin");
  await page.getByRole("link", { name: "Administration" }).click();
  const row = page.locator("#accounts-table tr", { hasText: "locktest" });
  await expect(row).toContainText("Locked until");
  await row.getByRole("button", { name: "Unlock…" }).click();
  await page.fill("#ul-reason", "C14 S2 identity confirmed by the owner");
  await page.locator("dialog").getByRole("button", { name: "Unlock" }).click();
  await expect(page.locator("#accounts-table tr", { hasText: "locktest" })).toContainText("Active");
  await expect(page.locator("#audit-table")).toContainText("unlock");
  await expect(page.locator("#audit-table")).toContainText("C14 S2 identity confirmed by the owner");
  await expect(page.locator("#audit-table")).toContainText("lockout");
  await expect(page.locator("#audit-table")).not.toContainText("wrong-password-xx");
  await shot(page, "c14-s2-05-admin-accounts-audit.png");
  await user.click("form.login button[type=submit]");
  await expect(user.locator("#research")).toBeVisible();
  await anon.close();
});