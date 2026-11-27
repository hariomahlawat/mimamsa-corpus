// Shell, router and keymap (app/design/02 §2-4, 05 §2, keymap.json). Client policy: no localStorage/IndexedDB/
// service worker; sessionStorage only for pane_widths, rail_collapsed, view_mode, theme; no query text stored.
import { api, probe, noteEpoch, state as apiState } from "./api.js";
import { h, append, clear, $, toast, announce, openDialog, session, fmtDate } from "./ui.js";
import * as research from "./research.js";
import { loginPage, gatePage, laterPage, statutesPage, citePage, adminPage } from "./pages.js";
import { noteRecentSearch, invalidateLibrary } from "./home.js";
import { commanderPage, studioPage, refreshWorkspace, workspaceShown } from "./workspace.js";
import { refreshRelations, liveRelationViews, relationsRefreshPending } from "./relations.js";
const add = (el, ...k) => append(el, k);

const main = $("#main");
let S = null;               // session
let gPending = 0;           // "G then X" sequence timer
window.__mimamsaNoSingleKeys = false;

const nav = {
  go(url) { history.pushState({}, "", url); route(); },
  replace(url) { if (location.pathname + location.search !== url) history.replaceState({}, "", url); },
};
window.addEventListener("popstate", () => route());
// Review (PR #57): on an expired or rejected session every trace of the previous user's research context is destroyed
// before the login page appears (viewers, tabs, cached metadata, results, pending requests, the search field).
function clearUserState() {
  research.resetResearch();
  const q = document.getElementById("q"); if (q) q.value = "";
  document.querySelectorAll("dialog[open]").forEach((d) => d.close());
}
window.addEventListener("mimamsa:unauthenticated", () => {
  if (!S) return;
  S = null; apiState.session = null; clearUserState();
  history.replaceState({}, "", "/r");
  renderShell(); loginPage(main, onLogin, "Your session has ended. Sign in again.");
});

// C14 F05: a change of serving-policy epoch (seen on any API response) re-checks the open documents at once; while
// documents are open, the epoch is also polled so pages already on screen are cleared within about 10 seconds even
// when the reader does nothing. The poll does not refresh the session.
// Relationship evidence on screen (Statutes section view, instrument overview, context pane) is refreshed too, and the
// poll also runs while such evidence is displayed (Codex review of PR #70).
// The library home (statute shortcuts, Commander task provisions) is re-fetched too, and the poll also runs while the
// home is displayed (Codex review of PR #70).
// C15: the Commander workspace and Studio pages re-render too (library-derived content follows withdrawals).
window.addEventListener("mimamsa:policy-changed", () => { if (S) { research.revalidateOpenDocuments(); refreshRelations(); invalidateLibrary(); research.refreshHome(); refreshWorkspace(); } });
const POLICY_POLL_MS = 10_000;
setInterval(async () => {
  if (!S || document.hidden || !(research.openDocumentCount() || liveRelationViews() || document.querySelector("section.home") || workspaceShown())) return;
  // plain fetch: the poll only reads the epoch; it never changes the connection or session state shown to the user
  try { noteEpoch(await fetch("/api/policy", { credentials: "same-origin", cache: "no-store" })); } catch { /* next tick */ }
  // a re-check that could not decide after an earlier epoch change is retried on every tick until it resolves
  if (research.hasPendingRecheck()) research.revalidateOpenDocuments();
  if (relationsRefreshPending()) refreshRelations();
}, POLICY_POLL_MS);

// ------------------------------------------------------------------ shell
function applyTheme() {
  const t = session.get("theme");
  if (t === "light" || t === "dark") document.documentElement.dataset.theme = t; else delete document.documentElement.dataset.theme;
}
function applyView() {
  const v = session.get("view_mode") === "commander" ? "commander" : "practitioner";
  document.body.classList.toggle("commander", v === "commander");
  $("#view-practitioner").setAttribute("aria-pressed", String(v === "practitioner"));
  $("#view-commander").setAttribute("aria-pressed", String(v === "commander"));
}
$("#view-practitioner").addEventListener("click", () => { session.set("view_mode", "practitioner"); applyView(); if (research.R.el) { research.R.el.classList.remove("no-ctx"); } route(); });
$("#view-commander").addEventListener("click", () => { session.set("view_mode", "commander"); applyView(); if (research.R.el) research.R.el.classList.add("no-ctx"); route(); });

