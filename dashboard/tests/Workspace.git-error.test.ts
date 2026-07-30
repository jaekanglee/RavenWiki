/* git status/diff 실패가 사용자에게 도달한다 — docs/issues/server-전역-에러-envelope-불일치.md (c).
 *
 * 서버가 이 두 경로의 실패를 200 + {ok:false,error}에서 502 + detail로 바꿨는데,
 * 클라이언트가 `!r.ok → null`로 삼켜버리면 사용자는 "워크스페이스를 연결하세요"라는
 * 엉뚱한 안내만 본다. 실패 문장이 호출자까지 전달되는지를 고정한다.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fetchGitDiff, fetchGitStatus, formatApiError } from "../src/lib/api";

function stubStorage() {
  const mem = new Map<string, string>();
  vi.stubGlobal("localStorage", {
    getItem: (k: string) => mem.get(k) ?? null,
    setItem: (k: string, v: string) => void mem.set(k, v),
    removeItem: (k: string) => void mem.delete(k),
    clear: () => mem.clear(),
    key: () => null,
    length: 0,
  });
}

function stubFetch(status: number, body: unknown) {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(
      new Response(JSON.stringify(body), {
        status,
        headers: { "Content-Type": "application/json" },
      }),
    ),
  );
}

beforeEach(() => {
  stubStorage();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("git status/diff failure reaches the caller", () => {
  it("throws the server sentence instead of swallowing it as null", async () => {
    stubFetch(502, { detail: "Failed to get git status: fatal: not a git repository" });
    await expect(fetchGitStatus("v1")).rejects.toThrow(/not a git repository/);
  });

  it("throws the server sentence for diff failures too", async () => {
    stubFetch(502, { detail: "Failed to get git diff: fatal: bad revision" });
    await expect(fetchGitDiff("v1", "readme.txt")).rejects.toThrow(/bad revision/);
  });

  it("still returns null when the vault simply has no workspace", async () => {
    stubFetch(404, { detail: "vault 'v1' not found" });
    await expect(fetchGitStatus("v1")).resolves.toBeNull();
  });

  it("passes a normal status response through untouched", async () => {
    stubFetch(200, { ok: true, has_workspace: true, is_git: true, changes: [] });
    const res = await fetchGitStatus("v1");
    expect(res?.is_git).toBe(true);
  });

  it("formatApiError renders the thrown sentence for the UI", async () => {
    stubFetch(502, { detail: "Failed to get git status: fatal: not a git repository" });
    try {
      await fetchGitStatus("v1");
      throw new Error("expected a rejection");
    } catch (err) {
      expect(formatApiError(err)).toMatch(/not a git repository/);
    }
  });
});
