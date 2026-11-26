// Copies the pinned PDF.js distribution into the service's wwwroot (offline: no CDN, no network at run time).
// Source: ./node_modules/pdfjs-dist (after `npm ci --omit=optional` on a connected build host), or the directory
// given as the first argument / $PDFJS_DIST (an already-installed copy of the same pinned version).
import { cpSync, mkdirSync, rmSync, existsSync, readFileSync, readdirSync, statSync, writeFileSync } from "node:fs";
import { createHash } from "node:crypto";
import { join, dirname, relative } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const src = process.argv[2] || process.env.PDFJS_DIST || join(here, "node_modules", "pdfjs-dist");
const pkg = JSON.parse(readFileSync(join(src, "package.json"), "utf8"));
if (pkg.name !== "pdfjs-dist" || pkg.version !== "6.5.438") throw new Error(`expected pdfjs-dist 6.5.438, found ${pkg.name} ${pkg.version}`);
const dst = join(here, "..", "src", "Mimamsa.Web", "wwwroot", "vendor", "pdfjs");
if (existsSync(dst)) rmSync(dst, { recursive: true });
mkdirSync(dst, { recursive: true });
for (const f of ["build/pdf.min.mjs", "build/pdf.worker.min.mjs", "LICENSE"]) cpSync(join(src, f), join(dst, f.split("/").pop()));
for (const d of ["cmaps", "standard_fonts", "wasm", "iccs"]) if (existsSync(join(src, d))) cpSync(join(src, d), join(dst, d), { recursive: true });
const files = [];
const walk = (d) => { for (const n of readdirSync(d)) { const p = join(d, n); statSync(p).isDirectory() ? walk(p) : files.push(p); } };
walk(dst);
const sums = files.sort().map((p) => `${createHash("sha256").update(readFileSync(p)).digest("hex")}  ${relative(dst, p).split("\\").join("/")}`);
writeFileSync(join(dst, "SHA256SUMS"), sums.join("\n") + "\n");
console.log(`pdfjs-dist ${pkg.version}: ${files.length} files copied to ${dst}`);
