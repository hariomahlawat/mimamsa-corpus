// C14 S3: statutory relationships view shared by the Statutes section view and the document context pane.
// Notices quote held text with page links; correspondence rows are labelled candidates from a secondary table, with the
// caution that corresponding provisions are not legally interchangeable. Nothing here is a legal determination.
import { h, append, candidateChip, chip } from "./ui.js";

const add = (el, ...k) => append(el, k);
const KIND_ORDER = ["repealed_by", "commencement_delegated", "commencement_notification_not_held", "commencement_secondary_source", "repeal", "savings_transitional"];

function evidenceLink(ev, onOpen, label) {
  if (!ev) return null;
  if (!ev.doc_id) return h("div.muted", "Evidence copy is not available in this installation.");
  return h("div.rel-ev", ev.quote ? h("q", ev.quote) : null,
    h("div", h("a", { href: "#", onclick: (e) => { e.preventDefault(); onOpen(ev.doc_id, ev.page); } }, `${label || "Open"} p.${ev.page}${ev.title ? ` · ${ev.title}` : ""}`)));
}

function sectionLink(t, nav) {
  if (!t) return null;
  const text = `${t.title || t.family} s.${t.section}`;
  return t.held && t.doc_id
    ? h("a", { href: `/s/${encodeURIComponent(t.doc_id)}/${encodeURIComponent(t.section)}`, onclick: (e) => { e.preventDefault(); nav.go(`/s/${encodeURIComponent(t.doc_id)}/${encodeURIComponent(t.section)}`); } }, text)
    : h("span", text, h("span.muted", " (not held in this library)"));
}

/** Render a /api/documents/{id}/relations response. `onOpen(docId, page)` opens evidence; `nav` routes Statutes links. */
export function renderRelations(box, r, { onOpen, nav, showNotices = true, noticesCollapsed = false }) {
  const wrap = h("div.relations", { "data-relations": r.doc_id });
  add(box, wrap);
  if (!r.instrument) { add(wrap, h("p.muted", "No statutory relationships: this document is not an Act, Rules or Regulations held in this library.")); return; }
  if (r.correspondence.length) {
    const s = h("div.sect", { "data-rel": "correspondence" }, h("h3", "Corresponding provisions ", candidateChip("Candidate (automated, not verified)")),
      h("div.absence", r.caution));
    for (const c of r.correspondence) {
      const head = c.direction === "replaces"
        ? (c.new_provision
          ? h("span", `s.${c.new_section}: a new provision; the comparison table names no counterpart in the repealed code.`)
          : h("span", `s.${c.new_section} corresponds to `, ...(c.other || []).flatMap((t, i) => [i ? ", " : null, sectionLink(t, nav)]), " in the repealed code."))
        : h("span", `This section (s.${c.this_section}) corresponds to `, sectionLink((c.other || [])[0], nav), c.new_section !== (c.other || [])[0]?.section ? ` (row ${c.new_section})` : "", " in the new code.");
      add(s, h("div.cand.rel-row", { "data-direction": c.direction }, h("div.cand-head", candidateChip(c.label), head),
        h("div.cand-body", h("div.muted", `Comparison table (secondary source), row as printed:`), evidenceLink({ doc_id: c.evidence.doc_id, page: c.evidence.page, quote: c.evidence.row, title: c.evidence.title }, onOpen, "Open the table at"))));
    }
    add(wrap, s);
  } else if (r.sections?.length) {
    add(wrap, h("p.muted", `No corresponding provision is recorded in the held comparison tables for s.${r.sections.join(", s.")}.`));
  }
  if (showNotices && r.notices.length) {
    const lead = h("p.muted", "Read from the held texts, with the page each statement comes from. Dates and effects on a particular matter are not determined here.");
    const s = noticesCollapsed
      ? h("details.sect", { "data-rel": "notices" }, h("summary", `Commencement, repeal and savings of this instrument (${r.notices.length})`), lead)
      : h("div.sect", { "data-rel": "notices" }, h("h3", "Commencement, repeal and savings"), lead);
    for (const n of [...r.notices].sort((a, b) => KIND_ORDER.indexOf(a.kind) - KIND_ORDER.indexOf(b.kind)))
      add(s, h("div.rel-notice", { "data-kind": n.kind }, h("div.rel-title", n.kind === "commencement_notification_not_held" ? chip("warning", "Not held") : null, h("strong", n.title)),
        h("div", n.text), evidenceLink(n.evidence, onOpen, "Open"), h("div.sr-hint", n.basis)));
    add(wrap, s);
  }
  add(wrap, h("p.sr-hint", r.absence));
}
