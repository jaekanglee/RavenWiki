import { describe, expect, it, beforeEach, afterEach, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Outlet, Route, Routes } from "react-router-dom";
import { GardenPage } from "../src/routes/GardenPage";

const mocks = vi.hoisted(() => ({
  fetchGarden: vi.fn(),
  fetchPages: vi.fn(),
  fetchPage: vi.fn(),
  updatePage: vi.fn(),
  deletePage: vi.fn(),
}));

vi.mock("../src/lib/api", () => ({
  fetchGarden: mocks.fetchGarden,
  fetchPages: mocks.fetchPages,
  fetchPage: mocks.fetchPage,
  updatePage: mocks.updatePage,
  deletePage: mocks.deletePage,
}));

function OutletShell() {
  return <Outlet context={{ vault: "harumoa" }} />;
}

describe("GardenPage link candidates", () => {
  beforeEach(() => {
    mocks.fetchGarden.mockReset();
    mocks.fetchPages.mockReset();
    mocks.fetchPage.mockReset();
    mocks.updatePage.mockReset();
    mocks.deletePage.mockReset();

    vi.stubGlobal("matchMedia", (query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }));
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders object-shaped link candidates returned by the garden API", async () => {
    mocks.fetchGarden.mockResolvedValue({
      ok: true,
      vault: "harumoa",
      stale: [],
      orphan: [
        {
          slug: "content/index",
          title: "harumoa",
          type: "concept",
          link_candidates: [
            {
              slug: "content/decisions/vault-policy",
              title: "vault 정책 일관성 fix",
              reason: "본문 내 'index' 키워드 포함",
              score: 5,
            },
          ],
        },
      ],
    });
    mocks.fetchPages.mockResolvedValue([
      { slug: "content/index", title: "harumoa" },
      { slug: "content/decisions/vault-policy", title: "vault 정책 일관성 fix" },
    ]);

    render(
      <MemoryRouter initialEntries={["/garden"]}>
        <Routes>
          <Route element={<OutletShell />}>
            <Route path="/garden" element={<GardenPage />} />
          </Route>
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("vault 정책 일관성 fix")).toBeTruthy();
    });
    expect(screen.getByText("harumoa")).toBeTruthy();
  });
});