function renderShell() {
  const rel = S?.release;
  $("#banner-text").textContent = rel?.banner || "Research and candidate data. Not legally verified.";
  $("#banner-meta").textContent = rel ? `AUTH-LEDGER v${rel.auth_ledger_version} · Release ${rel.release_id}` : "";
  const dev = (S?.degraded || []).map((d) => d.text).join(" ");
  $("#banner-dev").textContent = dev; $("#banner-dev").hidden = !dev; $("#banner").title = [$("#banner-text").textContent, dev].filter(Boolean).join(" ");
  const deg = $("#degraded");
  clear(deg);
  const items = [];   // C14 S3: one banner line; the development-key statement moved onto it (#banner-dev)
  if (!apiState.online) items.unshift("Connection to the server lost. Retrying.");
  deg.hidden = !items.length;
  for (const t of items) add(deg, h("span", t));
  const ws = clear($("#workspaces"));
  const path = location.pathname;
  const link = (href, label, current, extra) => h("a", { href, "aria-current": current ? "page" : null, onclick: (e) => { e.preventDefault(); nav.go(href); } }, extra, h("span.wlabel", label));
  if (S) {
    add(ws, link("/r", "Research", path === "/r" || path.startsWith("/d/") || path.startsWith("/cite/")),
      link("/s", "Statutes", path.startsWith("/s")), link("/g", "Graph", path.startsWith("/g")),
      link("/c", "Commander", path === "/c" || path.startsWith("/c/")), link("/studio", "Studio", path.startsWith("/studio")),
      link("/assistant", "Assistant", path.startsWith("/assistant"), h("span.chip.chip-gated", { style: "height:16px", title: "Closed" }, "")));
    if (S.role === "Admin") add(ws, link("/admin", "Administration", path.startsWith("/admin")));
  }
  const um = clear($("#usermenu"));
  if (S) {
    const btn = h("button.btn", { type: "button", "aria-haspopup": "true", "aria-expanded": "false" }, `${S.user} · ${S.role}`);
    const panel = h("div.menu-panel", { hidden: true, role: "menu" },
      h("div.menu-info", `Signed in as ${S.user} (${S.role})`),
      h("div.menu-info", `Release ${rel.release_id} · HF ${rel.hf_revision_short}`),
      h("hr"),
      h("button", { role: "menuitemcheckbox", "aria-checked": String(window.__mimamsaNoSingleKeys), onclick: () => { window.__mimamsaNoSingleKeys = !window.__mimamsaNoSingleKeys; announce(window.__mimamsaNoSingleKeys ? "Single-key shortcuts off (screen-reader mode)" : "Single-key shortcuts on"); closeMenu(); renderShell(); } },
        window.__mimamsaNoSingleKeys ? "✓ Screen-reader mode (single-key shortcuts off)" : "Screen-reader mode (turn single-key shortcuts off)"),
      h("button", { role: "menuitem", onclick: () => { const t = document.documentElement.dataset.theme === "dark" || (!document.documentElement.dataset.theme && matchMedia("(prefers-color-scheme: dark)").matches) ? "light" : "dark"; session.set("theme", t); applyTheme(); closeMenu(); } }, "Switch light / dark theme"),
      h("button", { role: "menuitem", onclick: () => { closeMenu(); help(); } }, "Keyboard shortcuts (?)"),
      h("hr"),
      h("button", { role: "menuitem", onclick: async () => { try { await api("/api/logout", { method: "POST" }); } catch { /* ignore */ } S = null; apiState.session = null; clearUserState(); renderShell(); loginPage(main, onLogin, "You have signed out."); } }, "Sign out"));
    const closeMenu = () => { panel.hidden = true; btn.setAttribute("aria-expanded", "false"); };
    btn.addEventListener("click", () => { panel.hidden = !panel.hidden; btn.setAttribute("aria-expanded", String(!panel.hidden)); if (!panel.hidden) panel.querySelector("button").focus(); });
    panel.addEventListener("keydown", (e) => { if (e.key === "Escape") { closeMenu(); btn.focus(); } });
    document.addEventListener("click", (e) => { if (!um.contains(e.target)) closeMenu(); });
    add(um, btn, panel);
  }
  const ft = clear($("#footer"));
  if (rel) add(ft, h("span", `Release ${rel.release_id}`), h("span", `created ${fmtDate(rel.created_at)}`), h("span", `HF ${rel.hf_revision_short}`),
    h("span", `generation ${rel.generation}`), h("span.conn" + (apiState.online ? "" : ".lost"), apiState.online ? "connected" : "connection lost"),
    h("span", "Lexical search · no generative AI"));
  $("#searchform").hidden = !S;
}
apiState.listeners.add((online) => {
  renderShell();
  if (!online) {
    // shared-desktop policy: open views are blanked to a reconnecting notice; nothing is shown from cache
    research.R.tabs.forEach((t) => t.viewer && t.viewer.destroy());
    research.R.tabs = []; research.R.result = null; research.R.el = null;
    clear(main); add(main, h("div.page", h("div.error-state", { role: "alert" }, h("h2", "Connection to the server lost"), h("p", "Retrying. Open views have been cleared; nothing is shown from cache and no changes are sent until the connection returns."))));
    const t = setInterval(async () => { if (await probe()) { clearInterval(t); route(); } }, 2000);
  }
});

