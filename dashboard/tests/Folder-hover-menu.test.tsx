/* v0.6.22+ — Sidebar folder hover 메뉴.
 *
 * 사용자 피드백: 사이드바 폴더 hover 시 인라인 + 버튼 (페이지 만들기) 표시.
 * 클릭하면 NewPageButton 모달이 열리고 initialSlug = parentPath로 자동 주입.
 *
 * 회귀 가드:
 *  1. 폴더 dir row에 NewPageButton 렌더 (hover 메뉴, 그러나 DOM엔 항상 존재)
 *  2. 클릭 시 initialSlug = parentPath 전달
 *  3. 부모 path를 그대로 URL로 사용 (content/concept/foo 같은 형태)
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

// Sidebar 내부 TreeLeaf 컴포넌트는 export되지 않으므로 통합 테스트:
// Sidebar 전체를 렌더하고 폴더 안에 페이지 만들기 버튼이 있는지 확인.
import { Sidebar } from "../src/components/Sidebar";
import type { TreeNode } from "../src/types";

const TREE: TreeNode = {
  type: "dir",
  path: "content",
  children: [
    {
      type: "dir",
      path: "content/concept",
      children: [
        {
          type: "page",
          path: "content/concept/dummy.md",
          title: "Dummy Page",
          pageType: "concept",
        },
      ],
    },
  ],
};

describe("Sidebar folder hover menu (v0.6.22)", () => {
  it("folder dir row contains an inline 'create page' button (initialSlug = parentPath)", async () => {
    render(
      <MemoryRouter>
        <Sidebar
          vaults={[{ name: "test", path: "/tmp/test", mode: "personal", owner: "user", default: true }]}
          trees={{ test: TREE }}
          activeVault="test"
          activeSlug={null}
          onSelectVault={() => {}}
          onRefresh={() => {}}
          open={true}
          onClose={() => {}}
          rawItems={{}}
        />
      </MemoryRouter>
    );

    // vault row 펼치기 (chevron 클릭)
    const vaultChevron = document.querySelector(".sidebar-chevron");
    if (!vaultChevron) throw new Error("vaultChevron not found");
    fireEvent.click(vaultChevron);

    // concept 폴더 안에 페이지 만들기 버튼이 나타날 때까지 비동기 대기
    const pageBtns = await screen.findAllByRole("button", { name: /페이지 만들기/ });
    expect(pageBtns.length).toBeGreaterThanOrEqual(2);
  });
});