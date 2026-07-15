import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Outlet, Route, Routes } from "react-router-dom";
import { GraphPage } from "../src/routes/GraphPage";

const mockGraphCanvas = vi.fn();

vi.mock("../src/components/GraphCanvas", async () => {
  const actual = await vi.importActual<typeof import("../src/components/GraphCanvas")>(
    "../src/components/GraphCanvas"
  );
  return {
    ...actual,
    GraphCanvas: (props: any) => {
      mockGraphCanvas(props);
      return (
      <div data-testid="graph-canvas">
        {props.nodes.map((node: any) => (
          <button
            key={node.id}
            type="button"
            data-testid={`graph-node-${node.id}`}
            onClick={() => props.onNodeClick(node.id)}
          >
            {node.title}
          </button>
        ))}
      </div>
      );
    },
  };
});

vi.mock("../src/components/FullscreenGraphModal", () => ({
  FullscreenGraphModal: () => <div data-testid="fullscreen-graph-modal" />,
}));

function OutletShell() {
  return <Outlet context={{ vault: "detail-vault" }} />;
}

describe("GraphPage detail panel", () => {
  it("renders compact tabbed node detail and switches relation lists", async () => {
    mockGraphCanvas.mockReset();
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          nodes: [
            {
              id: "content/a",
              slug: "content/a",
              title: "A",
              type: "concept",
              weight: 2,
              collection: "content",
              status: "current",
              aliases: ["Alpha", "First"],
            },
            { id: "content/b", slug: "content/b", title: "B", type: "tool", weight: 1 },
            { id: "content/c", slug: "content/c", title: "C", type: "project", weight: 1 },
          ],
          edges: [
            { source: "content/b", target: "content/a" },
            { source: "content/a", target: "content/c" },
          ],
        }),
      })
    );

    render(
      <MemoryRouter initialEntries={["/graph"]}>
        <Routes>
          <Route element={<OutletShell />}>
            <Route path="/graph" element={<GraphPage />} />
          </Route>
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.queryByTestId("graph-node-content/a")).not.toBeNull();
    });

    fireEvent.click(screen.getByTestId("graph-node-content/a"));

    expect(screen.queryByRole("complementary", { name: "선택 문서 상세" })).not.toBeNull();
    expect(screen.getAllByText("A").length).toBeGreaterThanOrEqual(1);
    expect(screen.queryByText("content/a")).not.toBeNull();
    expect(screen.queryByText("content")).not.toBeNull();
    expect(screen.queryByText("current")).not.toBeNull();
    expect(screen.queryByText("Alpha")).not.toBeNull();
    expect(screen.queryByRole("button", { name: /포커스/ })).not.toBeNull();
    expect(screen.queryByRole("button", { name: /열기/ })).not.toBeNull();
    expect(mockGraphCanvas.mock.calls.at(-1)?.[0].focusNodeId).toBe("content/a");

    const inboundTab = screen.getByRole("button", { name: /참조됨\s*1/ });
    const outboundTab = screen.getByRole("button", { name: /참조함\s*1/ });
    const neighborsTab = screen.getByRole("button", { name: /관련\s*2/ });
    expect(inboundTab.className).toContain("active");
    expect(screen.getAllByRole("button", { name: /B/ }).length).toBeGreaterThanOrEqual(1);

    fireEvent.click(outboundTab);
    expect(outboundTab.className).toContain("active");
    expect(screen.getAllByRole("button", { name: /C/ }).length).toBeGreaterThanOrEqual(1);

    fireEvent.click(neighborsTab);
    expect(neighborsTab.className).toContain("active");
    expect(screen.getAllByRole("button", { name: /B/ }).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByRole("button", { name: /C/ }).length).toBeGreaterThanOrEqual(1);
  });
});