// ------------------------------------------------------------------ router
async function route() {
  if (!S) return;
  const u = new URL(location.href);
  const p = u.pathname;
  renderShell();
  if (p === "/" || p === "/login") { nav.replace("/r"); return route(); }
  if (p === "/r" || p.startsWith("/d/")) {
    research.paramsFromUrl(u);
    $("#q").value = research.R.query;
    research.mountResearch(main, nav);
    if (document.body.classList.contains("commander")) research.R.el.classList.add("no-ctx");
    if (p === "/r") research.refreshHome();   // mountResearch keeps an existing shell, so a view switch must redraw the home
    await research.runSearch({ push: false });
    if (p.startsWith("/d/")) {
      const docId = decodeURIComponent(p.slice(3));
      const copy12 = u.searchParams.get("copy");
      const page = parseInt(u.searchParams.get("p") || "1", 10);
      if (copy12) {
        // ASR-E06: a copy named in the URL is resolved through the same citation and eligibility resolver; the
        // current edition is never substituted for it.
        let r;
        try { r = await api(`/api/cite?doc=${encodeURIComponent(docId)}&sha=${encodeURIComponent(copy12)}&page=${page}`); }
        catch { r = { state: "CITED_COPY_UNAVAILABLE", notice: "The cited copy is not available in this installation." }; }
        if (r.state === "CITED_COPY_ELIGIBLE" || r.state === "CITED_COPY_ELIGIBLE_NOT_CURRENT") {
          await research.openDocument({ docId, page: r.page, passage: r.state === "CITED_COPY_ELIGIBLE" ? u.searchParams.get("a") : null,
            copy: r.state === "CITED_COPY_ELIGIBLE" ? null : r.copy, notice: r.notice || null, citeState: r.state, currentCopy: r.current_copy,
            copyPages: r.copy_pages, firstRelease: r.first_release }, { push: false });
        } else {
          research.showDocNotice(r.notice, r.state);
        }
        return;
      }
      await research.openDocument({ docId, page, passage: u.searchParams.get("a"), copy: null }, { push: false });
    }
    return;
  }
  research.R.el = null;
  if (p.startsWith("/cite/")) return citePage(main, nav, p.slice(6).split("/").map(decodeURIComponent));
  if (p === "/s" || p.startsWith("/s/")) { const [docId, sec] = p.slice(3).split("/").map(decodeURIComponent); return statutesPage(main, nav, docId || null, sec || null); }
  if (p.startsWith("/admin")) return S.role === "Admin" ? adminPage(main, nav) : forbidden();
  if (p.startsWith("/assistant")) return gatePage(main, "assistant");
  if (p.startsWith("/g")) return laterPage(main, "Graph", "The citation graph workspace (canvas with a synchronised list view) is a later milestone (B3). In B1, extracted citations of a document are listed in its Cited/Citing tab, labelled as candidates.");
  if (p === "/c" || p.startsWith("/c/")) return commanderPage(main, nav, p.length > 3 ? decodeURIComponent(p.slice(3)) : null);
  if (p === "/studio" || p.startsWith("/studio/")) return studioPage(main, nav, p.length > 8 ? decodeURIComponent(p.slice(8)) : null);
  clear(main); add(main, h("div.page", h("h1", "Not found"), h("p", h("a", { href: "/r" }, "Go to research"))));
}
function forbidden() { clear(main); add(main, h("div.page", h("div.error-state", { role: "alert" }, h("h2", "This action is for Admins.")))); }

