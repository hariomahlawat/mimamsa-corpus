// Login, Statutes, Administration, citation permalinks and gated workspaces.
import { api, ApiError, state } from "./api.js";
import { h, append, clear, $, chip, candidateChip, fmtDate, short, typeLabel, toast, openDialog } from "./ui.js";
import { mountResearch, openDocument, R } from "./research.js";
const add = (el, ...k) => append(el, k);

export function loginPage(main, onDone, message) {
  clear(main);
  const err = h("div.err", { role: "alert", hidden: !message }, message || "");
  const form = h("form.login", { "aria-labelledby": "login-title" },
    h("h1#login-title", "Sign in to Mimamsa"),
    h("p", "Offline research library of published Indian military-law sources. Research and candidate data only: nothing here is legally verified."),
    err,
    h("div.form-row", h("label", { for: "username" }, "Username"), h("input#username", { name: "username", autocomplete: "username", required: true })),
    h("div.form-row", h("label", { for: "password" }, "Password"), h("input#password", { name: "password", type: "password", autocomplete: "current-password", required: true })),
    h("button.btn.btn-primary", { type: "submit", style: "width:100%" }, "Sign in"),
    h("p.sr-hint", { style: "margin-top:16px" }, "Local accounts. Five failed attempts lock the account for five minutes. Sessions end after 30 minutes without activity."));
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    err.hidden = true;
    try {
      const s = await api("/api/login", { method: "POST", body: { username: $("#username").value, password: $("#password").value } });
      onDone(s);
    } catch (ex) { err.textContent = ex.status === 0 ? "The server cannot be reached." : ex.message; err.hidden = false; $("#password").select(); }
  });
  add(main, h("div", { style: "flex:1;display:flex;overflow:auto;padding:24px" }, form));
  $("#username").focus();
}

export function gatePage(main, kind) {
  clear(main);
  const what = {
    assistant: ["Commander assistant", "Would answer situation questions for unit commanders with cited sources."],
    asof: ["As-of statute view", "Would show the text of a provision as it applied on a chosen date."],
  }[kind] || ["Closed feature", ""];
  add(main, h("div.page", h("div.gate.page-inner", { role: "region", "aria-labelledby": "gate-title", style: "max-width:72ch" },
    h("h2#gate-title", chip("gated", "Closed"), " ", what[0]),
    h("p", what[1]),
    h("p", h("strong", "Why it is closed: "), "No Legal Reviewer is appointed and AUTH-LEDGER is at version 0. No legal reasoning is available in this version."),
    h("p", "What must happen to open it:"),
    h("ul", h("li", "a Legal Reviewer appointment is recorded;"), h("li", "the underlying records receive recorded legal approvals;"), h("li", "the reasoning-feature gate is opened by the owner.")),
    h("p", "This page never shows sample or example outputs."),
    h("p", h("a", { href: "/r" }, "Return to research search")))));
}

export function laterPage(main, title, text) {
  clear(main);
  add(main, h("div.page", h("div.page-inner", { style: "max-width:72ch" }, h("h1", title), h("p", text),
    h("p", "Extracted links shown elsewhere in B1 are candidates; the absence of a link does not mean there is no related or adverse authority."),
    h("p", h("a", { href: "/r" }, "Return to research search")))));
}

