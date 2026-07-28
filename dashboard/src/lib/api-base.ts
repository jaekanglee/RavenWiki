/**
 * API base URL for the Raven Dashboard.
 *
 * Browser mode (vite dev / static serve): empty string — relative /api/...
 * URLs are proxied by vite or served by the same origin.
 *
 * Tauri desktop mode: set to the Python Core endpoint
 * (e.g. http://127.0.0.1:54321) before React renders.
 *
 * Multi-host mode (v0.8.0+): if an active remote host is selected,
 * the fetch/sendBeacon wrappers below dynamically prepend the active host's
 * endpoint to every /api/... request so the whole dashboard smoothly
 * switches target server context.
 */

let apiBase = "";

export function setApiBase(base: string): void {
  apiBase = base.replace(/\/+$/, "");
}

export function getApiBase(): string {
  return apiBase;
}

export function getActiveTargetBaseUrl(): string {
  if (typeof window === "undefined") return apiBase;
  try {
    const activeId = localStorage.getItem("raven:active_host") || "local";
    if (activeId === "local") return apiBase;
    const raw = localStorage.getItem("raven:hosts");
    if (!raw) return apiBase;
    const hosts = JSON.parse(raw);
    const found = hosts.find((h: any) => h.id === activeId);
    if (found && found.endpoint && !found.isLocal) {
      return found.endpoint.replace(/\/+$/, "");
    }
  } catch {}
  return apiBase;
}

// ─── install wrappers (module-load time, before any component mounts) ───

if (typeof window !== "undefined") {
  const origFetch = window.fetch.bind(window);
  window.fetch = (input: RequestInfo | URL, init?: RequestInit) => {
    const targetBase = getActiveTargetBaseUrl();
    if (targetBase && typeof input === "string" && input.startsWith("/api/")) {
      return origFetch(targetBase + input, init);
    }
    return origFetch(input, init);
  };

  const origBeacon = navigator.sendBeacon?.bind(navigator);
  if (origBeacon) {
    navigator.sendBeacon = (url: string | URL, data?: BodyInit | null) => {
      const targetBase = getActiveTargetBaseUrl();
      if (targetBase && typeof url === "string" && url.startsWith("/api/")) {
        return origBeacon(targetBase + url, data);
      }
      return origBeacon(url, data);
    };
  }
}