// ------------------------------------------------------------------ search form
$("#searchform").addEventListener("submit", (e) => {
  e.preventDefault();
  const q = $("#q").value;
  research.R.query = q; research.R.plainConfirmed = false; noteRecentSearch(q);
  if (!location.pathname.startsWith("/r") && !location.pathname.startsWith("/d/")) { history.pushState({}, "", "/r?q=" + encodeURIComponent(q)); return route(); }
  research.mountResearch(main, nav);
  research.runSearch();
  if (e.submitter === undefined && window.__ctrlEnter) { window.__ctrlEnter = false; }
});
$("#q").addEventListener("keydown", (e) => {
  if (e.key === "Escape") { $("#q").blur(); research.R.el?.querySelector("#results-list")?.focus(); }
  if (e.key === "Enter" && e.ctrlKey) { e.preventDefault(); research.R.query = $("#q").value; research.runSearch(); toast("Search run; open a result with O to use a new tab"); }
});

// ------------------------------------------------------------------ keymap (keymap.json v0.2)
function editable(t) { return t && (t.closest("input, textarea, select, [contenteditable=true]") !== null); }
function help() {
  const rows = [["/", "Focus search"], ["?", "Shortcut help"], [":", "Command palette"], ["G then R / S / G / D / A", "Research / Statutes / Graph / Studio / Administration"],
    [". / ,", "Next / previous pane"], ["B / Shift+B", "Toggle filters / context pane"], ["] / [", "Next / previous document tab"], ["J / K or ↓ / ↑", "Next / previous result"],
    ["Enter / O / Space", "Open / open in new tab / preview"], ["N / Shift+N", "Next / previous hit in document"], ["P", "Go to page"], ["C / Shift+C", "Copy legal citation / internal reference"],
    ["T", "Toggle Original / Text"], ["E", "Open Evidence panel"], ["X", "Close document tab"], ["M", "New note (not in B1)"], ["Esc", "Leave field, close popover"],
    ["Ctrl+Enter (search field)", "Run search"], ["←/→, Shift+←/→, Home/End, Enter (on a divider)", "Resize, collapse, expand, reset pane"]];
  openDialog("Keyboard shortcuts", h("div.help", h("p.muted", "Single-key shortcuts work when focus is not in a text field and can be turned off (user menu, screen-reader mode). Browser keys such as F3, F6 and Ctrl+F stay native."),
    h("table", h("tbody", rows.map(([k, v]) => h("tr", h("td", h("kbd", k)), h("td", v)))))));
}
function palette() {
  const actions = [["Go to Research", () => nav.go("/r")], ["Go to Statutes", () => nav.go("/s")], ["Open Commander assistant (closed)", () => nav.go("/assistant")],
    ["Toggle filters", () => research.R.el && research.toggleRail()], ["Toggle context pane", () => research.R.el && research.toggleCtx()],
    ["Copy legal citation", () => research.copyCitation(false)], ["Copy internal reference", () => research.copyCitation(true)], ["Toggle Original / Text", () => research.setView("toggle")],
    ["Keyboard shortcuts", help], ["Switch to Commander view", () => $("#view-commander").click()], ["Switch to Practitioner view", () => $("#view-practitioner").click()]];
  if (S?.role === "Admin") actions.push(["Go to Administration", () => nav.go("/admin")]);
  const input = h("input", { type: "text", "aria-label": "Filter commands", placeholder: "Type to filter commands" });
  const list = h("ul", { role: "listbox", "aria-label": "Commands" });
  let sel = 0, shown = actions;
  const draw = () => { clear(list); shown.forEach(([l], i) => add(list, h("li", { role: "option", "aria-selected": String(i === sel), onclick: () => run(i) }, l))); };
  const run = (i) => { document.getElementById("dialog").close(); shown[i]?.[1](); };
  input.addEventListener("input", () => { const q = input.value.toLowerCase(); shown = actions.filter(([l]) => l.toLowerCase().includes(q)); sel = 0; draw(); });
  input.addEventListener("keydown", (e) => { if (e.key === "ArrowDown") { sel = Math.min(shown.length - 1, sel + 1); draw(); e.preventDefault(); } else if (e.key === "ArrowUp") { sel = Math.max(0, sel - 1); draw(); e.preventDefault(); } else if (e.key === "Enter") { e.preventDefault(); run(sel); } });
  draw();
  openDialog("Command palette", h("div.palette", input, list));
}
function cyclePane(d) {
  const regions = ["#rail", "#results-list", "#viewer", "#ctx-body", ".divider.d1", ".divider.d2"].map((s) => $(s)).filter((x) => x && x.offsetParent !== null);
  const order = ["#rail", ".divider.d1", "#results-list", "#viewer", ".divider.d2", "#ctx-body"].map((s) => $(s)).filter((x) => regions.includes(x));
  if (!order.length) return;
  const i = order.findIndex((x) => x.contains(document.activeElement));
  const next = order[(i + d + order.length) % order.length];
  if (!next.hasAttribute("tabindex") && !["BUTTON", "A", "INPUT"].includes(next.tagName)) next.setAttribute("tabindex", "-1");
  next.focus();
}

