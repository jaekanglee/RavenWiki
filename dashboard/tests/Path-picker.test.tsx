/* v0.6.19+ — Path picker UX for new page modal.
 *
 * 기존: 저장 위치를 직접 타이핑 (content/my-note) → 오타 위험.
 * 개선: 모달 안에 vault 트리 렌더, 클릭 시 slug prefix 주입.
 *        기존 인풋은 "최종 파일명" 담당으로 단순화.
 *
 * 회귀 가드:
 *  1. 모달 열면 fetchTree 호출 (트리 데이터 있음)
 *  2. 트리에서 폴더 클릭 → slug가 "content/선택폴더/" prefix로 갱신
 *  3. 폴더 클릭 후 파일명 입력 가능 (slug 끝이 파일명 자리)
 *  4. 트리 fetch 실패해도 인풋 직접 입력은 가능 (graceful)
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { NewPageButton } from "../src/components/NewPageButton";
import * as api from "../src/lib/api";

// fetchTree mock
const SAMPLE_TREE = {
  type: "dir" as const,
  path: "content",
  children: [
    {
      type: "dir" as const,
      path: "content/concept",
      children: [
        {
          type: "page" as const,
          path: "content/concept/existing",
          slug: "content/concept/existing",
          title: "기존 페이지",
        },
      ],
    },
    {
      type: "dir" as const,
      path: "content/empty",
      children: [],
    },
    {
      type: "page" as const,
      path: "content/index",
      slug: "content/index",
      title: "Index",
    },
  ],
};

beforeEach(() => {
  vi.spyOn(api, "fetchTree").mockResolvedValue(SAMPLE_TREE);
});

function wrap(node: React.ReactNode) {
  return render(<MemoryRouter>{node}</MemoryRouter>);
}

describe("NewPageButton — path picker UX (v0.6.19)", () => {
  it("Modal renders tree picker section after opening", async () => {
    wrap(<NewPageButton vault="test" variant="icon" />);
    fireEvent.click(screen.getByRole("button", { name: /페이지 만들기/ }));

    // data-path attribute로 트리 노드 찾기 (path-based assertion)
    await waitFor(() => {
      expect(document.querySelector('[data-path="content/concept"]')).toBeTruthy();
    });
    expect(document.querySelector('[data-path="content/empty"]')).toBeTruthy();
    expect(document.querySelector('[data-path="content"]')).toBeTruthy();
  });

  it("Clicking a folder in the picker sets slug prefix", async () => {
    wrap(<NewPageButton vault="test" variant="icon" />);
    fireEvent.click(screen.getByRole("button", { name: /페이지 만들기/ }));

    await waitFor(() => {
      expect(document.querySelector('[data-path="content/concept"]')).toBeTruthy();
    });

    // concept 폴더 클릭
    const conceptBtn = document.querySelector(
      '[data-path="content/concept"]'
    ) as HTMLButtonElement;
    fireEvent.click(conceptBtn);

    // slug input 값이 content/concept/ prefix로 시작해야 함
    const slugInput = screen.getByPlaceholderText(/my-concept/) as HTMLInputElement;
    expect(slugInput.value.startsWith("content/concept/")).toBe(true);
  });

  it("Slug input remains editable for the file name part (direct typing fallback)", async () => {
    // fetchTree 실패해도 slug 인풋은 정상 동작
    vi.spyOn(api, "fetchTree").mockRejectedValueOnce(new Error("net err"));
    wrap(<NewPageButton vault="test" variant="icon" />);
    fireEvent.click(screen.getByRole("button", { name: /페이지 만들기/ }));

    // 인풋 직접 타이핑 가능
    const slugInput = screen.getByPlaceholderText(/my-concept/) as HTMLInputElement;
    fireEvent.change(slugInput, { target: { value: "content/manual-typing" } });
    expect(slugInput.value).toBe("content/manual-typing");
  });
});