// ------------------------------------------------------------------ statutes
export async function statutesPage(main, nav, docId, section) {
  clear(main);
  const ws = h("div.workspace", h("nav.pane.rail#statute-rail", { "aria-label": "Acts, Rules and Regulations" }, h("span.skeleton.w80"), h("span.skeleton.w60")),
    h("div.pane#statute-main", { style: "display:flex;flex-direction:column;min-height:0" }));
  add(main, ws);
  let list;
  try { list = (await api("/api/statutes")).statutes; } catch (e) { $("#statute-rail").replaceChildren(h("p", { role: "alert" }, e.message)); return; }
  const rail = clear($("#statute-rail"));
  const sm = $("#statute-main");
  if (!docId) {
    add(rail, h("h2", "Acts, Rules and Regulations"), h("div.statute-list", list.map((s) => h("a", { href: `/s/${encodeURIComponent(s.doc_id)}`, onclick: (e) => { e.preventDefault(); nav.go(`/s/${encodeURIComponent(s.doc_id)}`); } },
      h("div", { lang: s.language === "hi" ? "hi" : null }, s.title || s.doc_id), h("div.sub", `${typeLabel(s.type)}${s.number ? " · " + s.number : ""} · ${s.page_count} pp${s.language === "hi" ? " · Hindi" : ""}`)))));
    add(sm, h("div.docempty", h("h2", "Statutes"), h("p", "Choose an Act, Rules or Regulations to see its table of contents, read a section at its page in the original, and see temporal version candidates."),
      h("p", chip("gated", "As-of date: closed"), " The as-of control is not available: the temporal chain is not established and no legal approval exists.")));
    return;
  }
  const s = list.find((x) => x.doc_id === docId);
  let toc;
  try { toc = await api(`/api/documents/${encodeURIComponent(docId)}/sections`); }
  catch (e) { add(sm, h("div.docempty", { role: "alert" }, h("h2", "Not available"), h("p", "This document is not available in this installation."))); return; }
  add(rail, h("a", { href: "/s", onclick: (e) => { e.preventDefault(); nav.go("/s"); } }, "← All statutes"),
    h("h2", { style: "margin-top:12px", lang: s?.language === "hi" ? "hi" : null }, s?.title || docId),
    h("p.sr-hint", toc.note),
    toc.sections?.length ? h("ul.toc", { role: "tree", "aria-label": "Table of contents" }, toc.sections.map((e) => h("li", { role: "treeitem", "aria-selected": String(e.number === section) },
      h("a", { href: `/s/${encodeURIComponent(docId)}/${encodeURIComponent(e.number)}`, "aria-current": e.number === section ? "true" : null, tabindex: "0",
        onclick: (ev) => { ev.preventDefault(); nav.go(`/s/${encodeURIComponent(docId)}/${encodeURIComponent(e.number)}`); } },
        h("span.num", e.number), h("span", { class: e.omitted_as_printed ? "omitted" : null }, e.heading))))) : h("p.muted", "No section headings were found in the extracted text."));
  const entry = toc.sections?.find((e) => e.number === section);
  const asof = h("div.notice.info", { style: "margin:0;border-left-color:var(--status-gated-fg)" },
    h("label", { for: "asof" }, "As of date "), h("input#asof", { type: "date", disabled: true, "aria-describedby": "asof-why" }),
    h("span#asof-why", chip("gated", "Closed"), " Temporal chain not established. Closed: needs a Legal Reviewer appointment and recorded approvals. No legal reasoning is available in this version."));
  add(sm, asof);
  if (entry) {
    const provs = section ? [`s.${section}`, `r.${section}`, `reg.${section}`, `Section ${section}`, `Rule ${section}`] : [];
    const strip = h("section.dochead", { "aria-label": "Amendment strip" }, h("h2", `Section ${entry.number}. ${entry.heading}`),
      h("p.muted", "Heading and any amendment note are compilation text as printed in the held copy. They are not a verified amendment history."),
      entry.omitted_as_printed ? h("div.notice", "The held compilation prints this provision as omitted. Commencement and chain are not established here.") : null,
      h("div#a4strip", h("span.skeleton.w60")));
    add(sm, strip);
    add(sm, h("div#statute-doc", { style: "flex:1;min-height:0;display:flex" }));
    mountResearch($("#statute-doc"), nav).classList.add("statute-mode", "doc-open");
    await openDocument({ docId, page: entry.page, passage: entry.passage_id }, { push: false });
    try {
      const doc = await api(`/api/documents/${encodeURIComponent(docId)}`);
      const vs = doc.provision_versions.filter((v) => provs.includes(v.provision));
      $("#a4strip").replaceChildren(vs.length ? h("div", h("p", candidateChip(), " Temporal version candidates (A4). Temporal chain not established."),
        vs.map((v) => h("div.cand", h("div.cand-head", h("strong", v.version_kind.replaceAll("_", " ")), h("span.mono.muted", v.version_id), h("span.muted", `linked by ${v.linked_by}`)),
          h("div.cand-body", v.change_summary || "", h("div", `Effective from: ${v.effective_from.status?.replaceAll("_", " ") || "not recorded"}${v.effective_from.date ? " " + v.effective_from.date : ""}${v.effective_from.reported_date ? ` (reported in compilation: ${v.effective_from.reported_date})` : ""}`),
            h("div", `Effective to: ${v.effective_to_status?.replaceAll("_", " ") || "not recorded"} · currency ${v.currency || "not recorded"}`),
            v.evidence.map((e) => h("div.muted", `${e.role.replaceAll("_", " ")}: ${e.resolution.replaceAll("_", " ").toLowerCase()}${e.page ? ` (p.${e.page})` : ""}`))))))
        : h("p.muted", "No A4 temporal version candidate is recorded for this provision with evidence in this copy."));
    } catch { $("#a4strip").replaceChildren(h("p.muted", "Version candidates could not be loaded.")); }
  } else {
    add(sm, h("div#statute-doc", { style: "flex:1;min-height:0;display:flex" }));
    mountResearch($("#statute-doc"), nav).classList.add("statute-mode", "doc-open");
    await openDocument({ docId, page: 1 }, { push: false });
  }
}

