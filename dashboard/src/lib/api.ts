/**
 * Active vault store (simple, no zustand needed).
 *
 * Vault identity is stored in localStorage so refresh keeps the choice.
 * Components read this through `useActiveVault()` and refresh when needed.
 */
import type { TreeNode } from "../types";

export const ACTIVE_VAULT_KEY = "raven:active_vault";

export function getActiveVault(): string {
  return localStorage.getItem(ACTIVE_VAULT_KEY) || "";
}

export function setActiveVault(name: string): void {
  localStorage.setItem(ACTIVE_VAULT_KEY, name);
}

// ─── debug logger (Raven-Debug v0.6.10+) ─────────────────────
// fetch throw / React error 등을 tmp/dashboard.log에 자동 기록.
// 브라우저 console에서 못 봐도 사용자가 cat으로 직접 확인 가능.
let _logInited = false;
function _ensureLogInited() {
  if (_logInited || typeof window === "undefined") return;
  _logInited = true;
  // unhandled error / promise rejection 자동 캡처
  window.addEventListener("error", (e) => {
    _writeLog(
      `[error] ${e.message}\n  file=${e.filename}:${e.lineno}\n  stack=${(e.error && e.error.stack) || ""}`
    );
  });
  window.addEventListener("unhandledrejection", (e) => {
    const r = e.reason;
    _writeLog(
      `[unhandledrejection] ${r && r.message ? r.message : String(r)}\n  stack=${r && r.stack ? r.stack : ""}`
    );
  });
}

function _writeLog(line: string) {
  if (typeof window === "undefined") return;
  try {
    const key = "raven:debug:log";
    const arr = JSON.parse(localStorage.getItem(key) || "[]");
    arr.push({ t: new Date().toISOString(), line });
    // 최대 200줄만 유지
    if (arr.length > 200) arr.splice(0, arr.length - 200);
    localStorage.setItem(key, JSON.stringify(arr));
  } catch {
    // localStorage 실패해도 silent
  }
}

export function debugLog(line: string) {
  _ensureLogInited();
  // eslint-disable-next-line no-console
  console.log("[Raven-Debug]", line);
  _writeLog(line);
}

export function fetchDebugLog(): string[] {
  if (typeof window === "undefined") return [];
  try {
    const arr = JSON.parse(localStorage.getItem("raven:debug:log") || "[]");
    return arr.map((e: { t: string; line: string }) => `${e.t} ${e.line}`);
  } catch {
    return [];
  }
}

