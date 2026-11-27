// Real offline sample (290 public documents from the HF corpus master, imported by app/importer). Only configured
// when B1_SAMPLE_SITE exists on the host (corpus bytes are never in git or CI). Produces the B1 screenshots.
const { test, expect } = require("playwright/test");
const { login, search, shot, a11yBasics, darkPixelsUnderFirstMark } = require("./helpers.cjs");

test("S-01 identifier search s.69 Army Act: provision text first, original at the page", async ({ page }) => {
  await login(page);
  await search(page, "s.69 Army Act");
  await expect(page.locator(".qchip").first()).toContainText("Section 69 · The Army Act, 1950");
  await expect(page.locator(".hit").first()).toContainText("69. Civil offences.—Subject to the provisions of section 70");
  await page.locator(".hit").first().click();
  await expect(page.locator(".pagewrap canvas")).toBeVisible();
  await expect(page.locator(".textLayer mark").first()).toBeVisible();
  expect(await darkPixelsUnderFirstMark(page)).toBeGreaterThan(10);
  await shot(page, "b1-01-identifier-search-document-1920.png");
  expect(await a11yBasics(page)).toEqual([]);
});

test("S-02 neutral citation 2013 INSC 408 opens Dharamvir Singh with candidate outcome and seven axes", async ({ page }) => {
  await login(page);
  await search(page, "2013 INSC 408");
  await expect(page.locator(".rgroup-title").first()).toContainText("DHARAMVIR SINGH");
  await page.locator(".hit").first().click();
  await expect(page.locator(".dochead")).toContainText("2013 INSC 408");
  await expect(page.locator("details.axis")).toHaveCount(7);
  await expect(page.locator(".pagewrap canvas")).toBeVisible();
  await expect(page.locator(".placeholder")).toHaveCount(0);
  await expect(page.locator(".dochead")).toContainText("Judges (crawler; may be incomplete)");
  await shot(page, "b1-02-judgment-evidence-1920.png");
  await page.getByRole("tab", { name: "Provenance" }).click();
  await shot(page, "b1-03-provenance-1920.png");
  await page.getByRole("tab", { name: "Cited/Citing" }).click();
  await expect(page.locator(".ctx-body")).toContainText("Absence of a citation is not absence of authority");
});

test("S-03 statutes: Army Act s.75 printed as omitted, A4 temporal candidates, as-of closed", async ({ page }) => {
  await login(page);
  await page.goto("/s/act-army-1950/75");
  await expect(page.locator(".dochead h2")).toContainText("Field punishment");
  await expect(page.locator("#a4strip")).toContainText("Temporal chain not established");
  await expect(page.locator("#asof")).toBeDisabled();
  await shot(page, "b1-04-statute-section-75-1920.png");
});

test("S-04 compact 1366x768: rail collapses, context becomes a drawer", async ({ page }) => {
  await page.setViewportSize({ width: 1366, height: 768 });
  await login(page);
  await search(page, "disability pension invalided");
  await page.locator(".hit").first().click();
  await expect(page.locator(".pagewrap canvas")).toBeVisible();
  await shot(page, "b1-05-compact-1366.png");
  await page.getByRole("button", { name: "Evidence", exact: true }).click();
  await expect(page.locator(".ctx")).toBeVisible();
  await shot(page, "b1-06-compact-1366-evidence-drawer.png");
});

test("S-05 narrow window 1024 and 800: document fills the width, results become a drawer", async ({ page }) => {
  await page.setViewportSize({ width: 1024, height: 768 });
  await login(page);
  await search(page, "court martial summary of evidence");
  await shot(page, "b1-07-narrow-1024-results.png");
  await page.locator(".hit").first().click();
  await expect(page.locator(".docpane")).toBeVisible();
  await page.setViewportSize({ width: 800, height: 900 });
  await expect(page.locator(".pagewrap canvas")).toBeVisible();
  await page.waitForTimeout(500);
  await shot(page, "b1-08-narrow-800-document.png");
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth);
  expect(overflow).toBe(false);
});

test("S-08 instrument disambiguation: Rule 22 Army Rules scopes to the Army Rules, not another Rules instrument", async ({ page }) => {
  await login(page);
  await search(page, "Rule 22 Army Rules");
  await expect(page.locator(".qchip").first()).toContainText("Army Rules,1954");
  const docs = await page.locator(".rgroup").evaluateAll((els) => els.map((e) => e.dataset.doc));
  expect(docs[0]).toBe("rules-army-rules-1954");
  expect(docs).not.toContain("rules-the-army-and-air-force-disposal-of-private-property-rules-1953");
});

