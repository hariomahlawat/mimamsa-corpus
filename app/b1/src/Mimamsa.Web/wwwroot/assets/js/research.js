// Research workspace (app/design/03_RESEARCH_WORKSPACE.md): persistent search, grouped results with page-anchored
// excerpts, facets, document tabs with the protected original and the Text view, and the context pane
// (Evidence, Provenance, Related, Cited/Citing, Notes). Everything shown is a record, a verified-text excerpt, or a
// labelled automated candidate. No generated text.
import { api, ApiError, state as apiState } from "./api.js";
import { h, append, clear, $, $$, chip, candidateChip, axisChip, fmtDate, short, host, typeLabel, toast, announce, copyText, marked, session, icon, openDialog } from "./ui.js";
import { ProtectedViewer } from "./viewer.js";

const add = (el, ...k) => append(el, k);
export const R = {
  query: "", filters: emptyFilters(), result: null, flat: false, sort: "relevance", selected: -1, plainConfirmed: false,
  tabs: [], active: -1, ctxTab: "evidence", ctxOpen: false, railOpen: false, resultsOpen: false, el: null, reqSeq: 0, abort: null,
};

function emptyFilters() { return { type: new Set(), court: new Set(), status: new Set(), year_from: "", year_to: "" }; }

// ------------------------------------------------------------------ URL state
export function paramsFromUrl(url) {
  const sp = url.searchParams;
  R.query = sp.get("q") || "";
  R.filters = emptyFilters();
  for (const k of ["type", "court", "status"]) for (const v of sp.getAll(k)) R.filters[k].add(v);
  R.filters.year_from = sp.get("year_from") || ""; R.filters.year_to = sp.get("year_to") || "";
  R.plainConfirmed = sp.get("plain") === "1";
}
function searchParams() {
  const sp = new URLSearchParams();
  if (R.query) sp.set("q", R.query);
  for (const k of ["type", "court", "status"]) for (const v of R.filters[k]) sp.append(k, v);
  if (R.filters.year_from) sp.set("year_from", R.filters.year_from);
  if (R.filters.year_to) sp.set("year_to", R.filters.year_to);
  if (R.plainConfirmed) sp.set("plain", "1");
  return sp;
}
export function researchUrl() { const s = searchParams().toString(); return "/r" + (s ? "?" + s : ""); }

// ------------------------------------------------------------------ layout
export function mountResearch(main, nav) {
  R.nav = nav;
  if (R.el && main.contains(R.el)) return R.el;
  clear(main);
  const widths = JSON.parse(session.get("pane_widths") || "{}");
  const el = h("div.research#research", { style: [widths.results ? `--results-w:${widths.results}px` : "", widths.ctx ? `--ctx-w:${widths.ctx}px` : ""].join(";") },
    h("aside.pane.rail#rail", { "aria-label": "Filters" },
      h("button.icon-btn.rail-toggle", { type: "button", "aria-label": "Show filters (B)", title: "Filters (B)", onclick: () => toggleRail() }, icon("filter")),
      h("h2", "Filters"), h("div#facets")),
    h("section.pane.results#results", { "aria-label": "Search results" },
      h("div.results-head#results-head"), h("div.results-list#results-list", { role: "listbox", "aria-label": "Results", tabindex: "0" })),
    divider("d1", "results"),
    h("section.pane.docpane#docpane", { "aria-label": "Document" }),
    divider("d2", "ctx"),
    h("aside.pane.ctx#ctx", { "aria-label": "Context" }));
  if (session.get("rail_collapsed") === "1") el.classList.add("rail-collapsed");
  add(main, el);
  R.el = el;
  $("#results-list").addEventListener("keydown", resultsKeys);
  renderDocPane();
  return el;
}

function divider(cls, which) {
  const d = h(`button.divider.${cls}`, { type: "button", "aria-label": which === "results" ? "Resize results pane" : "Resize context pane", title: "Drag, or use arrow keys (Shift for 64 px), Home/End, Enter resets" });
  const varName = which === "results" ? "--results-w" : "--ctx-w";
  const def = which === "results" ? 400 : 320, min = which === "results" ? 320 : 280;
  const cur = () => parseInt(getComputedStyle(R.el).getPropertyValue(varName)) || def;
  const set = (v) => {
    v = Math.max(min, Math.min(760, v)); R.el.style.setProperty(varName, v + "px");
    const w = JSON.parse(session.get("pane_widths") || "{}"); w[which] = v; session.set("pane_widths", JSON.stringify(w));
  };
  d.addEventListener("keydown", (e) => {
    const sign = which === "results" ? 1 : -1;
    if (e.key === "ArrowLeft" || e.key === "ArrowRight") { e.preventDefault(); set(cur() + (e.key === "ArrowRight" ? 1 : -1) * sign * (e.shiftKey ? 64 : 16)); }
    else if (e.key === "Home") { e.preventDefault(); set(min); }
    else if (e.key === "End") { e.preventDefault(); set(760); }
    else if (e.key === "Enter") { e.preventDefault(); set(def); }
  });
  d.addEventListener("pointerdown", (e) => {
    d.setPointerCapture(e.pointerId);
    const x0 = e.clientX, w0 = cur(), sign = which === "results" ? 1 : -1;
    const move = (ev) => set(w0 + (ev.clientX - x0) * sign);
    d.addEventListener("pointermove", move);
    d.addEventListener("pointerup", () => d.removeEventListener("pointermove", move), { once: true });
  });
  d.addEventListener("dblclick", () => set(def));
  return d;
}

export function toggleRail() {
  if (window.matchMedia("(max-width: 1599px)").matches) { R.el.classList.toggle("rail-open"); return; }
  R.el.classList.toggle("rail-collapsed");
  session.set("rail_collapsed", R.el.classList.contains("rail-collapsed") ? "1" : "0");
}
export function toggleCtx() {
  if (window.matchMedia("(max-width: 1599px)").matches) { R.el.classList.toggle("ctx-open"); R.ctxOpen = R.el.classList.contains("ctx-open"); }
  else R.el.classList.toggle("no-ctx");
}

// ------------------------------------------------------------------ search
export async function runSearch({ push = true } = {}) {
  const head = $("#results-head"), list = $("#results-list");
  if (!head) return;
  if (push) R.nav.replace(researchUrl());
  if (!R.query.trim()) { R.result = null; renderResults(); renderFacets(); return; }
  const seq = ++R.reqSeq;
  if (R.abort) R.abort.abort();
  R.abort = new AbortController();
  list.classList.add("dim");
  head.setAttribute("aria-busy", "true");
  const slow = setTimeout(() => { if (seq === R.reqSeq) { clear(list); list.classList.remove("dim"); for (let i = 0; i < 6; i++) add(list, h("div.rgroup", h("span.skeleton.w60"), h("span.skeleton.w80"), h("span.skeleton.w40"))); } }, 400);
  try {
    const res = await api("/api/search?" + searchParams().toString(), { signal: R.abort.signal });
    if (seq !== R.reqSeq) return;           // a later query won (UX-14)
    R.result = res; R.selected = -1;
    announce(res.state === "results" ? `${res.total_documents} documents, ${res.total_passages} passages` : res.state === "empty" ? "No published documents match" : "The query could not be read");
  } catch (e) {
    if (e.name === "AbortError" || seq !== R.reqSeq) return;
    R.result = { state: "error", error: e.message, status: e.status };
  } finally {
    clearTimeout(slow);
    if (seq === R.reqSeq) { list.classList.remove("dim"); head.removeAttribute("aria-busy"); }
  }
  renderResults(); renderFacets();
  syncTabsWithResult();
}