document.addEventListener("keydown", (e) => {
  if (!S) return;
  if (document.querySelector("dialog[open]")) return;
  if (e.ctrlKey || e.metaKey || e.altKey) return;
  if (editable(e.target)) return;
  if (window.__mimamsaNoSingleKeys && e.key !== "Escape") return;
  const k = e.key;
  if (gPending) {
    clearTimeout(gPending); gPending = 0;
    const map = { r: "/r", s: "/s", g: "/g", d: "/studio", a: "/admin" };
    if (map[k.toLowerCase()]) { e.preventDefault(); if (k.toLowerCase() !== "a" || S.role === "Admin") nav.go(map[k.toLowerCase()]); }
    return;
  }
  const inResults = e.target.closest?.("#results-list");
  const docOpen = !!research.currentDoc();
  const act = (f) => { e.preventDefault(); f(); };
  switch (k) {
    case "/": return act(() => { $("#q").focus(); $("#q").select(); });
    case "?": return act(help);
    case ":": return act(palette);
    case "g": case "G": if (!e.shiftKey) { e.preventDefault(); gPending = setTimeout(() => { gPending = 0; }, 1200); } return;
    case ".": return act(() => cyclePane(1));
    case ",": return act(() => cyclePane(-1));
    case "b": return research.R.el ? act(research.toggleRail) : undefined;
    case "B": return research.R.el ? act(research.toggleCtx) : undefined;
    case "]": return act(() => research.cycleTab(1));
    case "[": return act(() => research.cycleTab(-1));
    case "j": case "ArrowDown": if (research.R.el && !inResults && research.hasResults() && (k === "j" || e.target === document.body)) return act(() => research.moveSelection(1)); return;
    case "k": case "ArrowUp": if (research.R.el && !inResults && research.hasResults() && (k === "k" || e.target === document.body)) return act(() => research.moveSelection(-1)); return;
    case "n": return docOpen ? act(() => research.nextHit(1)) : undefined;
    case "N": return docOpen ? act(() => research.nextHit(-1)) : undefined;
    case "p": return docOpen ? act(research.focusPageInput) : undefined;
    case "c": return docOpen ? act(() => research.copyCitation(false)) : undefined;
    case "C": return docOpen ? act(() => research.copyCitation(true)) : undefined;
    case "t": return docOpen ? act(() => research.setView("toggle")) : undefined;
    case "e": return docOpen ? act(() => research.openCtxTab("evidence")) : undefined;
    case "x": return docOpen ? act(() => research.closeTab()) : undefined;
    case "m": return docOpen ? act(() => toast("Private notes are not part of the B1 prototype.")) : undefined;
    case "Escape": $$popovers(); return;
    default: return;
  }
});
function $$popovers() { document.querySelectorAll(".menu-panel").forEach((p) => { p.hidden = true; }); research.R.el?.classList.remove("rail-open", "ctx-open", "results-open"); }

// ------------------------------------------------------------------ boot
function onLogin(s) { S = s; apiState.session = s; renderShell(); if (location.pathname === "/login" || location.pathname === "/") nav.replace("/r"); route(); }
async function boot() {
  applyTheme(); applyView();
  try { S = await api("/api/session"); apiState.session = S; }
  catch (e) {
    S = null;
    const rel = e.body?.release;
    if (rel) { $("#banner-text").textContent = rel.banner; $("#banner-meta").textContent = `AUTH-LEDGER v${rel.auth_ledger_version} · Release ${rel.release_id}`; }
    renderShell();
    if (e.status === 0) { clear(main); add(main, h("div.page", h("div.error-state", { role: "alert" }, h("h2", "The server cannot be reached"), h("p", "Retrying…")))); setTimeout(boot, 2000); return; }
    return loginPage(main, onLogin);
  }
  renderShell();
  route();
}
setInterval(() => { if (S) probe(); }, 15000);
boot();
