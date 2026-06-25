/**
 * Active vault store (simple, no zustand needed).
 *
 * Vault identity is stored in localStorage so refresh keeps the choice.
 * Components read this through `useActiveVault()` and refresh when needed.
 */
export const ACTIVE_VAULT_KEY = "wikisys:active_vault";

export function getActiveVault(): string {
  return localStorage.getItem(ACTIVE_VAULT_KEY) || "";
}

export function setActiveVault(name: string): void {
  localStorage.setItem(ACTIVE_VAULT_KEY, name);
}

export interface VaultInfo {
  name: string;
  path: string;
  mode: string;
  owner: string;
  default: boolean;
}

export async function fetchVaults(): Promise<VaultInfo[]> {
  const r = await fetch("/api/vaults");
  if (!r.ok) return [];
  const d = await r.json();
  return d.vaults || [];
}

export async function fetchVaultInfo(name: string): Promise<any> {
  const r = await fetch(`/api/vaults/${name}`);
  if (!r.ok) throw new Error(`vault ${name} not found`);
  const d = await r.json();
  return d.vault;
}

export async function fetchPages(vault: string, opts: { type?: string; tag?: string } = {}) {
  const params = new URLSearchParams();
  if (opts.type) params.set("type", opts.type);
  if (opts.tag) params.set("tag", opts.tag);
  const qs = params.toString();
  const r = await fetch(`/api/vaults/${vault}/pages${qs ? "?" + qs : ""}`);
  if (!r.ok) return [];
  const d = await r.json();
  return d.pages || [];
}

export async function fetchPage(vault: string, slug: string) {
  const r = await fetch(`/api/vaults/${vault}/pages/${slug}`);
  if (!r.ok) throw new Error(`page ${slug} not found in vault ${vault}`);
  return r.json();
}

export async function createPage(
  vault: string,
  payload: { slug: string; title: string; content: string; type: string; tags: string[] },
) {
  const r = await fetch(`/api/vaults/${vault}/pages`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!r.ok) throw new Error(`create failed: ${r.status}`);
  return r.json();
}

export async function updatePage(vault: string, slug: string, payload: { content: string }) {
  const r = await fetch(`/api/vaults/${vault}/pages/${slug}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!r.ok) throw new Error(`update failed: ${r.status}`);
  return r.json();
}

export async function deletePage(vault: string, slug: string) {
  const r = await fetch(`/api/vaults/${vault}/pages/${slug}`, { method: "DELETE" });
  if (!r.ok) throw new Error(`delete failed: ${r.status}`);
  return r.json();
}