function filterChips() {
  const out = [];
  for (const k of ["type", "court", "status"]) for (const v of R.filters[k])
    out.push(h("span.qchip", h("span.qchip-kind", k), k === "type" ? typeLabel(v) : v,
      h("button", { type: "button", "aria-label": `Remove filter ${k} ${v}`, onclick: () => { R.filters[k].delete(v); runSearch(); } }, "×")));
  if (R.filters.year_from || R.filters.year_to)
    out.push(h("span.qchip", h("span.qchip-kind", "year"), `${R.filters.year_from || "…"}–${R.filters.year_to || "…"}`,
      h("button", { type: "button", "aria-label": "Remove year filter", onclick: () => { R.filters.year_from = R.filters.year_to = ""; runSearch(); } }, "×")));
  return out;
}

function renderResults() {
  const head = clear($("#results-head")), list = clear($("#results-list"));
  const r = R.result;
  if (!r) {
    add(head, h("strong", "Search the published library"));
    add(list, h("div.empty", h("p", "Type words, a phrase in quotes, or an identifier such as ", h("code", "s.69 Army Act"), ", ", h("code", "OA 411/2021"), " or ", h("code", "2013 INSC 408"), ". Identifiers are matched exactly and listed first."),
      h("p.muted", "Search is lexical (word and phrase matching). It does not answer questions and draws no legal conclusions."),
      h("p.muted", "Press ", h("kbd", "/"), " to focus the search field, ", h("kbd", "?"), " for all shortcuts.")));
    return;
  }
  if (r.state === "error") {
    add(head, h("strong", "Search did not run"));
    add(list, h("div.error-state", { role: "alert" }, h("h2", "The search could not be completed"),
      h("p", r.status === 0 ? "The connection to the server was lost. Nothing is shown from cache." : "The server returned an error. Your query has been kept."),
      h("p.mono", `Reference: SEARCH-${r.status || "NET"}-${Date.now().toString(36)}`), h("button.btn", { onclick: () => runSearch() }, "Try again")));
    return;
  }
  if (r.state === "parser_error") {
    add(head, h("strong", "The query could not be read"));
    const pos = Math.max(0, Math.min(R.query.length, r.error_position ?? 0));
    add(list, h("div.error-state", { role: "alert" }, h("h2", r.error || "Syntax error"),
      h("div.parse-echo", { "aria-label": `Query with the problem at character ${pos + 1}` }, R.query.slice(0, pos), h("span.caret", R.query.slice(pos, pos + 1) || " "), R.query.slice(pos + 1)),
      h("p", `Problem at character ${pos + 1}. Your query is kept unchanged in the search field. Nothing was searched.`),
      h("p", "You can correct it, or search the words only, without operators, phrases or fields:"),
      h("button.btn", { type: "button", onclick: () => { R.plainConfirmed = true; runSearch(); } }, "Search the words without operators")));
    return;
  }
  const docsCount = r.total_documents, pass = r.total_passages;
  add(head, 
    h("div.results-count", h("strong", r.state === "empty" ? "No results" : `${docsCount.toLocaleString("en-GB")} document${docsCount === 1 ? "" : "s"} · ${pass.toLocaleString("en-GB")} passage${pass === 1 ? "" : "s"}`),
      r.shown_passages < pass ? h("span.muted", `showing the first ${r.shown_passages} passages`) : null),
    h("div.runline", { "data-testid": "runline" }, `${r.run.mode_label} · semantic search ${r.run.semantic} · ${R.plainConfirmed ? "words only (operators removed on request) · " : ""}${[...R.filters.type, ...R.filters.court, ...R.filters.status].length + (R.filters.year_from || R.filters.year_to ? 1 : 0)} filter(s) · release ${r.run.release_id} · ${r.run.elapsed_ms} ms`),
    r.chips?.length ? h("div.chips-row", { "aria-label": "How the query was read" }, r.chips.map((c) => h("span.qchip", { title: c.source || "" }, h("span.qchip-kind", c.kind), c.text))) : null,
    filterChips().length ? h("div.chips-row", { "aria-label": "Active filters" }, filterChips()) : null,
    r.state === "results" ? h("div.results-tools",
      h("label", "Sort ", h("select", { onchange: (e) => { R.sort = e.target.value; renderResults(); } },
        h("option", { value: "relevance", selected: R.sort === "relevance" }, "Relevance"), h("option", { value: "new", selected: R.sort === "new" }, "Date, newest"), h("option", { value: "old", selected: R.sort === "old" }, "Date, oldest"))),
      h("label", h("input", { type: "checkbox", checked: R.flat, onchange: (e) => { R.flat = e.target.checked; renderResults(); } }), " Flat passages")) : null);
  if (r.state === "empty") {
    add(list, h("div.empty", h("h2", "No published documents match"),
      h("p", "Try fewer filters, or search the words without the section number."),
      filterChips().length ? [h("p", "Active filters:"), h("div.active-filters", filterChips())] : null,
      h("p.muted", "This is a statement about the published library in this installation only. It is not evidence that no authority exists.")));
    return;
  }
  const groups = [];
  const byDoc = new Map();
  for (const p of r.passages) {
    if (R.flat) { groups.push({ doc: r.documents[p.doc_id], hits: [p] }); continue; }
    if (!byDoc.has(p.doc_id)) { const g = { doc: r.documents[p.doc_id], hits: [] }; byDoc.set(p.doc_id, g); groups.push(g); }
    byDoc.get(p.doc_id).hits.push(p);
  }
  if (R.sort !== "relevance") groups.sort((a, b) => ((a.doc.issue_date || "") < (b.doc.issue_date || "") ? -1 : 1) * (R.sort === "new" ? -1 : 1));
  let idx = 0;
  for (const g of groups) {
    const d = g.doc;
    const shown = R.flat ? g.hits : g.hits.slice(0, 3);
    const li = h("div.rgroup", { "data-doc": d.doc_id },
      h("a.rgroup-title", { href: shown[0].link, onclick: (e) => { e.preventDefault(); openFromHit(shown[0], false); } }, d.title || d.doc_id),
      h("div.rgroup-meta", h("span", typeLabel(d.type)), d.language === "hi" ? h("span", { lang: "en" }, "Hindi text") : null, h("span", d.court || d.issuer || "Issuer not recorded"), d.issue_date ? h("span", fmtDate(d.issue_date)) : null,
        d.neutral_citation ? h("span.mono", d.neutral_citation) : null, (d.case_numbers || []).slice(0, 2).map((c) => h("span.mono", c)), d.number && !d.neutral_citation ? h("span", d.number) : null),
      h("div.rgroup-prov", { "aria-label": "Provenance" }, h("span", `Source ${host(d.source_url)}`), h("span.mono", `copy ${short(d.copy_sha256)}`),
        h("span", `retrieved ${fmtDate(d.retrieved_at) || "not recorded"}`), h("span", `corpus status: ${d.corpus_status} (display only)`),
        d.candidate_outcomes ? h("span", candidateChip("Candidate outcomes are automated and not verified"), " outcome candidates") : null));
    for (const p of shown) {
      const i = idx++;
      const states = [];
      if (p.ocr) states.push(chip("warning", "OCR", "OCR text: for search only. Quote from the original page."));
      if (p.low_confidence) states.push(chip("warning", "Low OCR confidence"));
      const reason = p.tier === "identifier" ? chip("checked", "Identifier", p.reasons.join("; "))
        : p.tier === "document" ? chip("reason", "Document match", p.reasons.join("; "))
        : p.tier === "title" ? chip("reason", "Title match", p.reasons.join("; "))
        : p.tier === "mention" ? chip("reason", "Mention", p.reasons.join("; ")) : chip("reason", "Lexical", p.reasons.join("; "));
      const row = h("div.hit", { role: "option", id: `hit-${i}`, "aria-selected": "false", "data-i": i, tabindex: "-1",
          onclick: () => { select(i); openFromHit(p, false); }, title: "Enter opens; O opens in a new tab; Space previews" },
        h("span.pg", p.page ? `p.${p.page}` : "", p.paragraph_label ? h("div", `¶${p.paragraph_label}`) : null),
        h("div", h("div.ex", p.truncated_start ? "… " : "", marked(p.snippet, p.highlights), p.truncated_end ? " …" : ""),
          h("div.meta", reason, states.length > 1 ? [states[0], h("span.chip.chip-neutral", { title: states.slice(1).map((s) => s.textContent).join(", "), tabindex: "0" }, `+${states.length - 1}`)] : states,
            h("span.why", p.reasons[0] || ""))));
      row._hit = p;
      add(li, row);
    }
    if (!R.flat && g.hits.length > 3) add(li, h("div.muted", { style: "font-size:12px;margin-top:4px" }, `${g.hits.length - 3} more passage(s) in this document`));
    add(list, li);
  }
}

