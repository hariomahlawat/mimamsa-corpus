// C14 S3 journeys on the synthetic SYN site (CI): library home, grouped Statutes list, relations surface with no
// comparison table held (absence stated, nothing invented).
const { test, expect } = require("playwright/test");
const { login } = require("./helpers.cjs");

test("R-SYN-01 library home replaces the empty document pane", async ({ page }) => {
  await login(page);
  await expect(page.locator(".home")).toContainText("Library");
  await expect(page.locator(".home-summary")).toContainText("documents");
  await expect(page.locator(".home-card", { hasText: "Try" }).locator("a").first()).toBeVisible();
});

test("R-SYN-02 Statutes list is grouped and a section with no comparison table says so", async ({ page }) => {
  await login(page);
  await page.goto("/s");
  await expect(page.locator(".statute-cat").first()).toBeVisible();
  const first = page.locator(".statute-list .instrument > a").first();
  const href = await first.getAttribute("href");
  await page.goto(href);
  const sec = page.locator("ul.toc a").first();
  if (await sec.count()) {
    await sec.click();
    await expect(page.locator("#relstrip")).not.toContainText("Candidate");
    await expect(page.locator("#relstrip")).toContainText(/No corresponding provision|not an Act/);
  }
});
