const path = require("path");
const { expect } = require("playwright/test");

const SHOTS = path.resolve(__dirname, "..", "..", "..", "docs", "architecture", "b1", "screenshots");

async function login(page, user = "reader") {
  await page.goto("/");
  await page.fill("#username", user);
  await page.fill("#password", `${user}-password-1`);
  await page.click("form.login button[type=submit]");
  await expect(page.locator("#research")).toBeVisible();
}

async function search(page, q) {
  await page.fill("#q", q);
  await page.press("#q", "Enter");
  await expect(page.locator("#results-head")).not.toHaveAttribute("aria-busy", "true");
  await page.waitForFunction(() => !document.querySelector("#results-list.dim"));
}

async function shot(page, name) {
  await page.waitForTimeout(400);
  await page.screenshot({ path: path.join(SHOTS, name), fullPage: false });
}

/** Accessibility checks that need no third-party engine: landmarks, accessible names, focus ring, no positive tabindex. */
async function a11yBasics(page) {
  return page.evaluate(() => {
    const issues = [];
    for (const sel of ["header", "nav", "[role=search]", "main", "footer[role=contentinfo]"]) if (!document.querySelector(sel)) issues.push(`missing landmark ${sel}`);
    const named = (el) => (el.getAttribute("aria-label") || el.getAttribute("aria-labelledby") || el.getAttribute("title") || (el.labels && el.labels.length) || el.textContent.trim()).toString().length > 0;
    for (const el of document.querySelectorAll("button, a[href], input:not([type=hidden]), select, textarea, [role=tab], [role=option]"))
      if (el.offsetParent !== null && !named(el)) issues.push(`unnamed ${el.tagName.toLowerCase()} ${el.className}`);
    for (const el of document.querySelectorAll("[tabindex]")) if (+el.getAttribute("tabindex") > 0) issues.push("positive tabindex");
    for (const img of document.querySelectorAll("img")) if (!img.hasAttribute("alt")) issues.push("img without alt");
    return issues;
  });
}

module.exports = { login, search, shot, a11yBasics, SHOTS };
