// Small DOM helpers and shared components (status chips, notices, dialogs). No framework, no network.

/** h("div.cls#id", {attrs}, ...children) */
export function h(tag, attrs, ...kids) {
  const m = /^([a-z0-9]+)((?:[.#][\w-]+)*)$/i.exec(tag);
  const el = document.createElement(m ? m[1] : tag);
  if (m && m[2]) for (const part of m[2].match(/[.#][\w-]+/g)) part[0] === "." ? el.classList.add(part.slice(1)) : (el.id = part.slice(1));
  if (attrs && (typeof attrs !== "object" || attrs instanceof Node || Array.isArray(attrs))) { kids.unshift(attrs); attrs = null; }
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v === null || v === undefined || v === false) continue;
    if (k === "class") el.className = v;
    else if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else if (k === "dataset") Object.assign(el.dataset, v);
    else if (k === "text") el.textContent = v;
    else if (k === "style") el.style.cssText = v;   // CSSOM, allowed under the style-src 'self' CSP
    else el.setAttribute(k, v === true ? "" : String(v));
  }
  append(el, kids);
  return el;
}
export function append(el, kids) {
  for (const k of kids.flat(Infinity)) {
    if (k === null || k === undefined || k === false) continue;
    el.append(k instanceof Node ? k : document.createTextNode(String(k)));
  }
  return el;
}
export const clear = (el) => { while (el.firstChild) el.firstChild.remove(); return el; };
export const $ = (sel, root = document) => root.querySelector(sel);
export const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

export function icon(name) {
  const paths = {
    prev: "M10 3 5 8l5 5", next: "M6 3l5 5-5 5", close: "M4 4l8 8M12 4l-8 8", copy: "M5 5h8v8H5zM3 11V3h8",
    filter: "M2 3h12l-5 6v4l-2 1V9z", panel: "M2 3h12v10H2zM10 3v10", minus: "M3 8h10", plus: "M3 8h10M8 3v10",
    cite: "M3 4h4v4l-2 4M9 4h4v4l-2 4", page: "M4 2h6l3 3v9H4z", lock: "M4 7V5a4 4 0 0 1 8 0v2M3 7h10v7H3z", list: "M3 4h10M3 8h10M3 12h10",
  };
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("width", "16"); svg.setAttribute("height", "16"); svg.setAttribute("viewBox", "0 0 16 16");
  svg.setAttribute("aria-hidden", "true"); svg.setAttribute("focusable", "false");
  const p = document.createElementNS("http://www.w3.org/2000/svg", "path");
  p.setAttribute("d", paths[name] || ""); p.setAttribute("fill", "none"); p.setAttribute("stroke", "currentColor");
  p.setAttribute("stroke-width", "1.5"); p.setAttribute("stroke-linecap", "square");
  svg.append(p);
  return svg;
}

export function chip(kind, text, title) { return h(`span.chip.chip-${kind}`, { title: title || null }, text); }
export const candidateChip = (title) => chip("candidate", "Candidate", title || "Candidate (automated, not verified). AUTOMATED_CANDIDATE_NOT_VERIFIED");

/** Status chip for a status-axis value: glyph + text + colour, never colour alone; no "verified" wording. */
export function axisChip(axis, value) {
  const label = (value || "not recorded").replaceAll("_", " ").toLowerCase().replace(/^./, (c) => c.toUpperCase());
  if (!value) return chip("neutral", "Not recorded");
  if (value === "AUTOMATED_CANDIDATE_NOT_VERIFIED") return chip("candidate", "Candidate (automated, not verified)");
  if (["DOCUMENTARY_CHECKED", "FIDELITY_VERIFIED"].includes(value)) return chip("checked", "Checked against source");
  if (axis === "source_integrity" && value === "BYTE_VERIFIED") return chip("neutral", "Bytes re-hashed (SHA-256)");
  if (["MISMATCH", "INCORRECT", "REJECTED", "FAILED", "WITHDRAWN"].includes(value)) return chip("error", label);
  if (["T0_RESEARCH_ONLY", "NOT_ESTABLISHED"].includes(value)) return chip("gated", value === "T0_RESEARCH_ONLY" ? "T0 Research only" : "Not established");
  if (["UNKNOWN", "NOT_EVALUATED", "NOT_CHECKED", "TRUNCATED_AT_SOURCE"].includes(value)) return chip("warning", label);
  return chip("neutral", label);
}

export const fmtDate = (iso) => {
  if (!iso) return null;
  const d = new Date(iso.length === 10 ? iso + "T00:00:00Z" : iso);
  if (isNaN(d)) return iso;
  return d.toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" });
};
export const short = (sha) => (sha || "").slice(0, 12);
export const host = (url) => { try { return new URL(url).host; } catch { return url || "not recorded"; } };
export const typeLabel = (t) => ({ act: "Act", rules: "Rules", regulations: "Regulations", notification: "Notification", judgment: "Judgment",
  order: "Order", manual: "Manual", other: "Other", book_historical: "Historical book" }[t] || t);

let toastTimer = null;
export function toast(msg) {
  const t = document.getElementById("toast");
  t.textContent = msg; t.hidden = false;
  clearTimeout(toastTimer); toastTimer = setTimeout(() => { t.hidden = true; }, 3200);
}
export function announce(msg) { const a = document.getElementById("announcer"); a.textContent = ""; setTimeout(() => { a.textContent = msg; }, 30); }

/** Modal dialog with focus trap (native <dialog>), Esc closes, focus returns to the opener. */
export function openDialog(title, body, actions = []) {
  const d = document.getElementById("dialog");
  const opener = document.activeElement;
  clear(d);
  append(d, [h("h2#dialog-title", title), body, h("div.actions", actions.length ? actions : [h("button.btn", { onclick: () => d.close() }, "Close")])]);
  d.onclose = () => { if (opener && opener.focus) opener.focus(); };
  d.showModal();
  const f = d.querySelector("input, textarea, select, button.btn-primary, button");
  if (f) f.focus();
  return d;
}

export async function copyText(text) {
  try { if (navigator.clipboard && window.isSecureContext) { await navigator.clipboard.writeText(text); return true; } } catch { /* fall through */ }
  const ta = h("textarea", { style: "position:fixed;left:-9999px;top:0", "aria-hidden": "true" }); ta.value = text;
  document.body.append(ta); ta.select();
  let ok = false; try { ok = document.execCommand("copy"); } catch { ok = false; }
  ta.remove();
  return ok;
}

/** Excerpt text with <mark> highlight ranges [[start,end],...] (offsets into the excerpt). */
export function marked(text, ranges) {
  const frag = document.createDocumentFragment();
  let pos = 0;
  for (const [s, e] of ranges || []) {
    if (s < pos) continue;
    frag.append(text.slice(pos, s), h("mark", text.slice(s, e)));
    pos = e;
  }
  frag.append(text.slice(pos));
  return frag;
}

export const session = { get(k) { try { return sessionStorage.getItem(k); } catch { return null; } },
  set(k, v) { if (!["pane_widths", "rail_collapsed", "view_mode", "theme"].includes(k)) return; try { sessionStorage.setItem(k, v); } catch { /* ignore */ } } };
