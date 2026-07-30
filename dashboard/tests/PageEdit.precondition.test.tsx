/* Theme A.3 — 저장 충돌을 사람에게 보이게 (계획 docs/superpowers/plans/2026-07-29-raven-concept-reinforcement.md §2).
 *
 * 회귀 가드:
 *  1. 편집 저장 시 읽은 시점의 precondition 토큰을 PUT 본문에 실어 보낸다
 *  2. 409(낡은 토큰)면 서버가 준 사람이 읽을 문장을 화면에 띄운다 — 조용한 덮어쓰기 ❌
 *  3. 409가 아닌 실패도 그대로 보고한다 (기존 동작 유지)
 *
 * 이 저장소의 vitest jsdom 환경은 localStorage를 제공하지 않으므로(기존 한계,
 * PageView.local-graph.test.ts도 in-memory shim 사용) storage를 stub한다.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import { InlineMarkdownEditor } from "../src/components/InlineMarkdownEditor";

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

function renderEditor(precondition: string) {
  return render(
    <MemoryRouter>
      <InlineMarkdownEditor
        vault="v1"
        slug="content/hello"
        title="Hello"
        content="base body"
        precondition={precondition}
      />
    </MemoryRouter>,
  );
}

async function enterEditModeAndSave() {
  fireEvent.click(await screen.findByLabelText("편집"));
  const editor = document.querySelector("textarea");
  if (!editor) throw new Error("edit mode textarea not rendered");
  fireEvent.change(editor, { target: { value: "base body + my edit" } });
  const saveButton = (await screen.findByLabelText("저장")) as HTMLButtonElement;
  await waitFor(() => expect(saveButton.disabled).toBe(false));
  fireEvent.click(saveButton);
}

beforeEach(() => {
  stubStorage();
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("InlineMarkdownEditor precondition", () => {
  it("sends the token it was given in the PUT body", async () => {
    const fetchSpy = stubFetch(200, { ok: true, slug: "content/hello" });

    renderEditor("12345-67");
    await enterEditModeAndSave();

    await waitFor(() => expect(fetchSpy).toHaveBeenCalled());
    const put = fetchSpy.mock.calls.find(([, init]) => init?.method === "PUT");
    expect(put).toBeDefined();
    expect(JSON.parse(put![1].body as string).precondition).toBe("12345-67");
  });

  it("shows the server's conflict sentence on 409 instead of a bare status code", async () => {
    stubFetch(409, { detail: "페이지가 이 편집을 시작한 뒤 다른 곳에서 변경됐습니다." });

    renderEditor("stale-token");
    await enterEditModeAndSave();

    expect(await screen.findByText(/다른 곳에서 변경됐습니다/)).toBeTruthy();
  });

  it("still reports a non-conflict failure", async () => {
    stubFetch(400, { detail: "invalid slug" });

    renderEditor("12345-67");
    await enterEditModeAndSave();

    expect(await screen.findByText(/invalid slug/)).toBeTruthy();
  });
});
