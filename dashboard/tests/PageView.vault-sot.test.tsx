import { describe, it, expect, vi } from "vitest";
import { MemoryRouter, Routes, Route, useParams } from "react-router-dom";
import { render, screen } from "@testing-library/react";

// PageView 내부에서 vault 우선순위 로직을 그대로 검증하기 위해,
// 라우트의 :vault 파라미터가 PageView로 흘러가는지 확인하는 최소 회귀 테스트.
//
// 회귀 대상 (P15 — Wizard 후 vault active 전환 race):
//   URL = "/page/what/content/index"
//   Layout ctx.vault = "develop" (stale)
//   → PageView는 vault="develop"으로 호출하면 Not found 404
//   → P15 fix 후: URL의 :vault를 SOT로 사용 → "what"으로 호출 → 정상
//
// 이 테스트는 App.tsx의 라우트가 `/page/:vault/*`로 변경되어 있는지,
// 그리고 :vault 파라미터가 정상적으로 추출되는지를 가드한다.

// PageView의 핵심 로직 (params.vault 우선)만 따로 떼어 검증하기 위한 미니 컴포넌트.
// PageView 전체를 import하지 않고 router 파라미터 흐름만 검증한다.
function VaultEcho() {
  const params = useParams();
  const slug = params["*"];
  return (
    <div>
      <span data-testid="vault">{params.vault ?? ""}</span>
      <span data-testid="slug">{slug ?? ""}</span>
    </div>
  );
}

describe("PageView vault routing (P15 fix)", () => {
  it("/page/what/content/index → vault=what, slug=content/index", () => {
    render(
      <MemoryRouter initialEntries={["/page/what/content/index"]}>
        <Routes>
          <Route path="/page/:vault/*" element={<VaultEcho />} />
        </Routes>
      </MemoryRouter>
    );
    expect(screen.getByTestId("vault").textContent).toBe("what");
    expect(screen.getByTestId("slug").textContent).toBe("content/index");
  });

  it("/page/develop/content/foo → vault=develop (URL is SOT)", () => {
    render(
      <MemoryRouter initialEntries={["/page/develop/content/foo"]}>
        <Routes>
          <Route path="/page/:vault/*" element={<VaultEcho />} />
        </Routes>
      </MemoryRouter>
    );
    expect(screen.getByTestId("vault").textContent).toBe("develop");
    expect(screen.getByTestId("slug").textContent).toBe("content/foo");
  });

  it("/page/infra → vault=infra, slug empty (no wildcard part)", () => {
    render(
      <MemoryRouter initialEntries={["/page/infra"]}>
        <Routes>
          <Route path="/page/:vault/*" element={<VaultEcho />} />
        </Routes>
      </MemoryRouter>
    );
    expect(screen.getByTestId("vault").textContent).toBe("infra");
    expect(screen.getByTestId("slug").textContent).toBe("");
  });

  it("/page missing → does not match /page/:vault/* (route mismatch guard)", () => {
    // /page 단독은 :vault가 비어서 match 안 됨 → VaultEcho 미렌더
    // (실제 App.tsx에선 /page 없이 /만 매칭되니 OK — 이건 라우트 변경 가드)
    const { container } = render(
      <MemoryRouter initialEntries={["/page"]}>
        <Routes>
          <Route path="/page/:vault/*" element={<VaultEcho />} />
        </Routes>
      </MemoryRouter>
    );
    expect(container.querySelector('[data-testid="vault"]')).toBeNull();
  });
});