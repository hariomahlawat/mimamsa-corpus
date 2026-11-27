// C15 WP5 Commander workspace (/c, /c/<domain>) and WP6 Document Studio (/studio, /studio/<id>).
// Commander pages show provisions held in this library under a task heading, with headings and excerpts as printed; they
// are candidate research aids, not legal advice, and use the same corpus, search and eligibility as everything else.
// Studio documents are private to their author. Every block shows its origin (you / template / automated suggestion /
// from the library); library citations are rendered by the server from the current eligible copy, so a withdrawn source
// shows "Source no longer available in this installation." while the author's own text is kept.
// All text is inserted with text nodes (h()), never as HTML.
import { api } from "./api.js";
import { h, append, clear, $, chip, candidateChip, toast, openDialog, fmtDate } from "./ui.js";

const add = (el, ...k) => append(el, k);
const go = (nav, url) => (e) => { e.preventDefault(); nav.go(url); };
const ORIGIN = { user: "You", template: "Template heading", suggestion: "Automated suggestion", corpus: "From the library" };
const STATE = { draft: "Draft", in_review: "In review (your label)", final_draft: "Final draft (your label; not legal approval)" };

// ------------------------------------------------------------------ policy refresh (withdrawal / reinstatement)
let current = null;   // { kind: "commander"|"studio", render: () => void }
export function refreshWorkspace() { if (current && document.querySelector("[data-workspace]")) current.render(); }
export const workspaceShown = () => !!document.querySelector("[data-workspace]");

// ------------------------------------------------------------------ Commander
export async function commanderPage(main, nav, id) {
  current = { kind: "commander", render: () => commanderPage(main, nav, id) };
  clear(main);
  const page = h("div.page.workspace", { "data-workspace": "commander" }, h("span.skeleton.w60"));
  add(main, page);
  let list, d = null;
  try { list = await api("/api/commander/domains"); if (id) d = await api(`/api/commander/domains/${encodeURIComponent(id)}`); }
  catch (e) { clear(page); add(page, h("div.error-state", { role: "alert" }, h("h2", e.status === 404 ? "No such task area" : "Could not load the Commander workspace"), h("p", e.message))); return; }
  clear(page);
  const nav2 = h("nav.ws-nav", { "aria-label": "Commander task areas" },
    h("a", { href: "/c", "aria-current": !id ? "page" : null, onclick: go(nav, "/c") }, "All task areas"),
    list.domains.map((x) => h("a", { href: `/c/${x.id}`, "aria-current": x.id === id ? "page" : null, onclick: go(nav, `/c/${x.id}`) }, x.title)));
  const label = h("p.ws-label", chip("candidate", list.label));
  if (!d) {
    add(page, h("header.ws-head", h("h1", "Commander workspace"), label, h("p.muted", list.disclaimer)), nav2,
      h("div.home-grid", list.domains.map((x) => h("a.home-card.ws-card", { href: `/c/${x.id}`, "data-domain": x.id, onclick: go(nav, `/c/${x.id}`) },
        h("h3", x.title), h("p.muted", x.purpose)))));
    return;
  }
  const prov = (it) => it.found
    ? h("li.ws-prov", { "data-provision": `${it.kind} ${it.number}` },
        h("div.ws-prov-head", h("a", { href: it.link, onclick: go(nav, it.link) }, h("span.num", `${it.kind} ${it.number}`), " ", h("span", it.heading || "")),
          it.omitted_as_printed ? chip("warning", "Printed as omitted") : null,
          h("button.btn.btn-small.btn-quiet", { type: "button", title: "Add a copy-pinned citation of this provision to a Studio document",
            onclick: () => openAddToStudio({ doc_id: it.doc_id, copy: it.copy, page: it.page, passage_id: null, label: `${it.kind} ${it.number}, ${it.instrument}` }) }, "Add to Studio")),
        h("div.muted.ws-src", `${it.instrument} · p.${it.page} · printed text from the held copy`),
        it.excerpt ? h("blockquote.ws-excerpt", it.excerpt) : null)
    : h("li.ws-prov.unavailable", { "data-provision": `${it.kind} ${it.number}` }, h("span.num", `${it.kind} ${it.number}`), h("span.muted", " not available in this library"));
  add(page,
    h("header.ws-head", h("h1", d.title), label, h("p", d.purpose), h("p.muted", d.disclaimer)), nav2,
    h("section.ws-sect", { "data-sect": "provisions" }, h("h2", "Provisions in the held text"),
      h("p.muted", "Grouped for this task. The order is the order of the held instrument, not a prescribed sequence."),
      d.groups.map((g) => h("div.ws-group", h("h3", g.label), h("p.muted", g.note), h("ul.ws-list", g.items.map(prov))))),
    d.safeguards.length ? h("section.ws-sect", { "data-sect": "safeguards" }, h("h2", "Safeguards in the held text"),
      h("p.muted", "Provisions that protect the person concerned. Whether and how they apply needs legal review."), h("ul.ws-list", d.safeguards.map(prov))) : null,
    h("section.ws-sect", { "data-sect": "forms" }, h("h2", "Forms and procedural references ", candidateChip("Search results, not a form registry")),
      h("p.muted", d.forms_note),
      d.forms.length ? d.forms.map((f) => h("div.ws-group", h("h3.mono", f.query),
        f.results.length ? h("ul.ws-list", f.results.map((r) => h("li", h("a", { href: r.link, onclick: go(nav, r.link) }, `${r.title} · p.${r.page}`), h("div.muted.ws-snip", r.snippet))))
          : h("p.muted", "No match in the held Acts, Rules or Regulations.")))
        : h("p.muted", "No form search is defined for this task area.")),
    h("section.ws-sect", { "data-sect": "questions" }, h("h2", "Questions requiring legal review"), h("p.muted", d.review_note),
      h("ol.ws-questions", d.review_questions.map((q) => h("li", q))),
      h("button.btn", { type: "button", onclick: () => openAddToStudio({ questions: d.review_questions, label: `Questions: ${d.title}` }) }, "Add these questions to a Studio document")));
}

