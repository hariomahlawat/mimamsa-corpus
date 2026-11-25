import assert from "node:assert/strict";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || "playwright");
const fixtureUrl = new URL(process.argv[2]);
const browser = await chromium.launch({executablePath: process.env.CHROMIUM_PATH || undefined, headless: true});
try {
  const page = await browser.newPage();
  const responses = [];
  const unexpected = [];
  await page.route("**/*", route => {
    if (new URL(route.request().url()).origin !== fixtureUrl.origin) {
      unexpected.push(route.request().url());
      return route.abort();
    }
    return route.continue();
  });
  page.on("response", response => {
    if (new URL(response.url()).pathname === "/pdf") responses.push(response);
  });
  await page.goto(fixtureUrl.href);
  await page.waitForFunction(() => document.querySelector("canvas").dataset.pageText === "Synthetic page 1");
  await page.getByLabel("Page", {exact: true}).fill("12");
  await page.getByRole("button", {name: "Go"}).click();
  await page.waitForFunction(() => document.querySelector("canvas").dataset.pageText === "Synthetic page 12");
  assert.deepEqual(unexpected, []);
  assert.ok(responses.length > 0);
  const ranges = responses.map(response => {
    assert.equal(response.status(), 206);
    const request = response.request();
    assert.ok(request.headers().authorization);
    const [, start, end] = /^bytes=(\d+)-(\d+)$/.exec(request.headers().range);
    const [, responseStart, responseEnd, size] =
      /^bytes (\d+)-(\d+)\/(\d+)$/.exec(response.headers()["content-range"]);
    assert.equal(start, responseStart);
    assert.equal(end, responseEnd);
    assert.equal(Number(response.headers()["content-length"]), Number(end) - Number(start) + 1);
    assert.ok(Number(size) > 256 * 1024);
    assert.ok(Number(end) - Number(start) + 1 <= 128 * 1024);
    return [Number(start), Number(end), Number(size)];
  });
  assert.ok(ranges.some(([start, , size]) => start > size * 0.75));
  console.log(JSON.stringify({browser: browser.version(), renderedPages: [1, 12], ranges}));
} finally {
  await browser.close();
}
