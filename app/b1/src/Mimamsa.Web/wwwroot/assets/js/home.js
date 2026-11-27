// C14 S3: library home (shown in the document pane while no document is open) and the early Commander task home.
// Recent searches and documents are kept in memory for this page session only: nothing is written to browser storage
// (client policy: sessionStorage holds only pane_widths, rail_collapsed, view_mode and theme; no query text is stored).
import { api } from "./api.js";
import { h, append, clear, chip, fmtDate, typeLabel } from "./ui.js";

const add = (el, ...k) => append(el, k);
const recent = { searches: [], docs: [] };
let library = null, libGen = 0;

/** Codex review of PR #70: after a policy change the cached library payload (statute shortcuts, Commander task
 *  provisions) may name withdrawn content, so it is dropped; a load that was in flight when it was dropped is
 *  discarded instead of being cached, and the caller re-renders the home with a fresh payload. */
export function invalidateLibrary() { library = null; libGen++; }

export function noteRecentSearch(q) {
  q = (q || "").trim();
  if (!q) return;
  recent.searches = [q, ...recent.searches.filter((x) => x !== q)].slice(0, 6);
}
export function noteRecentDoc(docId, title) {
  if (!docId) return;
  recent.docs = [{ docId, title: title || docId }, ...recent.docs.filter((x) => x.docId !== docId)].slice(0, 6);
}
export function resetRecent() { recent.searches = []; recent.docs = []; library = null; }

function go(nav, url) { return (e) => { e.preventDefault(); nav.go(url); }; }
function runQuery(q) {
  return (e) => {
    e.preventDefault();
    const box = document.getElementById("q"); const form = document.getElementById("searchform");
    if (!box || !form) return;
    box.value = q; form.requestSubmit();
  };
}

export async function renderHome(pane, { nav, commander, openDoc }) {
  const root = h("section.home", { "aria-label": commander ? "Commander workspace" : "Library home" }, h("span.skeleton.w60"), h("span.skeleton.w40"));
  add(pane, root);
  const gen = libGen;
  let L0;
  try { L0 = library || await api("/api/library"); }
  catch { clear(root); add(root, keyHint()); return; }
  if (gen !== libGen) return;          // superseded by a policy change: the refresh renders the home again
  library = L0;
  if (!root.isConnected) return;
  clear(root);
  if (commander) return commanderHome(root, library, nav);
  const L = library;
  add(root,
    h("header.home-head", h("h2", "Library"),
      h("p.home-summary", `${L.documents.toLocaleString("en-GB")} documents · ${L.pages.toLocaleString("en-GB")} pages`,
        L.years ? ` · ${L.years.from}–${L.years.to}` : "", ` · release ${L.release.release_id} (${fmtDate(L.release.created_at)})`)),
    h("div.home-grid",
      h("div.home-card", h("h3", "What is held"),
        h("ul.home-counts", L.by_type.map((t) => h("li", h("span", typeLabel(t.type)), h("span.count", t.count.toLocaleString("en-GB"))))),
        L.by_court.length ? h("ul.home-counts", L.by_court.map((c) => h("li", h("span", c.court), h("span.count", c.count.toLocaleString("en-GB"))))) : null,
        L.unreliable_text ? h("p.muted", chip("warning", "Extracted text unreliable"), ` ${L.unreliable_text} copies (legacy-font Hindi). Their originals can be read; their text is not searched.`) : null),
      h("div.home-card", h("h3", "Statutes"),
        h("ul.home-links", L.shortcuts.map((s) => h("li", h("a", { href: `/s/${encodeURIComponent(s.primary_doc)}`, onclick: go(nav, `/s/${encodeURIComponent(s.primary_doc)}`) }, s.title),
          h("span.muted", ` ${s.category}`)))),
        h("p", h("a", { href: "/s", onclick: go(nav, "/s") }, "All Acts, Rules and Regulations →"))),
      h("div.home-card", h("h3", "Recent in this session"),
        recent.docs.length ? h("ul.home-links", recent.docs.map((d) => h("li", h("a", { href: "#", onclick: (e) => { e.preventDefault(); openDoc(d.docId); } }, d.title)))) : h("p.muted", "No documents opened yet."),
        recent.searches.length ? h("ul.home-links", recent.searches.map((q) => h("li", h("a", { href: "#", onclick: runQuery(q) }, h("span.mono", q))))) : h("p.muted", "No searches yet."),
        h("p.sr-hint", "Kept in this page only; nothing is stored in the browser.")),
      h("div.home-card", h("h3", "Try"),
        h("ul.home-links", L.examples.map((q) => h("li", h("a", { href: "#", onclick: runQuery(q) }, h("span.mono", q))))),
        keyHint())));
}

function keyHint() {
  return h("p.muted.home-hint", "No document open. ", h("kbd", "Enter"), " opens the selected result, ", h("kbd", "O"), " a new tab, ", h("kbd", "Space"), " a preview. ",
    "Originals are delivered in bounded, authenticated byte ranges and are never stored in the browser.");
}

function commanderHome(root, L, nav) {
  add(root,
    h("header.home-head", h("h2", "Commander workspace ", chip("candidate", "Early")),
      h("p.home-summary", L.commander_note)),
    h("div.home-grid", L.commander_tasks.map((t) => h("div.home-card.task", { "data-task": t.task },
      h("h3", t.task), h("p.muted", t.purpose),
      h("ul.task-items", t.items.map((it) => h("li",
        it.found
          ? h("a", { href: `/s/${encodeURIComponent(it.doc_id)}/${encodeURIComponent(it.number)}`, onclick: go(nav, `/s/${encodeURIComponent(it.doc_id)}/${encodeURIComponent(it.number)}`) },
              h("span.num", `${it.kind} ${it.number}`), h("span", it.heading || ""))
          : h("span.muted", `${it.kind} ${it.number}: not found in the held copy`),
        it.found ? h("span.muted.task-src", `${it.instrument || ""}${it.page ? ` · p.${it.page}` : ""}${it.omitted_as_printed ? " · printed as omitted" : ""}`) : null))))),
      h("div.home-card.task", { "data-task": "Forms" }, h("h3", "Forms"),
        h("p.muted", "Forms printed in the held Rules can be found by search. Forms are not extracted as separate records yet."),
        h("ul.task-items", h("li", h("a", { href: "#", onclick: runQuery("\"form\" act:\"Army Rules\"") }, "Search the Army Rules for printed forms"))))),
    h("p.sr-hint", "The same search and documents as the Practitioner view; this page only organises held provisions by task."));
}
