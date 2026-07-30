/* P0-2 회귀 가드 — 활성 vault가 있으면 기록이 최우선 행동이다.
 *  1. 활성 vault가 있으면 "새 페이지"가 primary이고 "새 vault"보다 앞에 온다
 *  2. Cmd/Ctrl+N이 인라인 생성 폼을 연다
 *  3. 활성 vault가 없으면 단축키는 폼을 열지 않는다
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

let activeVaultName: string | null = "v1";

vi.mock("../src/lib/api", async (importOriginal) => {
  const actual = (await importOriginal()) as Record<string, unknown>;
  return {
    ...actual,
    fetchVaults: vi.fn(async () => [
      { name: "v1", path: "/tmp/v1", mode: "personal", owner: "user", default: true },
    ]),
    fetchPages: vi.fn(async () => []),
    getActiveVault: vi.fn(() => activeVaultName ?? ""),
    setActiveVault: vi.fn(),
  };
});

import { HomePage } from "../src/routes/HomePage";

function stubStatsFetch() {
  const spy = vi.fn().mockResolvedValue(
    new Response(JSON.stringify({ pages: 3, broken_links: 0, size_bytes: 1024, logs: 0 }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }),
  );
  vi.stubGlobal("fetch", spy);
  return spy;
}

function renderHome() {
  return render(
    <MemoryRouter>
      <HomePage />
    </MemoryRouter>,
  );
}

async function newPageTrigger() {
  return (await screen.findByRole("button", { name: /새 페이지/ })) as HTMLButtonElement;
}

beforeEach(() => {
  activeVaultName = "v1";
  stubStatsFetch();
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("HomePage 즉시 기록", () => {
  it("활성 vault가 있으면 새 페이지가 primary이고 새 vault보다 앞에 온다", async () => {
    renderHome();

    const newPage = await newPageTrigger();
    const newVault = await screen.findByRole("link", { name: /새 vault/ });

    expect(newPage.dataset.primary).toBe("true");
    expect((newVault as HTMLElement).dataset.primary).not.toBe("true");

    const newPageIsBefore = Boolean(
      newPage.compareDocumentPosition(newVault) & Node.DOCUMENT_POSITION_FOLLOWING,
    );
    expect(newPageIsBefore).toBe(true);
  });

  it("Cmd/Ctrl+N으로 인라인 생성 폼을 연다", async () => {
    renderHome();
    await waitFor(async () => {
      expect((await newPageTrigger()).dataset.primary).toBe("true");
    });

    fireEvent.keyDown(document, { key: "n", metaKey: true });

    const closeForm = await screen.findByRole("button", { name: /폼 닫기/ });
    expect(closeForm.getAttribute("aria-pressed")).toBe("true");
  });

  it("활성 vault가 없으면 단축키가 폼을 열지 않는다", async () => {
    activeVaultName = null;
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response("{}", { status: 500 })),
    );

    const { container } = render(
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>,
    );
    await waitFor(() => expect(container.textContent).toContain("빠른 액션"));

    fireEvent.keyDown(document, { key: "n", ctrlKey: true });

    await waitFor(() => {
      expect(screen.queryByRole("button", { name: /폼 닫기/ })).toBeNull();
    });
  });
});
