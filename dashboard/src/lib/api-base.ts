/**
 * API base URL for the Raven Dashboard.
 *
 * Browser mode (vite dev / static serve): empty string — relative /api/...
 * URLs are proxied by vite or served by the same origin.
 *
 * Tauri desktop mode: set to the Python Core endpoint
 * (e.g. http://127.0.0.1:54321) before React renders.
 *
 * The fetch/sendBeacon wrappers below prepend apiBase to every /api/...
 * request so the ~30 existing call sites need zero changes.
 */

let apiBase = "";

export function setApiBase(base: string): void {
  apiBase = base.replace(/\/+$/, "");
}

export function getApiBase(): string {
  return apiBase;
}

// ─── install wrappers (module-load time, before any component mounts) ───

if (typeof window !== "undefined") {
  const origFetch = window.fetch.bind(window);
  window.fetch = (input: RequestInfo | URL, init?: RequestInit) => {
    if (apiBase && typeof input === "string" && input.startsWith("/api/")) {
      return origFetch(apiBase + input, init);
    }
    return origFetch(input, init);
  };

  const origBeacon = navigator.sendBeacon?.bind(navigator);
  if (origBeacon) {
    navigator.sendBeacon = (url: string | URL, data?: BodyInit | null) => {
      if (apiBase && typeof url === "string" && url.startsWith("/api/")) {
        return origBeacon(apiBase + url, data);
      }
      return origBeacon(url, data);
    };
  }
}
