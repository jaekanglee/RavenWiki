/* Theme B.3 — 임베딩 열화를 검색 화면에 표시 (계획 §3).
 *
 * 회귀 가드:
 *  1. hybrid-search 응답이 embedding.degraded=true면 경고 배지와 이유를 띄운다
 *  2. degraded=false면 배지를 띄우지 않는다 (정상 상태를 오염시키지 않음)
 *  3. RAG 답변 표면도 같은 열화를 표시한다
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Outlet, Route, Routes } from "react-router-dom";

import { SearchPage } from "../src/routes/SearchPage";

const mocks = vi.hoisted(() => ({ apiFetch: vi.fn() }));

vi.mock("../src/lib/api", () => ({ apiFetch: mocks.apiFetch }));

const DEGRADED = {
  degraded: true,
  model: null,
  reason: "'sentence-transformers' 미설치 — 의미(벡터) 검색이 해시 기반 mock 벡터로 대체됩니다.",
};

function jsonResponse(body: unknown) {
  return {
    ok: true,
    json: async () => body,
  };
}

function routeFetch(embedding: unknown) {
  mocks.apiFetch.mockImplementation((path: string) => {
    if (path.includes("/rag/query")) {
      return Promise.resolve(
        jsonResponse({ ok: true, answer: "AI 답변", citations: [], embedding }),
      );
    }
    return Promise.resolve(
      jsonResponse({
        ok: true,
        results: [{ slug: "content/hello", title: "Hello", type: "concept", score: 1 }],
        embedding,
      }),
    );
  });
}

function OutletShell() {
  return <Outlet context={{ vault: "harumoa" }} />;
}

function renderSearch() {
  return render(
    <MemoryRouter initialEntries={["/search"]}>
      <Routes>
        <Route element={<OutletShell />}>
          <Route path="/search" element={<SearchPage />} />
        </Route>
      </Routes>
    </MemoryRouter>,
  );
}

async function search(term: string) {
  const input = await screen.findByPlaceholderText("검색어나 질문을 입력하세요");
  fireEvent.change(input, { target: { value: term } });
  await waitFor(() => expect(mocks.apiFetch).toHaveBeenCalled());
}

beforeEach(() => {
  mocks.apiFetch.mockReset();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("SearchPage embedding degradation", () => {
  it("warns when the vector half of the ranking is a mock", async () => {
    routeFetch(DEGRADED);
    renderSearch();
    await search("hello");

    expect(await screen.findByText(/의미 검색 열화/)).toBeTruthy();
    expect(await screen.findByText(/sentence-transformers/)).toBeTruthy();
  });

  it("stays quiet when a real embedding model is loaded", async () => {
    routeFetch({ degraded: false, model: "jhgan/ko-sroberta-multitask", reason: "" });
    renderSearch();
    await search("hello");

    await waitFor(() => expect(screen.getByText(/1개 결과/)).toBeTruthy());
    expect(screen.queryByText(/의미 검색 열화/)).toBeNull();
  });

  it("carries the same warning onto the AI answer surface", async () => {
    routeFetch(DEGRADED);
    renderSearch();
    await search("hello");

    fireEvent.click(await screen.findByText(/AI Q&A 답변 받기/));

    expect(await screen.findByText("AI 답변")).toBeTruthy();
    expect(screen.getByText(/의미 검색 열화/)).toBeTruthy();
  });
});