// ------------------------------------------------------------------ add to Studio (reader, Commander)
/** spec: { doc_id, copy, page, passage_id, para, label } for a citation (and quote when passage_id), or { questions, label }. */
export async function openAddToStudio(spec) {
  let docs;
  try { docs = (await api("/api/studio/documents")).documents; } catch (e) { toast(e.message); return; }
  const sel = h("select#studio-target", { "aria-label": "Studio document" },
    h("option", { value: "" }, "New document…"), docs.map((x) => h("option", { value: x.id }, `${x.title} (v${x.version})`)));
  const title = h("input#studio-new-title", { type: "text", maxlength: "200", value: spec.label ? spec.label.slice(0, 200) : "Research note", "aria-label": "Title of the new document" });
  const quote = spec.passage_id ? h("label", h("input#studio-quote", { type: "checkbox", checked: true }), " Also quote the passage (text taken from the held copy)") : null;
  const blocks = () => spec.questions
    ? spec.questions.map((q) => ({ type: "question", origin: "suggestion", text: q }))
    : [{ type: (spec.passage_id && $("#studio-quote")?.checked) ? "quote" : "citation", doc_id: spec.doc_id, copy: spec.copy, page: spec.page, passage_id: spec.passage_id || undefined, para: spec.para || undefined }];
  const d = openDialog("Add to Studio", h("div",
    h("p", spec.questions ? `${spec.questions.length} questions, added as automated suggestions.` : `Copy-pinned citation: ${spec.label || spec.doc_id + " p." + spec.page}`),
    h("div.form-row", h("label", { for: "studio-target" }, "Document"), sel),
    h("div.form-row", h("label", { for: "studio-new-title" }, "Title (new document)"), title), quote,
    h("p.muted", "Studio documents are private to you and are never added to the library, search or graph.")),
    [h("button.btn", { onclick: () => d.close() }, "Cancel"), h("button.btn.btn-primary", { onclick: async () => {
      try {
        let id = sel.value;
        if (!id) id = (await api("/api/studio/documents", { method: "POST", body: { title: title.value, template: "research-note" } })).id;
        await api(`/api/studio/documents/${encodeURIComponent(id)}/append`, { method: "POST", body: { blocks: blocks() } });
        d.close(); toast("Added to Studio");
      } catch (e) { toast(e.body?.error || e.message); }
    } }, "Add")]);
}