function visibleHits() { return $$("#results-list .hit"); }
function select(i) {
  const rows = visibleHits();
  if (!rows.length) return;
  i = Math.max(0, Math.min(rows.length - 1, i));
  rows.forEach((r) => r.setAttribute("aria-selected", "false"));
  rows[i].setAttribute("aria-selected", "true");
  rows[i].scrollIntoView({ block: "nearest" });
  $("#results-list").setAttribute("aria-activedescendant", rows[i].id);
  R.selected = i;
}
export function moveSelection(delta) { select((R.selected < 0 ? -1 : R.selected) + delta); $("#results-list")?.focus({ preventScroll: true }); }
export function openSelected(mode) {
  const row = visibleHits()[R.selected];
  if (row) openFromHit(row._hit, mode === "new", mode === "preview");
}
function resultsKeys(e) {
  if (e.target.closest("input,select,textarea") || e.altKey || e.ctrlKey || e.metaKey) return;
  const k = e.key;
  if (k === "ArrowDown" || (k === "j" && !window.__mimamsaNoSingleKeys)) { e.preventDefault(); moveSelection(1); }
  else if (k === "ArrowUp" || (k === "k" && !window.__mimamsaNoSingleKeys)) { e.preventDefault(); moveSelection(-1); }
  else if (k === "Enter") { e.preventDefault(); openSelected("current"); }
  else if (k === "o" && !window.__mimamsaNoSingleKeys) { e.preventDefault(); openSelected("new"); }
  else if (k === " ") { e.preventDefault(); openSelected("preview"); }
}

// ------------------------------------------------------------------ facets
function renderFacets() {
  const box = clear($("#facets"));
  const r = R.result;
  const commander = document.body.classList.contains("commander");
  if (!r || r.state !== "results" && !(r.state === "empty" && (filterChips().length))) { add(box, h("p.muted", { style: "font-size:13px" }, "Filters appear with results.")); return; }
  const facets = r.facets || {};
  const group = (key, label, fmt = (v) => v) => {
    const vals = facets[key] || [];
    if (!vals.length && !R.filters[key]?.size) return null;
    const fs = h("fieldset.facet", h("legend", label));
    const showAll = fs.dataset.all === "1";
    vals.slice(0, 8).forEach((v) => {
      const id = `f-${key}-${v.value}`.replace(/[^\w-]/g, "_");
      add(fs, h("label", { for: id }, h("input", { type: "checkbox", id, checked: R.filters[key].has(v.value),
        onchange: (e) => { e.target.checked ? R.filters[key].add(v.value) : R.filters[key].delete(v.value); runSearch(); } }), fmt(v.value), h("span.count", v.count.toLocaleString("en-GB"))));
    });
    if (vals.length > 8) add(fs, h("button.btn-quiet.btn-small.more", { type: "button", onclick: () => openDialog(label, h("div", { style: "max-height:60vh;overflow:auto" }, vals.map((v) =>
      h("label", { style: "display:flex;gap:8px;min-height:26px;align-items:center" }, h("input", { type: "checkbox", checked: R.filters[key].has(v.value),
        onchange: (e) => { e.target.checked ? R.filters[key].add(v.value) : R.filters[key].delete(v.value); } }), fmt(v.value), h("span.muted", `(${v.count})`)))),
      [h("button.btn.btn-primary", { onclick: () => { document.getElementById("dialog").close(); runSearch(); } }, "Apply")]) }, `Show all ${vals.length}`));
    void showAll;
    return fs;
  };
  add(box, group("type", "Document type", typeLabel));
  if (!commander) add(box, group("court", "Court or issuer"));
  const years = (facets.year || []).map((v) => +v.value).filter(Boolean);
  const yf = h("fieldset.facet", h("legend", "Year"),
    h("div.yearrange", h("label.visually-hidden", { for: "yf" }, "From year"), h("input#yf", { inputmode: "numeric", placeholder: years.length ? String(Math.min(...years)) : "from", value: R.filters.year_from }),
      "–", h("label.visually-hidden", { for: "yt" }, "To year"), h("input#yt", { inputmode: "numeric", placeholder: years.length ? String(Math.max(...years)) : "to", value: R.filters.year_to }),
      h("button.btn.btn-small", { type: "button", onclick: () => { R.filters.year_from = $("#yf").value.trim(); R.filters.year_to = $("#yt").value.trim(); runSearch(); } }, "Apply")));
  add(box, yf);
  if (!commander) add(box, group("status", "Corpus status (display only)"));
  add(box, h("p.sr-hint", "Counts are documents in the published library matching the query. Statuses are crawler summaries, not legal applicability."));
}

// ------------------------------------------------------------------ document tabs
function syncTabsWithResult() {
  const t = R.tabs[R.active];
  if (t) { t.hits = hitsFor(t.docId); renderToolbar(); }
}
function hitsFor(docId) {
  const r = R.result;
  if (!r || r.state !== "results") return [];
  return r.passages.filter((p) => p.doc_id === docId).sort((a, b) => a.page - b.page || (a.passage_id < b.passage_id ? -1 : 1));
}

export function openFromHit(p, newTab, preview) {
  openDocument({ docId: p.doc_id, page: p.page, passage: p.passage_id, copy: null }, { newTab, preview });
}

