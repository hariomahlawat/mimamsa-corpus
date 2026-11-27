// C15 WP3/WP4: Graph inspection workspace (list view). Shows a node of the legal knowledge graph with its typed
// relationships, each with its verification status, evidence page and uncertainty, and a research-only evidence
// assessment panel. Every relationship is a candidate, structure read from held text, or a navigation aid; nothing
// here is a verified legal fact or advice. Data: /api/graph/*, /api/reasoning/* (docs/architecture/b1/C15_GRAPH_API.md).
import { api } from "./api.js";
import { h, append, clear, chip, candidateChip } from "./ui.js";

const add = (el, ...k) => append(el, k);
const EXAMPLES = [["act-army-1950", "69", "Army Act s.69"], ["act-army-1950", "75", "Army Act s.75"], ["act-ipc-1860", "302", "IPC s.302"],
  ["act-bns-2023", "103", "BNS s.103"], ["sc-2013-dharamvir-singh-2013insc408", "", "Dharamvir Singh (2013)"]];
const STATE = { ESTABLISHED: ["ok", "Established"], CANDIDATE: ["candidate", "Candidate"], INSUFFICIENT_INFORMATION: ["warning", "Insufficient information"] };

function verChip(v) {
  if (v === "CANDIDATE") return candidateChip();
  if (v === "CURATED_NAVIGATION") return chip("neutral", "Navigation aid", "Chosen for navigation; not a statement of a legal requirement");
  return chip("neutral", "Structure", "Structure read from the held text");
}

