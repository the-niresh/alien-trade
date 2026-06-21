// Cockpit control-token store. The token is the shared secret every state-changing
// Convex mutation validates (convex/control.ts). It arrives once via the pairing
// deep-link (`#t=<token>` — from the onboarding QR), is persisted to localStorage,
// then attached to every guarded mutation. Read-only queries never need it.
const KEY = "alien_control_token";

/** Capture a token from the URL hash (`#t=...`) into localStorage, then return it. */
export function loadToken(): string | null {
  const hash = new URLSearchParams(location.hash.slice(1)).get("t");
  if (hash) {
    localStorage.setItem(KEY, hash);
    history.replaceState(null, "", location.pathname); // strip the secret from the URL
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