export async function openDocument({ docId, page, passage, copy, notice, citeState, currentCopy, copyPages, firstRelease }, { newTab = false, preview = false, push = true } = {}) {
  let t = R.tabs.findIndex((x) => x.docId === docId && (x.copy || null) === (copy || null));
  if (t < 0) {
    const tab = { docId, copy: copy || null, page: page || 1, passage: passage || null, view: "original", doc: null, viewer: null, hits: hitsFor(docId), hitIndex: -1, notice, citeState, currentCopy, preview, copyPages, firstRelease };
    if (!newTab && R.active >= 0 && (R.tabs[R.active].preview || R.tabs.length >= 12)) { disposeTab(R.tabs[R.active]); R.tabs[R.active] = tab; t = R.active; }
    else if (!newTab && R.active >= 0 && !preview) { disposeTab(R.tabs[R.active]); R.tabs[R.active] = tab; t = R.active; }
    else { if (R.tabs.length >= 12) { disposeTab(R.tabs.shift()); } R.tabs.push(tab); t = R.tabs.length - 1; }
  } else {
    const tab = R.tabs[t];
    tab.page = page || tab.page; tab.passage = passage || null; tab.notice = notice ?? tab.notice; tab.hits = hitsFor(docId);
  }
  R.active = t;
  R.el?.classList.add("doc-open");
  R.el?.classList.remove("results-open");
  const tab = R.tabs[t];
  tab.hitIndex = tab.hits.findIndex((x) => x.page === tab.page && (!tab.passage || x.passage_id === tab.passage));
  if (tab.hitIndex < 0) tab.hitIndex = tab.hits.findIndex((x) => x.page === tab.page);
  if (push) R.nav.replace(docUrl(tab));
  await renderDocPane();
}

function docUrl(tab) {
  const sp = searchParams();
  sp.set("p", tab.page); if (tab.passage) sp.set("a", tab.passage); if (tab.copy) sp.set("copy", tab.copy.slice(0, 12));
  return `/d/${encodeURIComponent(tab.docId)}?${sp.toString()}`;
}

function disposeTab(tab) { if (tab?.viewer) tab.viewer.destroy(); }
export function closeTab(i = R.active) {
  if (i < 0 || i >= R.tabs.length) return;
  disposeTab(R.tabs[i]); R.tabs.splice(i, 1);
  R.active = Math.min(R.active, R.tabs.length - 1);
  if (R.active < 0) { R.el?.classList.remove("doc-open"); R.nav.replace(researchUrl()); }
  renderDocPane();
}
export function cycleTab(d) { if (R.tabs.length < 2) return; R.active = (R.active + d + R.tabs.length) % R.tabs.length; R.nav.replace(docUrl(R.tabs[R.active])); renderDocPane(); }

async function renderDocPane() {
  const pane = $("#docpane"), ctx = $("#ctx");
  if (!pane) return;
  clear(pane);
  if (R.tabs.length) add(pane, h("div.tabs", { role: "tablist", "aria-label": "Open documents" }, R.tabs.map((t, i) =>
    h("div.tab", { role: "tab", "aria-selected": String(i === R.active), tabindex: i === R.active ? "0" : "-1", title: t.doc?.title || t.docId,
      onclick: (e) => { if (e.target.closest(".tab-close")) return; R.active = i; R.nav.replace(docUrl(t)); renderDocPane(); },
      onauxclick: (e) => { if (e.button === 1) closeTab(i); } },
      h("span.tab-title", `${t.preview ? "Preview · " : ""}${(t.doc?.title || t.docId).slice(0, 40)}`),
      h("button.tab-close", { type: "button", "aria-label": `Close ${t.doc?.title || t.docId} (X)`, onclick: () => closeTab(i) }, "×")))));
  const tab = R.tabs[R.active];
  if (!tab) {
    add(pane, h("div.docempty", h("h2", "No document open"), h("p", "Open a result to read the original at the cited page. ", h("kbd", "Enter"), " opens the selected result, ", h("kbd", "O"), " opens it in a new tab and ", h("kbd", "Space"), " previews it."),
      h("p", "Originals are delivered in bounded, authenticated byte ranges and are never stored in the browser.")));
    clear(ctx); add(ctx, h("div.ctx-body", h("p.muted", "Evidence, provenance and related candidates for the open document appear here.")));
    return;
  }
  if (!tab.doc) {
    add(pane, h("div.dochead", h("span.skeleton.w60"), h("span.skeleton.w40")));
    try { tab.doc = await api(`/api/documents/${encodeURIComponent(tab.docId)}`); }
    catch (e) {
      if (R.tabs[R.active] !== tab) return;
      clear(pane);
      add(pane, e instanceof ApiError && e.status === 404
        ? h("div.docempty", { role: "alert" }, h("h2", "Not available"), h("p", "This document is not available in this installation."))
        : h("div.error-state", { role: "alert" }, h("h2", "The document could not be loaded"), h("p", e.message), h("button.btn", { onclick: () => renderDocPane() }, "Try again")));
      return;
    }
    if (R.tabs[R.active] !== tab) return;
    return renderDocPane();
  }
  const d = tab.doc;
  add(pane, docHeader(d, tab), h("div.toolbar#toolbar", { role: "toolbar", "aria-label": "Document tools" }), h("div.viewer#viewer", { role: "region", "aria-label": tab.view === "original" ? "Original document" : "Extracted text" }));
  renderToolbar();
  renderCtx();
  await showView(tab);
}

function origin(d, field) {
  const o = d.field_origin?.[field];
  if (!o) return null;
  return h("span.chip.chip-origin", { title: `Field origin: ${o === "llm" ? "LLM-derived" : o}` }, o === "llm" ? "LLM-derived" : o);
}

