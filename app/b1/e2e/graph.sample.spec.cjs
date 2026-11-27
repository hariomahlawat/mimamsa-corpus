// C15 S3 journeys on the real offline sample: Graph inspection page, research assessment, eligibility, access control.
// Evidence screenshots (JPEG q70, DSF 1) are written to app/b1/evidence/c15_graph/.
const path = require("path");
const fs = require("fs");
const { test, expect } = require("playwright/test");
const { login } = require("./helpers.cjs");

const OUT = path.resolve(__dirname, "..", "evidence", "c15_graph");
fs.mkdirSync(OUT, { recursive: true });
async function evidence(page, name) { await page.waitForTimeout(300); await page.screenshot({ path: path.join(OUT, name + ".jpg"), type: "jpeg", quality: 70 }); }
test.use({ deviceScaleFactor: 1 });

test("G-01 graph page: IPC s.302 relationships with status and evidence; research assessment never establishes", async ({ page }) => {
  await login(page);
  await page.goto("/g?doc=act-ipc-1860&section=302");
  await expect(page.locator("#g-stats")).toContainText("relationships");
  await expect(page.locator(".g-node")).toContainText("302");
  const corr = page.locator('details.g-group[data-type="RE_ENACTED_AS"]');
  await expect(corr.locator("tr")).toHaveCount(2);                     // header + one row
  await expect(corr).toContainText("Candidate");
  await expect(corr.locator("td a", { hasText: "103" })).toBeVisible();
  await expect(corr).toContainText("not legally interchangeable");
  await evidence(page, "g01-ipc-302-relationships-1920");
  await page.fill("#g-conduct", "2023-12-01");
  await page.getByRole("button", { name: "Commencement, repeal, savings, correspondence" }).click();
  await expect(page.locator(".g-overall")).toHaveAttribute("data-state", "INSUFFICIENT_INFORMATION");
  await expect(page.locator('.g-findings li[data-code="correspondence"]')).toContainText("s.103");
  await expect(page.locator('.g-findings li[data-code="commencement_not_established"]')).toBeVisible();
  await expect(page.locator('.g-findings li[data-state="ESTABLISHED"]')).toHaveCount(0);
  await expect(page.locator("#g-assess-out")).toContainText("AUTH-LEDGER is at version 0");
  await evidence(page, "g01-ipc-302-assessment-1920");
  await page.getByRole("button", { name: "Which version on the as-of date?" }).click();
  await expect(page.locator("#g-assess-out")).toContainText("Missing facts");
  // navigate to the corresponding provision through the graph
  await corr.locator("td a", { hasText: "103" }).click();
  await expect(page.locator(".g-node")).toContainText("103");
});

test("G-02 withdrawing the comparison table removes its relationships from the graph; reinstatement restores them", async ({ page, browser }) => {
  const user = await browser.newPage();
  await login(user);
  const before = await (await user.request.get("/api/graph/stats")).json();
  await login(page, "admin");
  const origin = new URL(page.url()).origin;
  const csrf = (await (await page.request.get("/api/session")).json()).csrf;
  const post = (url, data) => page.request.post(url, { headers: { "X-CSRF-Token": csrf, Origin: origin }, data });
  expect((await post("/api/admin/withdraw", { doc_id: "ref-bprd-comparison-bns-ipc", reason: "C15 G-02 graph eligibility" })).status()).toBe(200);
  try {
    const during = await (await user.request.get("/api/graph/stats")).json();
    expect(during.edges_by_type.RE_ENACTED_AS).toBeLessThan(before.edges_by_type.RE_ENACTED_AS);
    await user.goto("/g?doc=act-ipc-1860&section=302");
    await expect(user.locator(".g-node")).toContainText("302");
    await expect(user.locator('details.g-group[data-type="RE_ENACTED_AS"]')).toHaveCount(0);
    const r = await (await user.request.get("/api/reasoning/assess?kind=succession&doc=act-ipc-1860&section=302")).json();
    expect(r.findings.map((f) => f.code)).not.toContain("correspondence");
  } finally {
    expect((await post("/api/admin/reinstate", { doc_id: "ref-bprd-comparison-bns-ipc", reason: "C15 G-02 restore after test" })).status()).toBe(200);
  }
  const after = await (await user.request.get("/api/graph/stats")).json();
  expect(after.edges_by_type.RE_ENACTED_AS).toBe(before.edges_by_type.RE_ENACTED_AS);
});

// Codex review of PR #75: a graph view that is already open follows a withdrawal without any reader action (the epoch
// poll runs while the graph is shown); the relationships and the assessment evidence from the withdrawn source go.
test("G-04 an open graph view and its assessment drop a withdrawn source without any reader action", async ({ page, browser }) => {
  const user = await browser.newPage();
  await login(user);
  await user.goto("/g?doc=act-ipc-1860&section=302");
  const corr = user.locator('details.g-group[data-type="RE_ENACTED_AS"]');
  await expect(corr).toHaveCount(1);
  await user.fill("#g-conduct", "2023-12-01");
  await user.getByRole("button", { name: "Commencement, repeal, savings, correspondence" }).click();
  await expect(user.locator('.g-findings li[data-code="correspondence"]')).toBeVisible();
  await login(page, "admin");
  const origin = new URL(page.url()).origin;
  const csrf = (await (await page.request.get("/api/session")).json()).csrf;
  const post = (url, data) => page.request.post(url, { headers: { "X-CSRF-Token": csrf, Origin: origin }, data });
  expect((await post("/api/admin/withdraw", { doc_id: "ref-bprd-comparison-bns-ipc", reason: "C15 G-04 open graph view" })).status()).toBe(200);
  try {
    await expect(corr).toHaveCount(0, { timeout: 25_000 });
    await expect(user.locator('.g-findings li[data-code="correspondence"]')).toHaveCount(0, { timeout: 10_000 });
    await expect(user.locator(".g-overall")).toBeVisible();                       // the assessment was re-run, not just cleared
    await expect(user.locator("#g-conduct")).toHaveValue("2023-12-01");
  } finally {
    expect((await post("/api/admin/reinstate", { doc_id: "ref-bprd-comparison-bns-ipc", reason: "C15 G-04 restore after test" })).status()).toBe(200);
  }
  await expect(corr).toHaveCount(1, { timeout: 25_000 });                          // reinstatement is followed too
});

test("G-03 graph and reasoning routes need a session", async ({ request }) => {
  for (const u of ["/api/graph/stats", "/api/graph/node?id=x", "/api/graph/path?from=a&to=b", "/api/graph/resolve?doc=act-army-1950",
                   "/api/reasoning/assess?kind=temporal&doc=act-army-1950&section=75", "/api/reasoning/rule-gate"])
    expect((await request.get(u)).status()).toBe(401);
});