// ------------------------------------------------------------------ Studio
export async function studioPage(main, nav, id) {
  current = { kind: "studio", render: () => studioPage(main, nav, id) };
  clear(main);
  const page = h("div.page.workspace", { "data-workspace": "studio" }, h("span.skeleton.w60"));
  add(main, page);
  return id ? studioEditor(page, nav, id) : studioHome(page, nav);
}

async function studioHome(page, nav) {
  let docs, tpls, notes;
  try { [docs, tpls, notes] = await Promise.all([api("/api/studio/documents"), api("/api/studio/templates"), api("/api/studio/notes")]); }
  catch (e) { clear(page); add(page, h("div.error-state", { role: "alert" }, h("h2", "Could not load the Studio"), h("p", e.message))); return; }
  clear(page);
  const title = h("input#new-doc-title", { type: "text", maxlength: "200", placeholder: "Title", "aria-label": "Title of the new document", required: true });
  const tpl = h("select#new-doc-template", { "aria-label": "Template" }, tpls.templates.map((t) => h("option", { value: t.id }, t.label)));
  const noteText = h("textarea#note-text", { rows: "2", maxlength: "4000", "aria-label": "New research note" });
  add(page,
    h("header.ws-head", h("h1", "Document Studio"), h("p.ws-label", chip("gated", "Working documents · not legally approved")),
      h("p.muted", "Private working documents and research notes. They are never added to the library, search or graph, and no one else can open them. " +
        "Review states are your own workflow labels, not legal approval. " + tpls.note)),
    h("section.ws-sect", { "data-sect": "new" }, h("h2", "New document"),
      h("form.ws-inline", { onsubmit: async (e) => { e.preventDefault();
        try { const d = await api("/api/studio/documents", { method: "POST", body: { title: title.value, template: tpl.value } }); nav.go(`/studio/${d.id}`); }
        catch (err) { toast(err.body?.error || err.message); } } }, title, tpl, h("button.btn.btn-primary", { type: "submit" }, "Create"))),
    h("section.ws-sect", { "data-sect": "documents" }, h("h2", `Your documents (${docs.documents.length})`),
      docs.documents.length ? h("table.data#studio-docs", h("thead", h("tr", ["Title", "State", "Version", "Updated", "Size"].map((x) => h("th", { scope: "col" }, x)))),
        h("tbody", docs.documents.map((x) => h("tr", { "data-doc": x.id }, h("td", h("a", { href: `/studio/${x.id}`, onclick: go(nav, `/studio/${x.id}`) }, x.title)),
          h("td", STATE[x.state] || x.state), h("td", `v${x.version}`), h("td", fmtDate(x.updated_at)), h("td", `${(x.bytes / 1000).toFixed(1)} kB`)))))
        : h("p.muted", "No documents yet.")),
    h("section.ws-sect", { "data-sect": "notes" }, h("h2", "Research notes"),
      h("form.ws-inline", { onsubmit: async (e) => { e.preventDefault();
        try { await api("/api/studio/notes", { method: "POST", body: { text: noteText.value } }); studioPage(page.parentElement, nav, null); }
        catch (err) { toast(err.body?.error || err.message); } } }, noteText, h("button.btn", { type: "submit" }, "Add note")),
      notes.notes.length ? h("ul.ws-list#studio-notes", notes.notes.map((n) => h("li", { "data-note": n.id }, h("div", n.text),
        n.has_reference ? (n.reference.available ? h("div.muted", h("a", { href: n.reference.link, onclick: go(nav, n.reference.link) }, n.reference.citation))
          : h("div.ws-na", n.reference.notice)) : null,
        h("div.muted", fmtDate(n.created_at), " ", h("button.btn-quiet.btn-small", { type: "button", onclick: async () => {
          try { await api(`/api/studio/notes/${encodeURIComponent(n.id)}/delete`, { method: "POST" }); studioPage(page.parentElement, nav, null); } catch (err) { toast(err.message); } } }, "Delete")))))
        : h("p.muted", "No notes yet.")));
}

