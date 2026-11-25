// B1 end-to-end journeys (headless Chromium). Run:
//   node <playwright>/cli.js test --config app/b1/e2e/playwright.config.cjs --trace off
// Environment:
//   B1_DLL            built Mimamsa.Web.dll (default: Release build in the source tree)
//   B1_SYN_SITE       synthetic SYN site (app/b1/build/build_fixture_site.py)      -> journeys.spec.cjs (required)
//   B1_SYN_DB         disposable Npgsql DSN for the SYN service
//   B1_SAMPLE_SITE    real offline sample site (app/b1/build/build_sample.py)        -> sample.spec.cjs (optional:
//   B1_SAMPLE_DB      only configured when the corpus sample exists on the host; CI has no corpus bytes)
// Screenshots are written by the specs to docs/architecture/b1/screenshots/ at deviceScaleFactor 2.
const path = require("path");
const root = path.resolve(__dirname, "..");
const dll = process.env.B1_DLL || path.join(root, "src", "Mimamsa.Web", "bin", "Release", "net10.0", "Mimamsa.Web.dll");
const dotnet = process.env.DOTNET || "dotnet";
const webDir = require("fs").existsSync(path.join(path.dirname(dll), "wwwroot")) ? path.dirname(dll) : path.join(root, "src", "Mimamsa.Web");

function server(port, site, db) {
  return {
    command: `"${dotnet}" "${dll}"`, cwd: webDir, url: `http://127.0.0.1:${port}/health`, reuseExistingServer: false, timeout: 120_000,
    stdout: "ignore", stderr: "pipe",
    env: { ASPNETCORE_URLS: `http://127.0.0.1:${port}`, Mimamsa__Site: site, Mimamsa__Db: db, Mimamsa__Test__Enabled: "true",
      Mimamsa__Test__ResetState: "true", Mimamsa__Test__ResetLedger: "true", Mimamsa__Test__Users__0: "admin:Admin:admin-password-1",
      Mimamsa__Test__Users__1: "reader:User:reader-password-1", DOTNET_CLI_TELEMETRY_OPTOUT: "1", DOTNET_NOLOGO: "1" },
  };
}

if (!process.env.B1_SYN_SITE || !process.env.B1_SYN_DB) throw new Error("B1_SYN_SITE and B1_SYN_DB are required");
const projects = [{ name: "syn", testMatch: /journeys\.spec\.cjs/, use: { baseURL: "http://127.0.0.1:5302" } }];
const webServer = [server(5302, process.env.B1_SYN_SITE, process.env.B1_SYN_DB)];
if (process.env.B1_SAMPLE_SITE && process.env.B1_SAMPLE_DB) {
  projects.push({ name: "sample", testMatch: /sample\.spec\.cjs/, use: { baseURL: "http://127.0.0.1:5301" } });
  webServer.push(server(5301, process.env.B1_SAMPLE_SITE, process.env.B1_SAMPLE_DB));
}

module.exports = {
  testDir: __dirname,
  timeout: 90_000,
  expect: { timeout: 15_000 },
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [["list"], ["json", { outputFile: path.join(__dirname, "out", "results.json") }]],
  outputDir: path.join(__dirname, "out", "artifacts"),
  use: { headless: true, viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 2, trace: "off", screenshot: "off", video: "off",
         locale: "en-GB", timezoneId: "UTC" },
  projects, webServer,
};