export async function graphPage(main, nav) {
  clear(main);
  const u = new URL(location.href);
  const root = h("section.graph-page", { "aria-label": "Legal knowledge graph" });
  add(main, root);
  const docIn = h("input#g-doc", { placeholder: "Document id, e.g. act-army-1950", spellcheck: "false", value: u.searchParams.get("doc") || "" });
  const secIn = h("input#g-sec", { placeholder: "Section or rule (optional)", spellcheck: "false", value: u.searchParams.get("section") || "" });
  const form = h("form#g-form.g-form", { onsubmit: (e) => { e.preventDefault(); go(docIn.value.trim(), secIn.value.trim()); } },
    h("label.visually-hidden", { for: "g-doc" }, "Document id"), docIn, h("label.visually-hidden", { for: "g-sec" }, "Section or rule"), secIn,
    h("button.btn.btn-primary", { type: "submit" }, "Show relationships"));
  const statsBox = h("p.muted#g-stats", "Loading graph statistics…");
  const body = h("div#g-body");
  add(root, h("header.home-head", h("h2", "Legal knowledge graph ", chip("candidate", "Research")),
      h("p.home-summary", "Typed relationships derived from held records: tables of contents, provision-version candidates, citation candidates, comparison tables and repeal notices. None is a verified legal fact; absence of a relationship is not evidence that none exists.")),
    statsBox, form, h("p.g-examples", "Examples: ", EXAMPLES.map(([d, s, l], i) => [i ? " · " : "", h("a", { href: "#", onclick: (e) => { e.preventDefault(); docIn.value = d; secIn.value = s; go(d, s); } }, l)])), body);

  api("/api/graph/stats").then((s) => {
    statsBox.textContent = `${s.nodes.toLocaleString("en-GB")} nodes · ${s.edges.toLocaleString("en-GB")} relationships (` +
      Object.entries(s.edges_by_verification).map(([k, v]) => `${v.toLocaleString("en-GB")} ${k.toLowerCase().replaceAll("_", " ")}`).join(", ") + `) · AUTH-LEDGER v${s.auth_ledger_version}`;
  }).catch(() => { statsBox.textContent = "The legal knowledge graph is not available in this installation."; });

  async function go(doc, section, push = true) {
    if (!doc) return;
    if (push) nav.replace(`/g?doc=${encodeURIComponent(doc)}${section ? `&section=${encodeURIComponent(section)}` : ""}`);
    clear(body); add(body, h("span.skeleton.w60"));
    let r;
    try { r = await api(`/api/graph/resolve?doc=${encodeURIComponent(doc)}${section ? `&section=${encodeURIComponent(section)}` : ""}`); }
    catch { clear(body); add(body, h("p.notice", "This document is not available in this installation, or it is not part of the graph.")); return; }
    await showNode(r.node_id, doc, section);
  }

  async function showNode(id, doc, section) {
    let n;
    try { n = await api(`/api/graph/node?id=${encodeURIComponent(id)}&depth=1`); }
    catch { clear(body); add(body, h("p.notice", "This item is not available in this installation.")); return; }
    clear(body);
    const groups = new Map();
    for (const e of n.edges) { const k = e.type; (groups.get(k) || groups.set(k, []).get(k)).push(e); }
    add(body, h("h3.g-node", n.node.label, " ", h("span.muted", `(${n.node.kind.replaceAll("_", " ")}${n.node.held ? "" : ", not located in a held copy"})`)),
      n.edges.length ? null : h("p.muted", n.absence),
      [...groups.entries()].map(([type, list]) => h("details.sect.g-group", { open: list.length <= 12 ? true : null, "data-type": type },
        h("summary", `${type.replaceAll("_", " ").toLowerCase()} (${list.length})`),
        h("table.data.g-edges", h("thead", h("tr", ["Direction", "Other end", "Status", "Evidence", "Temporal scope"].map((x) => h("th", { scope: "col" }, x)))),
          h("tbody", list.map((e) => {
            const out = e.from.id === n.node.id; const other = out ? e.to : e.from;
            return h("tr", { "data-edge": e.id },
              h("td", out ? "→" : "←"),
              h("td", other.held || other.kind === "procedural_requirement"
                ? h("a", { href: "#", onclick: (ev) => { ev.preventDefault(); showNode(other.id); } }, other.label) : h("span", other.label)),
              h("td", verChip(e.verification), e.has_legal_effect ? h("div.muted", "has legal effect if verified") : null),
              h("td", e.source ? h("a", { href: `/d/${encodeURIComponent(e.source.doc_id)}?p=${e.source.page || 1}`, onclick: (ev) => { ev.preventDefault(); nav.go(`/d/${encodeURIComponent(e.source.doc_id)}?p=${e.source.page || 1}`); } },
                `${e.source.doc_id}${e.source.page ? ` p.${e.source.page}` : ""}`) : "—", e.quote ? h("q.g-quote", e.quote) : null, h("div.muted", e.uncertainty)),
              h("td", `${e.temporal.from_status.replaceAll("_", " ").toLowerCase()}${e.temporal.from ? ` (${e.temporal.from})` : ""}`));
          }))))),
      n.truncated ? h("p.notice", "Only the first relationships are shown.") : null);
    if (n.node.kind === "provision" && doc && section) add(body, assessPanel(doc, section));
  }

  function assessPanel(doc, section) {
    const asOf = h("input#g-asof", { type: "date", "aria-label": "As-of date" });
    const conduct = h("input#g-conduct", { type: "date", "aria-label": "Date of the act or omission" });
    const proceeding = h("input#g-proceeding", { type: "date", "aria-label": "Date the proceeding started" });
    const out = h("div#g-assess-out");
    const run = async (kind) => {
      clear(out); add(out, h("span.skeleton.w40"));
      const q = new URLSearchParams({ kind, doc, section });
      if (asOf.value) q.set("as_of", asOf.value);
      if (conduct.value) q.set("conduct_date", conduct.value);
      if (proceeding.value) q.set("proceeding_date", proceeding.value);
      try { renderAssessment(out, await api(`/api/reasoning/assess?${q}`)); } catch { clear(out); add(out, h("p.notice", "The assessment could not be produced.")); }
    };
    return h("section.sect.g-assess", { "aria-label": "Research assessment" },
      h("h3", "Research assessment ", chip("candidate", "Research only")),
      h("p.muted", "States what the held evidence shows and what is missing. It does not decide which law applies and is not legal advice."),
      h("div.g-form", h("label", "As of ", asOf), h("label", "Act or omission on ", conduct), h("label", "Proceeding started ", proceeding)),
      h("div.g-form", h("button.btn", { type: "button", onclick: () => run("temporal") }, "Which version on the as-of date?"),
        h("button.btn", { type: "button", onclick: () => run("succession") }, "Commencement, repeal, savings, correspondence"),
        h("button.btn", { type: "button", onclick: () => run("conflicts") }, "Conflicting or unresolved records")), out);
  }

  const d0 = u.searchParams.get("doc");
  if (d0) go(d0, u.searchParams.get("section") || "", false);
}

export function renderAssessment(out, a) {
  clear(out);
  const [k, label] = STATE[a.overall] || ["neutral", a.overall];
  add(out, h("p.g-overall", { "data-state": a.overall }, "Overall: ", chip(k, label)),
    h("ul.g-findings", a.findings.map((f) => { const [fk, fl] = STATE[f.state] || ["neutral", f.state];
      return h("li", { "data-code": f.code, "data-state": f.state }, chip(fk, fl), " ", f.statement,
        f.evidence.length ? h("div.muted", f.evidence.map((e, i) => [i ? " · " : "", `${e.doc_id}${e.page ? ` p.${e.page}` : ""}`])) : null); })),
    a.missing_facts.length ? h("div.notice", h("strong", "Missing facts: "), a.missing_facts.join("; ")) : null,
    (a.blockers || []).length ? h("div.notice", h("strong", "Not evaluated: "), a.blockers.join(" ")) : null,
    h("p.sr-hint", a.notice));
}