test("S-09 instrument not held or ambiguous: nothing from another instrument is pinned (F14)", async ({ page }) => {
  await login(page);
  await search(page, "Rule 22 Navy Rules");
  await expect(page.locator(".qchip", { hasText: "No instrument titled" })).toContainText("Navy Rules");
  await expect(page.locator(".hit .chip", { hasText: /^Identifier$/ })).toHaveCount(0);
  await expect(page.locator(".hit", { hasText: "Rule 22: provision text" })).toHaveCount(0);
  await search(page, "Rule 22 Rules");
  await expect(page.locator(".qchip", { hasText: "which instrument?" })).toBeVisible();
  expect(await page.locator(".qchip", { hasText: "which instrument?" }).getAttribute("title")).toContain("Army Rules");
  await expect(page.locator(".hit .chip", { hasText: /^Identifier$/ })).toHaveCount(0);
});

test("S-06 Commander view and dark theme", async ({ page }) => {
  await login(page);
  await page.click("#view-commander");
  await search(page, "AFT jurisdiction");
  await expect(page.locator(".qchip", { hasText: "AFT" })).toContainText("Armed Forces Tribunal");
  await shot(page, "b1-09-commander-abbreviation.png");
  await page.click("#view-practitioner");
  await page.getByRole("button", { name: /reader · User/ }).click();
  await page.getByRole("menuitem", { name: "Switch light / dark theme" }).click();
  await page.locator(".hit").first().click();
  await page.keyboard.press("t");
  await expect(page.locator(".textview")).toBeVisible();
  await expect(page.locator(".pagewrap")).toHaveCount(0);
  await shot(page, "b1-10-dark-text-view.png");
});

test("S-07 Administration overview (Admin) and closed assistant", async ({ page }) => {
  await login(page, "admin");
  await page.getByRole("link", { name: "Administration" }).click();
  await expect(page.locator(".cards")).toContainText("Documents verified");
  await shot(page, "b1-11-admin-overview.png");
  await page.getByRole("link", { name: "Assistant" }).click();
  await shot(page, "b1-12-gated-assistant.png");
});

// C14 S1 on the real sample: statutory aliases, party names, unrecorded citations, editions nested, document pages.
test("S-10 IPC and BNS abbreviations pin the provision with a disclosed alias; I.P.C. too", async ({ page }) => {
  await login(page);
  for (const [q, chipText, hitText] of [["section 302 IPC", "IPC → The Indian Penal Code", "302. Punishment for murder"],
                                         ["s.302 I.P.C.", "IPC → The Indian Penal Code", "302. Punishment for murder"],
                                         ["section 103 BNS", "BNS → The Bharatiya Nyaya Sanhita", null]]) {
    await search(page, q);
    await expect(page.locator(".qchip[data-kind=alias]")).toContainText(chipText);
    await expect(page.locator(".qchip", { hasText: "No instrument titled" })).toHaveCount(0);
    await expect(page.locator(".hit").first().locator(".chip", { hasText: "Identifier" })).toBeVisible();
    if (hitText) await expect(page.locator(".rgroup").first().locator(".hit").first()).toContainText(hitText);
  }
  await expect(page.locator(".rgroup").first().locator(".rgroup-variants")).toContainText("Hindi text");
});

test("S-11 party name ranks the named judgment first; an unrecorded SCC citation says so", async ({ page }) => {
  await login(page);
  await search(page, "Dharamvir Singh");
  await expect(page.locator(".rgroup").first()).toHaveAttribute("data-doc", "sc-2013-dharamvir-singh-2013insc408");
  await expect(page.locator(".qchip[data-kind=case_name]")).toContainText("DHARAMVIR SINGH");
  await search(page, "(2013) 7 SCC 316");
  await expect(page.locator(".qchip[data-kind=not_held]")).toContainText("Citation not recorded in this library");
  await search(page, "[2013] 8 S.C.R. 1119");
  await expect(page.locator(".rgroup").first()).toHaveAttribute("data-doc", "sc-2013-dharamvir-singh-2013insc408");
  await search(page, "court marshal");
  await expect(page.locator(".qchip-suggest")).toContainText("court martial");
});

test("S-12 document pages reach every result; page is in the URL and restores", async ({ page }) => {
  await login(page);
  await search(page, "court martial");
  const pager = page.locator("nav.pager");
  await expect(pager).toContainText("Page 1 of");
  const total = parseInt((await pager.innerText()).match(/of (\d+)/)[1], 10);
  expect(total).toBeGreaterThan(5);
  await pager.getByRole("button", { name: "Next" }).click();
  await expect(page.locator("nav.pager")).toContainText(`Page 2 of ${total}`);
  expect(page.url()).toContain("page=2");
  await page.goto(`/r?q=court+martial&page=${total}`);
  await expect(page.locator("nav.pager")).toContainText(`Page ${total} of ${total}`);
  await expect(page.locator("nav.pager").getByRole("button", { name: "Next" })).toBeDisabled();
  await expect(page.locator(".rgroup").first()).toBeVisible();
  await page.selectOption("#sort", "new");
  await expect(page.locator("nav.pager")).toContainText(`Page 1 of ${total}`);     // a new ordering starts at page 1
});