// Same-origin JSON API client. Session is an HttpOnly cookie; state-changing calls send the CSRF token.
// Responses are never cached (server sends no-store; fetch uses cache: "no-store").
export const state = { session: null, online: true, listeners: new Set(), epoch: null };

/** C14 F05: every API response names the serving-policy epoch; a change means a withdrawal or reinstatement happened,
 *  and open documents must be re-checked (event "mimamsa:policy-changed"). */
export function noteEpoch(r) {
  const v = r?.headers?.get?.("X-Mimamsa-Policy-Epoch");
  if (v == null || v === "") return;
  const e = Number(v);
  if (!Number.isFinite(e)) return;
  const before = state.epoch;
  state.epoch = e;
  if (before !== null && before !== e) window.dispatchEvent(new CustomEvent("mimamsa:policy-changed", { detail: { from: before, to: e } }));
}

export class ApiError extends Error {
  constructor(status, body) { super(body?.error || body?.notice || `HTTP ${status}`); this.status = status; this.body = body; }
}

function setOnline(v) {
  if (state.online === v) return;
  state.online = v;
  for (const f of state.listeners) f(v);
}

export async function api(path, { method = "GET", body, signal } = {}) {
  const headers = { Accept: "application/json" };
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (method !== "GET" && state.session?.csrf) headers["X-CSRF-Token"] = state.session.csrf;
  let r;
  try {
    r = await fetch(path, { method, headers, body: body === undefined ? undefined : JSON.stringify(body), credentials: "same-origin", cache: "no-store", signal });
  } catch (e) {
    if (e.name === "AbortError") throw e;
    setOnline(false);
    throw new ApiError(0, { error: "Connection to the server lost." });
  }
  setOnline(true);
  noteEpoch(r);
  let data = null;
  try { data = await r.json(); } catch { data = null; }
  if (r.status === 401 && path !== "/api/login" && path !== "/api/session") { window.dispatchEvent(new CustomEvent("mimamsa:unauthenticated")); }
  if (!r.ok) throw new ApiError(r.status, data);
  return data;
}

export async function probe() {
  try { const r = await fetch("/health", { cache: "no-store" }); setOnline(r.ok); return r.ok; } catch { setOnline(false); return false; }
}