function blockView(b, i, ed) {
  const origin = h("span.ws-origin", { "data-origin": b.origin }, ORIGIN[b.origin] || b.origin);
  const tools = h("span.ws-tools",
    h("button.btn-quiet.btn-small", { type: "button", "aria-label": "Move up", disabled: i === 0 || null, onclick: () => ed.move(i, -1) }, "↑"),
    h("button.btn-quiet.btn-small", { type: "button", "aria-label": "Move down", disabled: i === ed.blocks.length - 1 || null, onclick: () => ed.move(i, 1) }, "↓"),
    h("button.btn-quiet.btn-small", { type: "button", "aria-label": "Remove block", onclick: () => ed.remove(i) }, "Remove"));
  if (b.type === "citation" || b.type === "quote") {
    const body = b.available
      ? [b.type === "quote" ? (b.quote_available ? h("blockquote.ws-excerpt", b.quote) : h("p.ws-na", b.quote_notice)) : null,
         h("p.ws-cite", b.citation), h("p.muted.mono", b.internal_reference, " ", h("a", { href: b.permalink }, "Open cited page")),
         b.edition_note ? h("p.muted", b.edition_note) : null]
      : [h("p.ws-na", { "data-unavailable": "" }, b.notice)];
    return h("div.ws-block.corpus", { "data-type": b.type }, h("div.ws-block-head", origin, tools), body);
  }
  const field = b.type === "heading"
    ? h("input.ws-heading", { type: "text", value: b.text, "aria-label": "Heading", maxlength: "20000" })
    : h("textarea.ws-text", { rows: b.type === "question" ? "2" : "4", "aria-label": b.type === "question" ? "Question" : "Text", maxlength: "20000" }, b.text);
  field.addEventListener("input", () => { b.text = field.value; if (b.origin !== "user") { b.origin = "user"; origin.textContent = ORIGIN.user; origin.dataset.origin = "user"; } ed.dirty(); });
  return h("div.ws-block", { "data-type": b.type }, h("div.ws-block-head", origin, b.type === "question" ? chip("neutral", "Question for legal review") : null, tools), field);
}