// ------------------------------------------------------------------ citation permalinks (ASR-E06)
export async function citePage(main, nav, parts) {
  const [releaseId, docId, sha12, page] = parts;
  const pg = parseInt(page, 10);
  clear(main);
  let r;
  try { r = await api(`/api/cite?doc=${encodeURIComponent(docId)}&sha=${encodeURIComponent(sha12)}&page=${pg}`); }
  catch (e) { add(main, h("div.page", h("div.error-state", { role: "alert" }, h("p", e.message)))); return; }
  if (r.state === "CITED_COPY_ELIGIBLE" || r.state === "CITED_COPY_ELIGIBLE_NOT_CURRENT") {
    mountResearch(main, nav);
    await openDocument({ docId, page: r.page, copy: r.state === "CITED_COPY_ELIGIBLE" ? null : r.copy, notice: r.notice || `Cited copy ${short(r.copy)} at physical page ${r.page} (citation made in release ${releaseId}).`,
      citeState: r.state, currentCopy: r.current_copy, copyPages: r.copy_pages, firstRelease: r.first_release }, { push: false });
    return;
  }
  add(main, h("div.page", h("div.page-inner", { style: "max-width:72ch" }, h("h1", "Citation"),
    h("div.notice", { role: "alert", "data-cite-state": r.state }, r.notice),
    h("p.muted", "The citation and internal reference keep the original copy hash and page. No other copy or page is opened in its place."),
    h("p", h("a", { href: "/r" }, "Return to research search")))));
}