export function clearDebugLog() {
  if (typeof window === "undefined") return;
  localStorage.removeItem("raven:debug:log");
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

export async function fetchTree(vault: string): Promise<TreeNode | null> {
  const r = await fetch(`/api/vaults/${vault}/tree`);
  if (!r.ok) return null;
  const d = await r.json();
  return d.tree || null;
}

export async function createFolder(
  vault: string,
  payload: { path: string },
): Promise<{ ok: boolean; path: string; existed: boolean }> {
  const r = await fetch(`/api/vaults/${vault}/folders`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!r.ok) {
    const detail = (await r.json().catch(() => ({}))).detail || `create folder failed: ${r.status}`;
    throw new Error(detail);
  }
  return r.json();
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

// ────────────────────────── log (v0.5.0+) ──────────────────────────

export interface LogEntry {
  date: string;
  action: string;
  subject: string;
  details: string[];
}

export interface LogStatus {
  vault: string;
  log_path: string;
  exists: boolean;
  total_entries: number;
  last_entry: LogEntry | null;
  needs_rotate: boolean;
  rotate_threshold: number;
}

export async function fetchLog(
  vault: string,
  opts: { tail?: number; action?: string } = {},
): Promise<{ total: number; shown: number; entries: LogEntry[] }> {
  const params = new URLSearchParams();
  if (opts.tail !== undefined) params.set("tail", String(opts.tail));
  if (opts.action) params.set("action", opts.action);
  const qs = params.toString();
  const r = await fetch(`/api/vaults/${vault}/log${qs ? "?" + qs : ""}`);
  if (!r.ok) return { total: 0, shown: 0, entries: [] };
  const d = await r.json();
  return { total: d.total, shown: d.shown, entries: d.entries || [] };
}

export async function fetchLogStatus(vault: string): Promise<LogStatus | null> {
  const r = await fetch(`/api/vaults/${vault}/log/status`);
  if (!r.ok) return null;
  return r.json();
}

export async function appendLog(
  vault: string,
  payload: { action: string; subject: string; files?: string[]; note?: string },
) {
  const r = await fetch(`/api/vaults/${vault}/log`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!r.ok) throw new Error(`log append failed: ${r.status}`);
  return r.json();
}

export async function rotateLog(vault: string, opts: { year?: number; force?: boolean } = {}) {
  const params = new URLSearchParams();
  if (opts.year !== undefined) params.set("year", String(opts.year));
  if (opts.force) params.set("force", "true");
  const qs = params.toString();
  const r = await fetch(`/api/vaults/${vault}/log/rotate${qs ? "?" + qs : ""}`, { method: "POST" });
  if (!r.ok) throw new Error(`log rotate failed: ${r.status}`);
  return r.json();
}

// ────────────────────────── lint (v0.5.1+) ──────────────────────────

export type LintSeverity = "critical" | "warning" | "info";

export interface LintIssue {
  id: string; // "#1" - "#12"
  severity: LintSeverity;
  slug: string;
  message: string;
  target?: string;
}

export interface LintResult {
  ok: boolean;
  vault: string;
  counts: Record<LintSeverity | "total", number>;
  by_check: Record<string, number>;
  issues: LintIssue[];
}

export interface LintSummary {
  ok: boolean;
  vault: string;
  counts: Record<LintSeverity | "total", number>;
  by_check: Record<string, number>;
}

export async function fetchLint(
  vault: string,
  opts: { check?: string; severity?: LintSeverity; write_log?: boolean } = {},
): Promise<LintResult | null> {
  const params = new URLSearchParams();
  if (opts.check) params.set("check", opts.check);
  if (opts.severity) params.set("severity", opts.severity);
  if (opts.write_log) params.set("write_log", "true");
  const qs = params.toString();
  const r = await fetch(`/api/vaults/${vault}/lint${qs ? "?" + qs : ""}`);
  if (!r.ok) return null;
  return r.json();
}

export async function fetchLintSummary(vault: string): Promise<LintSummary | null> {
  const r = await fetch(`/api/vaults/${vault}/lint/summary`);
  if (!r.ok) return null;
  return r.json();
}

// ────────────────────────── digest (v0.5.6, M5 F5) ──────────────────────────

export interface DigestTodayEntry {
  date: string;
  action: string;
  subject: string;
  details: string[];
}

export interface DigestDayBucket {
  date: string;
  count: number;
  by_action: Record<string, number>;
}

export interface DigestTopIssue {
  id: string;
  slug: string;
  message: string;
}

export interface DigestLint {
  ok: boolean;
  counts: Record<LintSeverity | "total", number>;
  by_check: Record<string, number>;
  top_issues: Record<LintSeverity, DigestTopIssue[]>;
}

export interface DigestRecentPage {
  slug: string;
  title: string;
  type: string;
  updated: string;
}

export interface DigestStats {
  total_pages: number;
  types: Record<string, number>;
  recent_pages: DigestRecentPage[];
  broken_links: number;
  missing_links: number;
}

export interface DigestPayload {
  ok: boolean;
  vault: string;
  generated_at: string;
  today: DigestTodayEntry[];
  this_week: DigestDayBucket[];
  lint: DigestLint;
  log_recent: DigestTodayEntry[];
  stats: DigestStats;
}

export async function fetchDigest(vault: string, days: number = 7): Promise<DigestPayload | null> {
  const r = await fetch(`/api/vaults/${vault}/digest?days=${days}`);
  if (!r.ok) return null;
  return r.json();
}