function docHeader(d, tab) {
  if (tab.copy && tab.copy !== d.copy.sha256) {
    const head = h("header.dochead", h("h1", { lang: d.language === "hi" ? "hi" : null }, d.title || "Title not printed"),
      h("div.meta", h("span.field", h("span.label", "Cited copy"), h("span.mono", short(tab.copy))),
        h("span.field", h("span.label", "Pages"), h("span", String(tab.pageCount || tab.copyPages || "…"))),
        tab.firstRelease ? h("span.field", h("span.label", "First held in release"), h("span.mono", tab.firstRelease)) : null,
        h("span.field", candidateChip("Earlier edition: only copy-level facts are shown"))),
      h("p.muted", "Only copy-level facts are shown for an earlier edition. Dates, court and other metadata of the current record may not describe this copy."));
    if (tab.notice) add(head, h("div.notice", { role: "status" }, h("span", tab.notice),
      tab.currentCopy ? h("button.btn.btn-small", { type: "button", onclick: () => openDocument({ docId: d.doc_id, page: 1, copy: null }, { newTab: true }) }, "Open current edition") : null));
    return head;
  }
  const j = d.judicial;
  const f = (label, value, field, mono) => value ? h("span.field", h("span.label", label), mono ? h("span.mono", value) : h("span", value), origin(d, field)) : null;
  const head = h("header.dochead",
    h("h1", { lang: d.language === "hi" ? "hi" : null }, d.title || "Title not printed", origin(d, "title")),
    h("div.meta",
      f("Type", typeLabel(d.doc_type)), j ? f("Court", j.court, "court") : f("Issuer", d.issuing_authority, "issuing_authority"),
      j?.bench ? f("Bench", j.bench, "bench") : null, f("Date", fmtDate(d.issue_date), "issue_date"),
      d.effective_date ? f("Commencement (as recorded)", fmtDate(d.effective_date), "effective_date") : null,
      f("Number", d.number, "number", true), j?.neutral_citation ? f("Neutral citation", j.neutral_citation, "neutral_citation", true) : null,
      (j?.case_numbers || []).length ? f("Case numbers", j.case_numbers.join(", "), "case_numbers", true) : null,
      (j?.reported_citations || []).length ? f("Reported", j.reported_citations.join("; "), "reported_citations", true) : null,
      j?.judges?.length ? h("span.field", { title: j.judges_note || "" }, h("span.label", "Judges (crawler; may be incomplete)"), h("span", j.judges.join(", ")), origin(d, "judges")) : null,
      j && !(j.case_numbers || []).length && (j.cover_case_numbers || []).length
        ? h("span.field", { title: j.cover_case_numbers_note }, h("span.label", "Case numbers on p.1"), h("span.mono", j.cover_case_numbers.join(", ")), candidateChip(j.cover_case_numbers_note)) : null),
    h("div.meta",
      tab.copy && tab.copy !== d.copy.sha256
        ? h("span.field", h("span.label", "Cited copy"), h("span.mono", short(tab.copy)), h("span.muted", "(earlier edition held in this installation; the metadata above is the current edition's record)"))
        : h("span.field", h("span.label", "Copy"), h("span.mono", short(d.copy.sha256)), h("span.muted", `${d.copy.page_count} pages · ${(d.copy.bytes / 1048576).toFixed(1)} MB`)),
      h("span.field", h("span.label", "Source"), h("span", host(d.provenance.source_url))),
      h("span.field", h("span.label", "Retrieved"), h("span", fmtDate(d.provenance.retrieved_at) || "not recorded")),
      h("span.field", h("span.label", "Corpus status"), h("span", d.corpus_status), h("span.muted", "(display only)")),
      h("span.field", candidateChip("Extracted text and metadata are automated and not verified"))));
  if (tab.notice) add(head, h("div.notice", { role: "status" }, h("span", tab.notice),
    tab.currentCopy ? h("button.btn.btn-small", { type: "button", onclick: () => openDocument({ docId: d.doc_id, page: 1, copy: null }, { newTab: true }) }, "Open current edition") : null));
  if (d.access_marking) add(head, h("div.notice", `Printed access marking: ${d.access_marking}`));
  if (d.copy.completeness === "TRUNCATED_AT_SOURCE") add(head, h("div.notice", { role: "note" }, chip("warning", "Truncated at source"),
    " This copy is incomplete as received from its source. Missing pages are not evidence that anything was decided or not decided; read a complete copy where one is held."));
  if (d.outcomes?.length && !(tab.copy && tab.copy !== d.copy.sha256)) {
    const strip = h("div.proceedings", { "aria-label": "Proceedings and candidate outcomes" }, h("span.label.muted", "Candidate outcomes (A2 extractor V4):"));
    for (const o of d.outcomes.slice(0, 6)) {
      const ev = o.evaluation;
      const fig = ev ? `P ${(ev.precision * 100).toFixed(1)}% / cov ${(ev.coverage * 100).toFixed(1)}% (field level, weighted; ${ev.human_checked ? "human-checked" : "not human-checked"})` : "not evaluated";
      add(strip, h("div.prow", h("span.mono", o.payload.proceeding_ref || "Proceeding not identified"), h("span", "·"),
        h("strong", (o.payload.label || "abstained").replaceAll("_", " ")), candidateChip(), h("span.muted", fig),
        h("button.btn-quiet.btn-small", { type: "button", onclick: () => candidatePopover(o) }, "Details")));
    }
    if (d.outcomes.length > 6) add(strip, h("span.muted", `${d.outcomes.length - 6} more in Related`));
    add(head, strip);
  }
  return head;
}

function candidatePopover(c) {
  const ev = c.evaluation;
  openDialog("Candidate (automated, not verified)", h("div",
    h("p", "This value was produced by a program and has not been checked by a person. It is a research aid, not a finding. ", h("code", "AUTOMATED_CANDIDATE_NOT_VERIFIED")),
    h("dl.kv",
      h("dt", "Extractor"), h("dd.mono", `${c.extractor.name} ${c.extractor.version} @ ${c.extractor.commit}`),
      h("dt", "Capability restriction"), h("dd", c.capability_restriction.replaceAll("_", " ")),
      h("dt", "Deferred findings"), h("dd", c.deferred_findings?.join(", ") || "none recorded"),
      h("dt", "Measured quality"), h("dd", ev ? `precision ${ev.precision}, coverage ${ev.coverage}; ${ev.ci_note || ""}; human-checked: ${ev.human_checked ? "yes" : "no"}` : "not evaluated"),
      h("dt", "Report"), h("dd.mono", ev ? `${ev.report_path} @ ${ev.report_commit}` : "none"),
      h("dt", "Evidence"), h("dd", c.anchors.map((a) => h("div", `page ${a.page}${a.page_only ? " (page-level anchor)" : ""}`, a.extractor_quote ? h("div.muted", "Quoted by the extractor: ", h("q", a.extractor_quote)) : null))))));
}

function renderToolbar() {
  const tb = $("#toolbar"); const tab = R.tabs[R.active];
  if (!tb || !tab?.doc) return;
  clear(tb);
  const n = tab.copy ? (tab.pageCount || tab.doc.copy.page_count) : tab.doc.copy.page_count;
  const hits = tab.copy ? [] : (tab.hits || []);
  add(tb, 
    h("div.segmented", { role: "group", "aria-label": "View (T)" },
      h("button", { type: "button", "aria-pressed": String(tab.view === "original"), onclick: () => setView("original") }, "Original"),
      h("button", { type: "button", "aria-pressed": String(tab.view === "text"), onclick: () => setView("text"), disabled: tab.copy && tab.citeState === "CITED_COPY_ELIGIBLE_NOT_CURRENT" ? true : null }, "Text")),
    h("span.sep"),
    h("button.icon-btn", { type: "button", "aria-label": "Previous hit (Shift+N)", title: "Previous hit (Shift+N)", disabled: !hits.length || null, onclick: () => nextHit(-1) }, icon("prev")),
    h("span.hitcount", { "aria-live": "polite" }, hits.length ? `hit ${tab.hitIndex >= 0 ? tab.hitIndex + 1 : "–"} of ${hits.length}` : "no hits"),
    h("button.icon-btn", { type: "button", "aria-label": "Next hit (N)", title: "Next hit (N)", disabled: !hits.length || null, onclick: () => nextHit(1) }, icon("next")),
    h("span.sep"),
    h("label", { for: "pageinput", class: "muted" }, "Page "),
    h("input.pageinput#pageinput", { inputmode: "numeric", value: tab.page, "aria-label": `Page number, 1 to ${n} (P)`,
      onkeydown: (e) => { if (e.key === "Enter") { e.preventDefault(); goPage(parseInt(e.target.value, 10)); } } }),
    h("span.muted", `of ${n}`),
    h("button.icon-btn", { type: "button", "aria-label": "Previous page", disabled: tab.page <= 1 || null, onclick: () => goPage(tab.page - 1) }, icon("prev")),
    h("button.icon-btn", { type: "button", "aria-label": "Next page", disabled: tab.page >= n || null, onclick: () => goPage(tab.page + 1) }, icon("next")),
    tab.view === "original" ? [h("span.sep"),
      h("button.icon-btn", { type: "button", "aria-label": "Zoom out", onclick: () => zoom(-1) }, icon("minus")),
      h("button.icon-btn", { type: "button", "aria-label": "Zoom in", onclick: () => zoom(1) }, icon("plus")),
      h("button.btn.btn-small", { type: "button", onclick: () => zoom(0) }, "Fit width")] : null,
    h("span", { style: "flex:1" }),
    h("button.btn.btn-small", { type: "button", onclick: () => copyCitation(false), title: "Copy legal citation (C)" }, icon("cite"), "Copy citation"),
    h("button.btn.btn-small", { type: "button", onclick: () => copyCitation(true), title: "Copy internal reference and permalink (Shift+C)" }, icon("copy"), "Internal ref"),
    h("button.btn.btn-small.drawer-toggle", { type: "button", onclick: () => toggleCtx(), title: "Evidence and provenance (Shift+B)" }, icon("panel"), "Evidence"),
    h("button.btn.btn-small.drawer-toggle", { type: "button", onclick: () => R.el.classList.toggle("results-open"), title: "Results" }, icon("list"), "Results"));
}

