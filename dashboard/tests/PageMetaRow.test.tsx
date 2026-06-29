/* v0.6.21+ — Index 마커 + type chip 메타 row.
 *
 * 사용자 의도 재해석: "Type ADR 자동 표시 + 📑 Index 자동 표시"는 페이지
 * 메타 row 강화로 통합. slug가 content/index일 때 📑 마크 표시.
 *
 * 회귀 가드:
 *  1. type이 chip-strong으로 표시 (기존 동작 유지)
 *  2. slug가 'content/index' 또는 'index'일 때 📑 chip 추가
 *  3. 다른 slug일 때 📑 마크 없음
 *  4. tags 표시 유지
 *  5. updated 표시 유지
 */
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { PageMetaRow } from "../src/components/PageMetaRow";

function wrap(node: React.ReactNode) {
  return render(<MemoryRouter>{node}</MemoryRouter>);
}

describe("PageMetaRow contract (v0.6.21)", () => {
  it("renders type as a chip", () => {
    wrap(
      <PageMetaRow
        type="concept"
        slug="content/some-page"
        tags=""
        updated="2026-06-29"
      />
    );
    expect(screen.getByText("concept")).toBeTruthy();
  });

  it("renders 📑 Index marker when slug is content/index", () => {
    wrap(
      <PageMetaRow
        type="concept"
        slug="content/index"
        tags=""
        updated="2026-06-29"
      />
    );
    expect(screen.getByText(/📑/)).toBeTruthy();
    expect(screen.getByText(/Index/)).toBeTruthy();
  });

  it("renders 📑 Index marker when slug is just 'index' (prefix tolerance)", () => {
    wrap(
      <PageMetaRow
        type="concept"
        slug="index"
        tags=""
        updated="2026-06-29"
      />
    );
    expect(screen.getByText(/📑/)).toBeTruthy();
  });

  it("does NOT render Index marker for non-index pages", () => {
    wrap(
      <PageMetaRow
        type="concept"
        slug="content/some-other-page"
        tags=""
        updated="2026-06-29"
      />
    );
    expect(screen.queryByText(/📑/)).toBeNull();
  });

  it("renders tags as #tag pills", () => {
    wrap(
      <PageMetaRow
        type="concept"
        slug="content/x"
        tags="ai, llm"
        updated="2026-06-29"
      />
    );
    expect(screen.getByText("#ai")).toBeTruthy();
    expect(screen.getByText("#llm")).toBeTruthy();
  });

  it("renders updated date", () => {
    wrap(
      <PageMetaRow
        type="concept"
        slug="content/x"
        tags=""
        updated="2026-06-29"
      />
    );
    expect(screen.getByText(/2026-06-29/)).toBeTruthy();
  });
});