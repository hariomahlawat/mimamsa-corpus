// C14 S3 journeys on the real offline sample: statutes navigation, statutory relationships, library and Commander
// homes, scroll-to-passage, language and unreliable-text handling. Evidence screenshots (JPEG q70, DSF 1) are written to
// app/b1/evidence/c14_reader/.
const path = require("path");
const fs = require("fs");
const { test, expect } = require("playwright/test");
const { login, search, a11yBasics } = require("./helpers.cjs");

const OUT = path.resolve(__dirname, "..", "evidence", "c14_reader");
fs.mkdirSync(OUT, { recursive: true });
async function evidence(page, name) { await page.waitForTimeout(300); await page.screenshot({ path: path.join(OUT, name + ".jpg"), type: "jpeg", quality: 70 }); }
test.use({ deviceScaleFactor: 1 });

test("R-01 Statutes: one entry per instrument, grouped by category, editions nested, filter", async ({ page }) => {
  await login(page);
  await page.goto("/s");
  await expect(page.locator(".statute-cat").first()).toBeVisible();
  const cats = await page.locator(".statute-cat").evaluateAll((els) => els.map((e) => e.dataset.category));
  expect(cats.slice(0, 3)).toEqual(["Army", "Navy", "Air Force"]);
  const army = page.locator(".instrument", { hasText: "The Army Act, 1950" }).first();
  await expect(army.locator(".editions")).toContainText("Hindi");
  await expect(army.locator(".editions")).toContainText("Schedule");
  expect(await page.locator(".statute-list .instrument > a", { hasText: /^The Army Act, 1950/ }).count()).toBe(1);   // not listed twice
  await expect(page.locator(".statute-overview")).toContainText("Statutes");
  await evidence(page, "r01-statutes-list-1920");
  await page.fill("#statute-filter", "sanhita");
  await expect(page.locator(".instrument:visible")).toHaveCount(3);
  await expect(page.locator(".statute-cat:visible")).toHaveCount(1);
  expect(await a11yBasics(page)).toEqual([]);
});

test("R-02 IPC s.302 shows candidate BNS s.103 with evidence, and the reverse; repealed-by notice with held text", async ({ page }) => {
  await login(page);
  await page.goto("/s/act-ipc-1860/302");
  const rel = page.locator("#relstrip");
  await expect(rel.locator(".rel-row")).toHaveCount(1);
  await expect(rel.locator(".rel-row")).toContainText("Candidate");
  await expect(rel.locator(".rel-row a", { hasText: "The Bharatiya Nyaya Sanhita, 2023 s.103" })).toBeVisible();
  await expect(rel.locator(".rel-row q")).toContainText("Punishment for murder");
  await expect(rel).toContainText("not legally interchangeable");
  await rel.locator("details summary").click();
  await expect(rel.locator('[data-kind="repealed_by"]')).toContainText("Repealed by section 358");
  await expect(rel.locator('[data-kind="repealed_by"] q')).toContainText("Indian Penal Code");
  await evidence(page, "r02-ipc-302-correspondence-1920");
  await rel.locator(".rel-row a", { hasText: "s.103" }).click();
  await expect(page).toHaveURL(/\/s\/act-bns-2023\/103$/);
  await expect(page.locator("#relstrip .rel-row").first()).toContainText("The Indian Penal Code s.302");
  await evidence(page, "r02-bns-103-reverse-1920");
});

test("R-03 BNS instrument overview: commencement, repeal and savings records each quote held text with a page", async ({ page }) => {
  await login(page);
  await page.goto("/s/act-bns-2023");
  await page.locator("#instrument-notices summary").click();
  const n = page.locator("#instrument-notices");
  await expect(n.locator('[data-kind="commencement_delegated"] q')).toContainText("Central Government");
  await expect(n.locator('[data-kind="commencement_notification_not_held"]')).toContainText("not established");
  await expect(n.locator('[data-kind="commencement_secondary_source"]')).toContainText("secondary");
  await expect(n.locator('[data-kind="repeal"] q')).toContainText("hereby repealed");
  await expect(n.locator('[data-kind="savings_transitional"] q')).toContainText("Notwithstanding");
  await expect(n.locator('[data-kind="repeal"] a')).toContainText("p.");
  await evidence(page, "r03-bns-repeal-savings-1920");
  await page.goto("/s/act-army-1950/75");   // A4 omission display unchanged
  await expect(page.locator(".dochead h2").first()).toContainText("Field punishment");
  await expect(page.locator("#asof")).toBeDisabled();
});