export function setView(v) {
  const tab = R.tabs[R.active];
  if (!tab) return;
  if (v === "toggle") v = tab.view === "original" ? "text" : "original";
  if (v === "text" && tab.copy && tab.citeState === "CITED_COPY_ELIGIBLE_NOT_CURRENT") { toast("Text view is available for the current edition only. The cited copy is shown as its original."); return; }
  if (tab.viewer) tab.viewer.invalidate();
  tab.view = v; renderToolbar(); showView(tab);
  const vw = $("#viewer"); if (vw) vw.setAttribute("aria-label", v === "original" ? "Original document" : "Extracted text");
}

function terms() { return R.result?.highlight_terms || []; }

async function showView(tab) {
  const vw = $("#viewer");
  if (!vw) return;
  if (tab.view === "text") return showText(tab, vw);
  const pageOcr = tab.doc.pages.find((p) => p.page === tab.page)?.method === "ocr";
  if (!tab.viewer || tab.viewer.destroyed) {
    clear(vw);
    add(vw, h("div.pdf-legend", "Loading the original…"), h("div.pagewrap", { style: "width:min(800px,90%);aspect-ratio:1/1.414" }, h("div.placeholder", `Loading page ${tab.page}…`)));
    tab.viewer = new ProtectedViewer(vw, { docId: tab.docId, copy: tab.copy, onState: (s, info) => viewerState(tab, s, info) });
    window.__mimamsaViewer = tab.viewer;
    let ok = false;
    try { ok = await tab.viewer.open(); } catch (e) { viewerState(tab, "failed", e.message); return; }
    if (!ok || R.tabs[R.active] !== tab || tab.view !== "original") return;
    tab.pageCount = tab.viewer.numPages; renderToolbar();
  } else tab.viewer.host = vw;
  if (tab.view !== "original") return;
  await tab.viewer.render(tab.page, { terms: terms(), ocr: pageOcr });
}

function viewerState(tab, s, info) {
  if (R.tabs[R.active] !== tab) return;
  const vw = $("#viewer");
  if (s === "unavailable") {
    tab.viewer = null;
    clear(vw); add(vw, h("div.docempty", { role: "alert" }, h("h2", "Not available"), h("p", "This document is not available in this installation."),
      h("p.muted", "Anything already displayed has been cleared.")));
  } else if (s === "failed") {
    tab.viewer = null;
    clear(vw); add(vw, h("div.error-state", { role: "alert", style: "margin:24px" }, h("h2", "The original could not be displayed in the browser"),
      h("p", "No derived or substitute file is shown in its place. You can read the extracted text (labelled as such) or check the provenance, and retry the same copy and page."),
      h("p.mono", `Reference: VIEW-${Date.now().toString(36)} · copy ${short(tab.doc.copy.sha256)} · p.${tab.page}`),
      h("div", { style: "display:flex;gap:8px" }, h("button.btn", { onclick: () => setView("text") }, "Show the Text view"),
        h("button.btn", { onclick: () => { R.ctxTab = "provenance"; renderCtx(); if (window.matchMedia("(max-width:1599px)").matches) R.el.classList.add("ctx-open"); } }, "Show provenance"),
        h("button.btn.btn-primary", { onclick: () => { window.__mimamsaTestFail = null; showView(tab); } }, "Retry the original"))));
  } else if (s === "rendered") {
    announce(`Page ${info} of ${tab.doc.copy.page_count}`);
  }
}

async function showText(tab, vw) {
  clear(vw);
  const box = h("article.textview", { "aria-label": "Extracted text with page markers" });
  add(vw, box);
  const from = Math.max(1, tab.page - 2), to = Math.min(tab.doc.copy.page_count, tab.page + 12);
  add(box, h("p.muted", { style: "font-family:var(--font-ui);font-size:13px" }, "Extracted text (automated, not verified). Page markers are physical pages of the original. ",
    tab.doc.quoting_permitted ? "" : "This text includes OCR: for search only; quote from the original page."));
  let data;
  try { data = await api(`/api/documents/${encodeURIComponent(tab.docId)}/text?from=${from}&to=${to}`); }
  catch (e) { add(box, h("div.error-state", { role: "alert" }, h("p", e.status === 404 ? "This document is not available in this installation." : "The text could not be loaded."))); return; }
  if (R.tabs[R.active] !== tab || tab.view !== "text") return;
  if (from > 1) add(box, h("button.btn.btn-small", { type: "button", onclick: () => { tab.page = Math.max(1, from - 10); showText(tab, vw); } }, `Earlier pages (before ${from})`));
  const t = terms();
  const rx = t.length ? new RegExp(`(?<![\\p{L}\\p{N}\\p{M}])(?:${t.map((w) => w.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).sort((a, b) => b.length - a.length).join("|")})(?![\\p{L}\\p{N}\\p{M}])`, "giu") : null;
  let target = null;
  for (const pg of data.pages) {
    add(box, h("div.pg-divider", { id: `tp-${pg.page}` }, `Page ${pg.page}`, pg.ocr ? h("span.chip.chip-warning.ocr-note", "OCR text: for search only. Quote from the original page.") : null,
      pg.low_confidence ? h("span.chip.chip-warning.ocr-note", "Low OCR confidence") : null));
    let cursor = 0;
    const parts = pg.passages.length ? pg.passages : [{ id: null, start: 0, end: pg.text.length }];
    for (const ps of parts) {
      if (ps.start > cursor) add(box, h("div.psg", pg.text.slice(cursor, ps.start)));
      const txt = pg.text.slice(ps.start, ps.end);
      const el = h("div.psg", { id: ps.id ? `psg-${ps.id}` : null, "data-page": pg.page }, rx ? highlightText(txt, rx) : txt);
      if (ps.id && ps.id === tab.passage) { el.classList.add("target"); target = el; }
      add(box, el); cursor = ps.end;
    }
    if (cursor < pg.text.length) add(box, h("div.psg", pg.text.slice(cursor)));
    if (!pg.text.trim()) add(box, h("p.muted", "No text on this page in the derivative."));
  }
  if (to < tab.doc.copy.page_count) add(box, h("button.btn.btn-small", { type: "button", onclick: () => { tab.page = to + 1; showText(tab, vw); } }, `Later pages (after ${to})`));
  (target || $(`#tp-${tab.page}`, box))?.scrollIntoView({ block: "start" });
}

