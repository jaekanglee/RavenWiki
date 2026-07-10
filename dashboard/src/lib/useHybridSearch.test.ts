import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";
import { useHybridSearch } from "./useHybridSearch";

describe("useHybridSearch", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("returns empty results for a blank query without fetching", () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch");
    const { result } = renderHook(() => useHybridSearch("vault1", ""));
    expect(result.current).toEqual([]);
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("debounces then fetches hybrid-search results", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      json: async () => ({
        results: [{ slug: "content/a", title: "A", type: "concept", score: 1, bm25_score: 1, distance: 0, method: "hybrid" }],
      }),
    } as Response);

    const { result, rerender } = renderHook(
      ({ q }) => useHybridSearch("vault1", q, { limit: 8 }),
      { initialProps: { q: "" } }
    );
    act(() => {
      rerender({ q: "hello" });
    });

    // Verify fetch is not called synchronously before debounce elapses
    expect(fetchSpy).not.toHaveBeenCalled();

    await waitFor(() => expect(result.current.length).toBe(1), { timeout: 3000 });

    expect(fetchSpy).toHaveBeenCalledWith(
      expect.stringContaining("/api/vaults/vault1/hybrid-search?query=hello&limit=8"),
      expect.anything()
    );
    expect(result.current[0].slug).toBe("content/a");
  });

  it("filters out excludeSlug from results", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      json: async () => ({
        results: [
          { slug: "content/self", title: "Self", type: "concept", score: 1, bm25_score: 1, distance: 0, method: "hybrid" },
          { slug: "content/other", title: "Other", type: "concept", score: 1, bm25_score: 1, distance: 0, method: "hybrid" },
        ],
      }),
    } as Response);

    const { result, rerender } = renderHook(
      ({ q }) => useHybridSearch("vault1", q, { excludeSlug: "content/self" }),
      { initialProps: { q: "" } }
    );
    act(() => {
      rerender({ q: "term" });
    });

    // Verify fetch is not called synchronously before debounce elapses
    expect(fetchSpy).not.toHaveBeenCalled();

    await waitFor(() => expect(result.current.length).toBe(1), { timeout: 3000 });
    expect(result.current[0].slug).toBe("content/other");
  });
});