test("R-04 Hindi legacy-font copy: language marker, unreliable label, not used by search", async ({ page }) => {
  await login(page);
  await search(page, "s.69 Army Act");
  const docs = await page.locator(".rgroup").evaluateAll((els) => els.map((e) => e.dataset.doc));
  expect(docs).not.toContain("act-army-1950-hi");
  await page.goto("/d/act-army-1950-hi?p=16");
  await expect(page.locator(".dochead [data-language]")).toContainText("Hindi");
  await expect(page.locator(".dochead [data-text-reliability]")).toContainText("Extracted text unreliable");
  await page.getByRole("button", { name: "Text", exact: true }).click();
  await expect(page.locator(".text-unreliable")).toContainText("not used for search");
  await evidence(page, "r04-hindi-unreliable-text-1920");
  await page.goto("/d/act-bns-2023-alt-d163e7?p=20");    // well-formed Unicode Hindi: language shown, no unreliable label
  await expect(page.locator(".dochead [data-language]")).toContainText("Hindi");
  await expect(page.locator(".dochead [data-text-reliability]")).toHaveCount(0);
});

for (const vp of [{ width: 1366, height: 768 }, { width: 1920, height: 1080 }, { width: 2560, height: 1440 }]) {
  test(`R-05 cited passage scrolled into view on open at ${vp.width}x${vp.height}`, async ({ page }) => {
    await page.setViewportSize(vp);
    await login(page);
    await search(page, "s.69 Army Act");
    await page.locator(".hit").first().click();
    const bar = page.locator(".cited-bar");
    await expect(bar).toHaveCount(1);
    await page.waitForTimeout(300);
    const [b, v] = [await bar.boundingBox(), await page.locator("#viewer").boundingBox()];
    expect(b.y).toBeGreaterThanOrEqual(v.y);
    expect(b.y + Math.min(b.height, 40)).toBeLessThanOrEqual(v.y + v.height);
    await expect(page.locator(".textLayer")).toContainText("Civil offences");
    await evidence(page, `r05-scroll-to-s69-${vp.width}`);
  });
}

test("R-06 Fit page shows the whole page in the viewer", async ({ page }) => {
  await login(page);
  await page.goto("/d/act-army-1950?p=25");
  await page.locator(".pagewrap canvas").first().waitFor();
  await page.getByRole("button", { name: "Fit page" }).click();
  await page.waitForTimeout(800);
  const [c, v] = [await page.locator(".pagewrap canvas").first().boundingBox(), await page.locator("#viewer").boundingBox()];
  expect(c.height).toBeLessThanOrEqual(v.height);
});

test("R-07 library home and the early Commander task home", async ({ page }) => {
  await login(page);
  await expect(page.locator(".home")).toContainText("Library");
  await expect(page.locator(".home-summary")).toContainText("290 documents");
  await expect(page.locator(".home-card", { hasText: "What is held" })).toContainText("Judgment");
  await expect(page.locator(".home-card", { hasText: "Statutes" }).locator("a").first()).toBeVisible();
  await evidence(page, "r07-library-home-1920");
  await search(page, "summary of evidence");
  await page.locator(".hit").first().click();
  await page.locator(".pagewrap canvas").first().waitFor();
  await page.locator(".tab-close").first().click();
  await expect(page.locator(".home-card", { hasText: "Recent in this session" })).toContainText("summary of evidence");
  await page.click("#view-commander");
  await expect(page.locator(".home")).toContainText("Commander workspace");
  const task = page.locator('.task[data-task="Absence and desertion"]');
  await expect(task.locator("a", { hasText: "Section 39" })).toBeVisible();
  await evidence(page, "r07-commander-home-1920");
  await task.locator("a", { hasText: "Section 39" }).click();
  await expect(page).toHaveURL(/\/s\/act-army-1950\/39$/);
  await page.click("#view-practitioner");
});

test("R-08 one banner line keeps both statements; the context pane groups provenance", async ({ page }) => {
  await login(page);
  await expect(page.locator("#banner")).toContainText("Not legally verified");
  await expect(page.locator("#banner-dev")).toContainText("development key");
  await expect(page.locator("#degraded")).toBeHidden();
  await search(page, "2013 INSC 408");
  await page.locator(".hit").first().click();
  await page.getByRole("tab", { name: "Provenance" }).click();
  await expect(page.locator(".prov h3")).toHaveText(["Where it came from", "This copy", "In this library", "Notes"]);
  await evidence(page, "r08-provenance-grouped-1920");
  await page.getByRole("tab", { name: "Cited/Citing" }).click();
  await expect(page.locator(".ctx-body")).not.toContainText("Unresolved reference");
});