function highlightText(txt, rx) {
  const frag = document.createDocumentFragment();
  let pos = 0;
  for (const m of txt.matchAll(rx)) { frag.append(txt.slice(pos, m.index), h("mark", m[0])); pos = m.index + m[0].length; }
  frag.append(txt.slice(pos));
  return frag;
}

export function goPage(n) {
  const tab = R.tabs[R.active];
  if (!tab || !Number.isFinite(n)) return;
  n = Math.max(1, Math.min(tab.copy ? (tab.pageCount || tab.doc.copy.page_count) : tab.doc.copy.page_count, n));
  tab.page = n; tab.passage = null;
  tab.hitIndex = (tab.hits || []).findIndex((x) => x.page === n);
  R.nav.replace(docUrl(tab));
  renderToolbar(); showView(tab);
}
export function focusPageInput() { const p = $("#pageinput"); if (p) { p.focus(); p.select(); } }
export function nextHit(d) {
  const tab = R.tabs[R.active];
  if (!tab || !tab.hits?.length) { toast("No search hits in this document"); return; }
  tab.hitIndex = (tab.hitIndex + d + tab.hits.length) % tab.hits.length;
  const hit = tab.hits[tab.hitIndex];
  tab.page = hit.page; tab.passage = hit.passage_id;
  R.nav.replace(docUrl(tab));
  renderToolbar(); showView(tab);
}
function zoom(dir) {
  const tab = R.tabs[R.active];
  if (!tab?.viewer) return;
  const cur = tab.viewer.scale || 1.2;
  tab.viewer.setScale(dir === 0 ? null : Math.max(0.5, Math.min(3, cur + dir * 0.2)));
}

export async function copyCitation(internal) {
  const tab = R.tabs[R.active];
  if (!tab?.doc) return;
  if (tab.copy && tab.citeState === "CITED_COPY_ELIGIBLE_NOT_CURRENT") {
    const ref = `[${tab.docId} · copy ${short(tab.copy)} · p.${tab.page} · cited copy, not the current edition]`;
    if (await copyText(ref)) toast("Internal reference to the cited copy copied"); return;
  }
  const hit = (tab.hits || [])[tab.hitIndex];
  const para = hit && hit.page === tab.page ? hit.paragraph_label : null;
  try {
    const c = await api(`/api/documents/${encodeURIComponent(tab.docId)}/citation?page=${tab.page}${para ? `&para=${encodeURIComponent(para)}` : ""}`);
    const text = internal ? c.internal_reference : c.legal;
    const ok = await copyText(text);
    toast(ok ? `${internal ? "Internal reference" : "Legal citation"} copied${c.ocr_note && !internal ? ". " + c.ocr_note : ""}` : "Copy was blocked by the browser");
    window.__mimamsaLastCopy = text;
  } catch (e) { toast(e.message); }
}

// ------------------------------------------------------------------ context pane
export function openCtxTab(name) {
  R.ctxTab = name; renderCtx();
  if (window.matchMedia("(max-width: 1599px)").matches) R.el.classList.add("ctx-open"); else R.el.classList.remove("no-ctx");
  $(`#ctx-tab-${name}`)?.focus();
}