async function studioEditor(page, nav, id, version) {
  let d, vers;
  try { [d, vers] = await Promise.all([api(`/api/studio/documents/${encodeURIComponent(id)}${version ? `?version=${version}` : ""}`), api(`/api/studio/documents/${encodeURIComponent(id)}/versions`)]); }
  catch (e) { clear(page); add(page, h("div.error-state", { role: "alert" }, h("h2", e.status === 404 ? "No such document in your Studio" : "Could not load the document"), h("p", e.body?.notice || e.message),
    h("p", h("a", { href: "/studio", onclick: go(nav, "/studio") }, "Back to the Studio")))); return; }
  clear(page);
  const latest = vers.versions[0].version, viewingOld = d.version !== latest;
  const ed = { blocks: d.blocks.map((b) => ({ ...b })), changed: false };
  const status = h("span.muted#studio-status", viewingOld ? `Viewing version ${d.version} of ${latest} (read-only)` : `Version ${d.version} · saved`);
  ed.dirty = () => { ed.changed = true; status.textContent = `Version ${d.version} · unsaved changes`; };
  const list = h("div.ws-blocks#studio-blocks");
  const draw = () => { clear(list); ed.blocks.forEach((b, i) => add(list, blockView(b, i, ed))); if (viewingOld) list.querySelectorAll("input, textarea, button").forEach((x) => { x.disabled = true; }); };
  ed.move = (i, dlt) => { const j = i + dlt; [ed.blocks[i], ed.blocks[j]] = [ed.blocks[j], ed.blocks[i]]; ed.dirty(); draw(); };
  ed.remove = (i) => { ed.blocks.splice(i, 1); ed.dirty(); draw(); };
  const addBlock = (type) => { ed.blocks.push({ type, origin: "user", text: "" }); ed.dirty(); draw(); list.lastElementChild?.querySelector("input, textarea")?.focus(); };
  const titleIn = h("input#studio-title", { type: "text", value: d.title, maxlength: "200", "aria-label": "Document title", oninput: () => ed.dirty() });
  const stateSel = h("select#studio-state", { "aria-label": "Workflow state (your label, not legal approval)", onchange: () => ed.dirty() },
    Object.entries(STATE).map(([k, v]) => h("option", { value: k, selected: d.state === k }, v)));
  const toWire = (b) => b.type === "citation" || b.type === "quote"
    ? { type: b.type, doc_id: b.doc_id, copy: b.copy, page: b.page, passage_id: b.passage_id, para: b.para }
    : { type: b.type, origin: b.origin, text: b.text };
  const save = async (blocks, state, title, base) => {
    try {
      const r = await api(`/api/studio/documents/${encodeURIComponent(id)}/save`, { method: "POST", body: { base_version: base, title, state, blocks: blocks.map(toWire) } });
      toast(`Saved as version ${r.version}`); nav.go(`/studio/${id}`);
    } catch (e) { toast(e.body?.notice || e.body?.error || e.message); }
  };
  add(page,
    h("header.ws-head", h("p", h("a", { href: "/studio", onclick: go(nav, "/studio") }, "← Studio")), titleIn,
      h("p.ws-label", chip("gated", "Working document · not legally approved"), " ", status), h("p.muted", d.notice)),
    h("div.ws-toolbar",
      h("label", "State ", stateSel),
      viewingOld
        ? h("button.btn.btn-primary", { type: "button", onclick: () => save(ed.blocks, d.state, d.title, latest) }, `Restore version ${d.version} as a new version`)
        : h("button.btn.btn-primary#studio-save", { type: "button", onclick: () => save(ed.blocks, stateSel.value, titleIn.value, d.version) }, "Save new version"),
      h("a.btn#export-html", { href: `/api/studio/documents/${encodeURIComponent(id)}/export?format=html&version=${d.version}`, download: "" }, "Export HTML"),
      h("a.btn#export-md", { href: `/api/studio/documents/${encodeURIComponent(id)}/export?format=md&version=${d.version}`, download: "" }, "Export Markdown"),
      h("button.btn", { type: "button", onclick: () => { const dl = openDialog("Delete this document?", h("p", "The document and all its versions are deleted permanently. Exported files are not affected."),
        [h("button.btn", { onclick: () => dl.close() }, "Cancel"), h("button.btn.btn-primary", { onclick: async () => {
          try { await api(`/api/studio/documents/${encodeURIComponent(id)}/delete`, { method: "POST" }); dl.close(); nav.go("/studio"); } catch (e) { toast(e.message); } } }, "Delete")]); } }, "Delete")),
    list,
    viewingOld ? null : h("div.ws-toolbar", h("span.muted", "Add: "),
      h("button.btn.btn-small", { type: "button", onclick: () => addBlock("text") }, "Text"),
      h("button.btn.btn-small", { type: "button", onclick: () => addBlock("heading") }, "Heading"),
      h("button.btn.btn-small", { type: "button", onclick: () => addBlock("question") }, "Question for legal review"),
      h("span.muted", " · Citations and quotations are added from the reader or the Commander workspace (\"Add to Studio\").")),
    h("section.ws-sect", { "data-sect": "versions" }, h("h2", "Version history"),
      h("ul.ws-list#studio-versions", vers.versions.map((v) => h("li", { "data-version": v.version },
        h("a", { href: "#", onclick: (e) => { e.preventDefault(); studioEditor(page, nav, id, v.version); } }, `Version ${v.version}`),
        ` · ${STATE[v.state] || v.state} · ${fmtDate(v.created_at)} · ${(v.bytes / 1000).toFixed(1)} kB`, v.version === d.version ? " (shown)" : null)))));
  draw();
  // On a withdrawal or reinstatement: without unsaved edits, reload the document; with unsaved edits, refresh only the
  // library blocks in place (the server re-renders them from the current eligible copy), keeping the author's text.
  const isCorpus = (b) => b.type === "citation" || b.type === "quote";
  const key = (b) => [b.type, b.doc_id, b.copy, b.page, b.passage_id || ""].join("|");
  current = { kind: "studio", render: async () => {
    if (!ed.changed) return studioEditor(page, nav, id, viewingOld ? d.version : undefined);
    try {
      const fresh = await api(`/api/studio/documents/${encodeURIComponent(id)}${viewingOld ? `?version=${d.version}` : ""}`);
      const m = new Map(fresh.blocks.filter(isCorpus).map((b) => [key(b), b]));
      ed.blocks = ed.blocks.map((b) => !isCorpus(b) ? b
        : m.get(key(b)) || { type: b.type, origin: "corpus", doc_id: b.doc_id, copy: b.copy, page: b.page, passage_id: b.passage_id, available: false, notice: "Source no longer available in this installation." });
      draw();
    } catch { /* the next policy change or reload re-checks */ }
  } };
}