// ------------------------------------------------------------------ administration
export async function adminPage(main, nav) {
  clear(main);
  const page = h("div.page", h("div.page-inner", h("h1", "Administration"), h("div#admin-body", h("span.skeleton.w60"))));
  add(main, page);
  let o;
  try { o = await api("/api/admin/overview"); }
  catch (e) { $("#admin-body").replaceChildren(h("div.error-state", { role: "alert" }, h("p", e.status === 403 ? "This action is for Admins." : e.message))); return; }
  const body = clear($("#admin-body"));
  add(body, h("p.muted", "Release import and staging screens arrive with B2. B1 shows the verified active generation and lets an Admin withdraw a published document."),
    h("h2", { style: "margin:16px 0 8px" }, "Active release"),
    h("dl.cards", [["Release", o.release.release_id], ["Generation", o.generation], ["HF revision", o.release.hf_revision_short], ["Created", fmtDate(o.release.created_at)],
      ["Documents verified", o.verified.documents], ["Derivatives verified", o.verified.derivatives], ["Candidates verified", o.verified.candidates],
      ["Originals re-hashed at start", o.verified.originals_rehashed_ok], ["Quarantined at import", o.quarantine.length], ["Exclusion channel", o.release.exclusion_channel],
      ["Serving policy epoch", o.policy.epoch], ["AUTH-LEDGER version", o.release.auth_ledger_version]].map(([k, v]) => h("div", h("dt", k), h("dd.mono", String(v))))),
    Object.keys(o.load_issues || {}).length ? h("div.notice", `Load issues: ${Object.entries(o.load_issues).map(([k, v]) => `${k}=${v}`).join(", ")}`) : h("p.muted", "No load issues: every served item passed the service's start-up re-checks."),
    h("h2", { style: "margin:24px 0 8px" }, "Withdraw a published document"),
    h("form#withdraw-form", { style: "max-width:640px" },
      h("div.form-row", h("label", { for: "wd-doc" }, "Document id"), h("input#wd-doc", { required: true, spellcheck: "false", placeholder: "e.g. sc-2013-dharamvir-singh-2013insc408" }),
        h("span.hint", "The current copy of the document is withdrawn for every user at once.")),
      h("div.form-row", h("label", { for: "wd-reason" }, "Reason (required)"), h("textarea#wd-reason", { rows: "2", required: true, minlength: "3", maxlength: "500" })),
      h("button.btn", { type: "submit" }, "Withdraw…")),
    h("h2", { style: "margin:24px 0 8px" }, "Withdrawals"),
    o.withdrawals.length ? h("table.data", h("thead", h("tr", ["When", "Document", "Copy", "Reason", "Actor", "Epoch"].map((x) => h("th", { scope: "col" }, x)))),
      h("tbody", o.withdrawals.map((w) => h("tr", h("td", fmtDate(w.at)), h("td.mono", w.doc_id), h("td.mono", short(w.copy)), h("td", w.reason), h("td.mono", w.actor), h("td", w.epoch)))))
      : h("p.muted", "No withdrawals."),
    h("h2", { style: "margin:24px 0 8px" }, "Quarantined at import"),
    o.quarantine.length ? h("table.data", h("thead", h("tr", ["Kind", "Item", "Reasons"].map((x) => h("th", { scope: "col" }, x)))),
      h("tbody", o.quarantine.slice(0, 200).map((q) => h("tr", h("td", q.kind), h("td.mono", q.id), h("td", (q.reasons || []).join("; "))))))
      : h("p.muted", "Nothing was quarantined by the importer for this generation."));
  $("#withdraw-form").addEventListener("submit", (e) => {
    e.preventDefault();
    const doc = $("#wd-doc").value.trim(), reason = $("#wd-reason").value.trim();
    if (reason.length < 3) { toast("A reason is required"); return; }
    const d = openDialog("Withdraw this document?", h("div", h("p", h("strong.mono", doc)),
      h("p", "Every copy of this document, including earlier editions, disappears from search, document views, citation links and original delivery for every user, effective immediately. Open viewers are cut off."),
      h("p", "Byte-identical copies held under another document id are separate documents and are not withdrawn by this action."),
      h("p", "Withdrawal is recorded with your account and the reason. It is not legal approval or disapproval.")),
      [h("button.btn", { onclick: () => d.close() }, "Cancel"), h("button.btn.btn-primary", { onclick: async () => {
        try { const r = await api("/api/admin/withdraw", { method: "POST", body: { doc_id: doc, reason } }); d.close(); toast(r.status === "withdrawn" ? `Withdrawn (policy epoch ${r.epoch})` : "Already withdrawn"); adminPage(main, nav); }
        catch (ex) { d.close(); toast(ex.message); }
      } }, "Withdraw")]);
  });
}
void ApiError; void state; void R;