function renderCtx() {
  const ctx = $("#ctx"); const tab = R.tabs[R.active];
  if (!ctx || !tab?.doc) return;
  clear(ctx);
  const tabs = [["evidence", "Evidence"], ["provenance", "Provenance"], ["related", "Related"], ["cited", "Cited/Citing"], ["notes", "Notes"]];
  add(ctx, h("div.ctx-tabs", { role: "tablist", "aria-label": "Context" }, tabs.map(([k, l]) =>
    h("button", { role: "tab", id: `ctx-tab-${k}`, "aria-selected": String(R.ctxTab === k), "aria-controls": "ctx-body", tabindex: R.ctxTab === k ? "0" : "-1",
      onclick: () => { R.ctxTab = k; renderCtx(); },
      onkeydown: (e) => { if (e.key === "ArrowRight" || e.key === "ArrowLeft") { const i = tabs.findIndex((t) => t[0] === R.ctxTab); R.ctxTab = tabs[(i + (e.key === "ArrowRight" ? 1 : -1) + tabs.length) % tabs.length][0]; renderCtx(); $(`#ctx-tab-${R.ctxTab}`).focus(); } } }, l))));
  const body = h("div.ctx-body#ctx-body", { role: "tabpanel", "aria-labelledby": `ctx-tab-${R.ctxTab}`, tabindex: "0" });
  add(ctx, body);
  const d = tab.doc;
  if (R.ctxTab === "evidence") {
    add(body, h("p.muted", "Seven separate status axes, in fixed order. No single “verified” state exists."));
    for (const a of d.status_axes) {
      const pv = a.policy_v1;
      add(body, h("details.axis", { "data-axis": a.axis }, h("summary", h("span.axis-name", a.label), axisChip(a.axis, a.value)),
        h("div.basis", h("div", a.basis || "No basis recorded."), a.evidence_ref ? h("div.mono", `Evidence: ${a.evidence_ref}`) : null,
          a.recorded_at ? h("div.muted", `Recorded ${fmtDate(a.recorded_at)}`) : null,
          a.axis === "legal_approval" ? h("div", "Closed: needs a Legal Reviewer appointment and recorded approvals. No legal reasoning is available in this version.") : null,
          pv ? h("dl.kv", { style: "margin-top:6px" }, Object.entries(pv).map(([k, v]) => [h("dt", k.replaceAll("_", " ")), h("dd", v === null ? "not recorded" : String(v).replaceAll("_", " "))])) : null)));
    }
    add(body, h("div.sect", { style: "margin-top:16px" }, h("h3", "Checked by this installation"),
      h("dl.kv", h("dt", "Importer"), h("dd", "Copy SHA-256, size, content type and page count verified from the bundled bytes before activation"),
        h("dt", "At service start"), h("dd", d.copy.rehashed_at_load ? "Original re-hashed from the vault: matches" : "Original did not re-hash: not served"),
        h("dt", "Derived text"), h("dd", "Page and passage hashes verified; text is automated (not checked against the page image)"))));
  } else if (R.ctxTab === "provenance") {
    const p = d.provenance;
    add(body, h("dl.kv",
      h("dt", "Source URL"), h("dd", h("span.mono", p.source_url || "not recorded"), " ", p.source_url ? h("button.btn-quiet.btn-small", { type: "button", onclick: async () => toast(await copyText(p.source_url) ? "Source URL copied" : "Copy blocked") }, "Copy") : null),
      h("dt", "Retrieved"), h("dd", p.retrieved_at || "not recorded"),
      h("dt", "Channel"), h("dd", p.acquisition_channel || ""), h("dt", "Source system"), h("dd", p.source_system || "not recorded"),
      h("dt", "Record id"), h("dd.mono", p.source_record_id || "not recorded"), h("dt", "Original file name"), h("dd.mono", p.original_filename || "not recorded"),
      h("dt", "SHA-256"), h("dd", h("div.copybox", h("code", d.copy.sha256), h("button.btn-quiet.btn-small", { type: "button", onclick: async () => toast(await copyText(d.copy.sha256) ? "SHA-256 copied" : "Copy blocked") }, "Copy"))),
      h("dt", "Bytes / pages"), h("dd", `${d.copy.bytes.toLocaleString("en-GB")} bytes · ${d.copy.page_count} physical pages`),
      h("dt", "Vault key"), h("dd.mono", d.copy.vault_key),
      h("dt", "HF repository"), h("dd.mono", p.hf ? `${p.hf.repo} @ ${p.hf.revision?.slice(0, 12)}` : "not recorded"), h("dt", "HF path"), h("dd.mono", p.hf?.path || ""),
      h("dt", "Release"), h("dd.mono", p.release_id), h("dt", "Generation"), h("dd.mono", p.generation),
      h("dt", "Text pipeline"), h("dd.mono", `${p.pipeline.name} ${p.pipeline.version} · text ${short(p.pipeline.text_sha256)}`),
      h("dt", "Text method"), h("dd", `${d.text_method}${d.ocr_confidence != null ? ` · OCR mean confidence ${d.ocr_confidence}` : ""}`),
      h("dt", "Aliases"), h("dd", (p.aliases || []).length ? p.aliases.map((a) => h("div.mono", a.source_url)) : "none"),
      h("dt", "Access marking"), h("dd", p.access_marking || "none printed (as recorded)"),
      h("dt", "Corpus status note"), h("dd", d.corpus_status_note || "none"),
      h("dt", "Publication"), h("dd", p.publication_history.map((x) => h("div", `${x.channel} · ${x.release_id}${x.actor ? " · " + x.actor : ""}`)))));
  } else if (R.ctxTab === "related") {
    add(body, h("div.absence", d.absence_notice));
    if (d.outcomes.length) {
      const s = h("div.sect", h("h3", `Candidate outcomes (${d.outcomes.length})`));
      for (const o of d.outcomes) add(s, candCard(o, `${(o.payload.label || "abstained").replaceAll("_", " ")} · ${o.payload.proceeding_ref || "proceeding not identified"}`));
      add(body, s);
    }
    if (d.provision_versions.length) {
      const s = h("div.sect", h("h3", `Temporal version candidates (A4, ${d.provision_versions.length})`),
        h("p.muted", "Temporal chain not established. Dates are shown only as the record states them; a publication date is never treated as commencement."));
      for (const v of d.provision_versions.slice(0, 80)) add(s, h("div.cand", h("div.cand-head", candidateChip(v.label), h("strong", `${v.provision}`), h("span.mono.muted", v.version_id)),
        h("div.cand-body", h("div", v.change_summary || ""), h("div", `Effective from: ${v.effective_from.status?.replaceAll("_", " ") || "not recorded"}${v.effective_from.reported_date ? ` (reported ${v.effective_from.reported_date})` : ""} · currency: ${v.currency || "not recorded"}`),
          v.evidence.filter((e) => e.page).map((e) => h("div", h("a", { href: "#", onclick: (ev) => { ev.preventDefault(); openDocument({ docId: e.doc_id, page: e.page }); } }, `Evidence: ${e.role.replaceAll("_", " ")} p.${e.page}`))))));
      add(body, s);
    }
    if (!d.outcomes.length && !d.provision_versions.length) add(body, h("p.muted", "No related candidate records for this document."));
  } else if (R.ctxTab === "cited") {
    add(body, h("div.absence", "Extracted citations: candidates. Absence of a citation is not absence of authority. A citation does not establish how one court treated another."));
    const out = h("div.sect", h("h3", `Cites (${d.edges_out_total} extracted)`));
    if (!d.edges_out.length) add(out, h("p.muted", "No extracted links. This does not mean there is no related or adverse authority."));
    for (const e of d.edges_out.slice(0, 150)) add(out, edgeCard(e, d));
    if (d.edges_out_total > d.edges_out.length) add(out, h("p.muted", `${d.edges_out_total - d.edges_out.length} more not listed in B1.`));
    const inc = h("div.sect", h("h3", `Cited by, within this library (${d.edges_in.length})`));
    if (!d.edges_in.length) add(inc, h("p.muted", "No extracted links. This does not mean there is no related or adverse authority."));
    for (const x of d.edges_in) add(inc, h("div.cand", h("div.cand-head", candidateChip(), h("span", x.candidate.payload.relation.replaceAll("_", " ").toLowerCase())),
      h("div.cand-body", h("a", { href: "#", onclick: (ev) => { ev.preventDefault(); openDocument({ docId: x.from_doc, page: x.candidate.anchors[0]?.page || 1 }, { newTab: true }); } }, x.from_title || x.from_doc),
        x.candidate.anchors[0] ? ` · p.${x.candidate.anchors[0].page}` : "")));
    add(body, out, inc);
  } else {
    add(body, h("p", "Private notes and pins are not part of the B1 prototype."), h("p.muted", "When they arrive they are stored on the server for your account only, never in the browser, and never shared or searched by others."));
  }
}

function candCard(c, title) {
  const ev = c.evaluation;
  return h("div.cand", h("div.cand-head", candidateChip(), h("strong", title)),
    h("div.cand-body", h("div", ev ? `Measured (field level, weighted): precision ${(ev.precision * 100).toFixed(1)}%, coverage ${(ev.coverage * 100).toFixed(1)}%; ${ev.human_checked ? "human-checked" : "not human-checked"}` : "Not evaluated"),
      h("div", `Restriction: ${c.capability_restriction.replaceAll("_", " ")}`),
      c.anchors.map((a) => h("div", h("a", { href: "#", onclick: (e) => { e.preventDefault(); goPage(a.page); } }, `Open evidence page ${a.page}`), a.page_only ? h("span.muted", " (page-level anchor)") : null,
        a.extractor_quote ? h("div.muted", "Quoted by the extractor: ", h("q", a.extractor_quote.slice(0, 280))) : null)),
      h("button.btn-quiet.btn-small", { type: "button", onclick: () => candidatePopover(c) }, "Details")));
}

function edgeCard(e, d) {
  const p = e.payload;
  const rel = p.relation.replaceAll("_", " ").toLowerCase();
  const proposed = !["CITES_JUDGMENT", "CITES_PROVISION", "QUOTES_PROVISION"].includes(p.relation);
  return h("div.cand", h("div.cand-head", candidateChip(), h("span", rel), proposed ? h("span.chip.chip-warning", "Proposed, not verified") : null),
    h("div.cand-body", e.target_in_library ? h("a", { href: "#", onclick: (ev) => { ev.preventDefault(); openDocument({ docId: e.target_in_library.doc_id, page: 1 }, { newTab: true }); } }, e.target_in_library.title)
      : h("span.mono", p.target?.raw_reference || "Unresolved reference"),
      e.anchors[0] ? h("div", h("a", { href: "#", onclick: (ev) => { ev.preventDefault(); goPage(e.anchors[0].page); } }, `Evidence on p.${e.anchors[0].page}`)) : null));
}

export function currentDoc() { return R.tabs[R.active]; }
export function hasResults() { return !!R.result; }
void apiState;
