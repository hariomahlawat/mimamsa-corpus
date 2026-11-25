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

// Review F12: a small committed set, JPEG (quality 72) at deviceScaleFactor 2; other names are not written.
const KEEP = new Set(["b1-01-identifier-search-document-1920", "b1-02-judgment-evidence-1920", "b1-04-statute-section-75-1920",
  "b1-05-compact-1366", "b1-08-narrow-800-document", "b1-10-dark-text-view", "syn-02-parser-error",
  "syn-12-cited-copy-not-current", "syn-15-original-failed"]);
async function shot(page, name) {
  const base = name.replace(/\.(png|jpg)$/, "");
  if (!KEEP.has(base)) return;
  await page.waitForTimeout(400);
  await page.screenshot({ path: path.join(SHOTS, base + ".jpg"), type: "jpeg", quality: 72, fullPage: false });
}

/** Review F04: dark glyph pixels must remain visible inside the first search mark on the original page. */
async function darkPixelsUnderFirstMark(page) {
  const mark = page.locator(".textLayer mark").first();
  await mark.scrollIntoViewIfNeeded();
  const box = await mark.boundingBox();
  const png = await page.screenshot({ clip: { x: box.x, y: box.y, width: Math.max(4, box.width), height: Math.max(4, box.height) } });
  return page.evaluate(async (b64) => {
    const img = new Image(); img.src = "data:image/png;base64," + b64; await img.decode();
    const c = document.createElement("canvas"); c.width = img.width; c.height = img.height;
    const x = c.getContext("2d"); x.drawImage(img, 0, 0);
    const d = x.getImageData(0, 0, c.width, c.height).data; let n = 0;
    for (let i = 0; i < d.length; i += 4) if (d[i] + d[i + 1] + d[i + 2] < 240) n++;
    return n;
  }, png.toString("base64"));
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

module.exports = { login, search, shot, a11yBasics, darkPixelsUnderFirstMark, SHOTS };
