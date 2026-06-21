// Cockpit control-token store. The token is the shared secret every state-changing
// Convex mutation validates (convex/control.ts). It arrives once via the pairing
// deep-link (`#t=<token>` — from the onboarding QR), is persisted to localStorage,
// then attached to every guarded mutation. Read-only queries never need it.
const KEY = "alien_control_token";

/**
 * Capture a token from the URL into localStorage, then return it.
 * Accepts both the hash form (`#t=...`, preferred — never hits server logs) and
 * the query form (`?t=...`, robust to link processors). The secret is stripped from
 * the address bar after capture; any other params (e.g. `?readonly`) are preserved.
 */
export function loadToken(): string | null {
  const hashParams = new URLSearchParams(location.hash.slice(1));
  const queryParams = new URLSearchParams(location.search);
  const incoming = hashParams.get("t") ?? queryParams.get("t");
  if (incoming) {
    localStorage.setItem(KEY, incoming.trim());
    hashParams.delete("t");
    queryParams.delete("t");
    const q = queryParams.toString();
    const h = hashParams.toString();
    history.replaceState(null, "", location.pathname + (q ? `?${q}` : "") + (h ? `#${h}` : ""));
  }
  return localStorage.getItem(KEY);
}

/** Persist a pasted/scanned token (used by the pairing screen). */
export function setToken(token: string): void {
  localStorage.setItem(KEY, token.trim());
}

/** Attach the stored control token to a mutation's args. */
export function withToken<T extends object>(args: T): T & { control_token: string } {
  return { ...args, control_token: localStorage.getItem(KEY) ?? "" };
}
