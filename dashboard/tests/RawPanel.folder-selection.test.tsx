import { describe, it, expect, vi, beforeEach } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { RawPanel } from "../src/routes/RawPanel";
import * as api from "../src/lib/api";
import type { RawItem } from "../src/lib/api";

vi.mock("../src/lib/api", () => ({
  fetchRawList: vi.fn(),
  fetchRawContent: vi.fn(),
  writeRaw: vi.fn(),
  deleteRaw: vi.fn(),
}));

const rawItems: RawItem[] = [
  { path: "raw/agent-policy", name: "agent-policy", type: "dir" as const, kind: "raw" },
  {
    path: "raw/agent-policy/README.md",
    name: "README.md",
    type: "file" as const,
    kind: "raw",
    size: 12,
  },
];

describe("RawPanel folder selection", () => {
  beforeEach(() => {
    vi.mocked(api.fetchRawList).mockResolvedValue({
      ok: true,
      vault: "raven-dev",
      root: "raw",
      items: rawItems,
    });
    vi.mocked(api.fetchRawContent).mockRejectedValue(new Error("directories are not files"));
  });

  it("opens a folder in the tree without requesting it as file content", async () => {
    render(
      <MemoryRouter initialEntries={["/raw/raven-dev"]}>
        <Routes>
          <Route path="/raw/:vault/*" element={<RawPanel />} />
        </Routes>
      </MemoryRouter>
    );

    const folder = await screen.findByRole("button", { name: /agent-policy/ });
    fireEvent.click(folder);

    await waitFor(() => {
      expect(api.fetchRawContent).not.toHaveBeenCalled();
    });
  });

  it("returns a direct folder URL to the raw tree without requesting file content", async () => {
    render(
      <MemoryRouter initialEntries={["/raw/raven-dev/agent-policy"]}>
        <Routes>
          <Route path="/raw/:vault/*" element={<RawPanel />} />
        </Routes>
      </MemoryRouter>
    );

    await screen.findByRole("button", { name: /agent-policy/ });
    await waitFor(() => {
      expect(api.fetchRawContent).not.toHaveBeenCalled();
    });
  });
});
