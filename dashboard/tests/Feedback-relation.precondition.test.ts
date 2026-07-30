/* Theme A 후속 — 피드백·관계 API 클라이언트가 토큰을 전달한다 (momus 라운드 2).
 *
 * 회귀 가드:
 *  1. 피드백 추가/수정/삭제, 관계 추가 요청이 precondition을 실어 보낸다
 *  2. 409 응답이면 서버가 준 문장을 던진다 (상태코드만 던지면 사용자가 원인을 모른다)
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  addRelation,
  deletePageFeedback,
  sendPageFeedback,
  updatePageFeedback,
} from "../src/lib/api";

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
  const spy = vi.fn().mockResolvedValue(
    new Response(JSON.stringify(body), {
      status,
      headers: { "Content-Type": "application/json" },
    }),
  );
  vi.stubGlobal("fetch", spy);
  return spy;
}

beforeEach(() => {
  stubStorage();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("feedback + relation precondition forwarding", () => {
  it("sends the token when adding feedback", async () => {
    const spy = stubFetch(200, { ok: true });
    await sendPageFeedback("v1", "content/hello", {
      feedback: "note",
      actor: "user",
      precondition: "111-22",
    });
    const [, init] = spy.mock.calls[0];
    expect(JSON.parse(init.body as string).precondition).toBe("111-22");
  });

  it("sends the token when editing feedback", async () => {
    const spy = stubFetch(200, { ok: true });
    await updatePageFeedback("v1", "content/hello", 0, {
      feedback: "edited",
      precondition: "111-22",
    });
    const [, init] = spy.mock.calls[0];
    expect(JSON.parse(init.body as string).precondition).toBe("111-22");
  });

  it("sends the token when deleting feedback", async () => {
    const spy = stubFetch(200, { ok: true });
    await deletePageFeedback("v1", "content/hello", 0, "111-22");
    const [url] = spy.mock.calls[0];
    expect(String(url)).toContain("precondition=111-22");
  });

  it("sends the token when adding a relation", async () => {
    const spy = stubFetch(200, { ok: true });
    await addRelation("v1", {
      source_slug: "content/hello",
      target_slug: "content/target",
      relation_type: "related",
      precondition: "111-22",
    });
    const [, init] = spy.mock.calls[0];
    expect(JSON.parse(init.body as string).precondition).toBe("111-22");
  });

  it("surfaces the conflict sentence on 409 for feedback", async () => {
    stubFetch(409, { detail: "페이지가 이 편집을 시작한 뒤 변경됐습니다." });
    await expect(
      sendPageFeedback("v1", "content/hello", { feedback: "note", precondition: "stale" }),
    ).rejects.toThrow(/변경됐습니다/);
  });

  it("surfaces the conflict sentence on 409 for relations", async () => {
    stubFetch(409, { detail: "페이지가 이 편집을 시작한 뒤 변경됐습니다." });
    await expect(
      addRelation("v1", {
        source_slug: "content/hello",
        target_slug: "content/target",
        relation_type: "related",
        precondition: "stale",
      }),
    ).rejects.toThrow(/변경됐습니다/);
  });
});
