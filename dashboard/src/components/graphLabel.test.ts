import { describe, it, expect } from "vitest";
import { truncateLabel } from "./GraphCanvas";

// 고정폭 mock: 문자 1개 = 6px (측정 로직만 검증하면 되므로 폰트 렌더는 불필요).
function makeMockCtx(charWidth = 6): CanvasRenderingContext2D {
  return {
    measureText: (text: string) => ({ width: text.length * charWidth }),
  } as unknown as CanvasRenderingContext2D;
}

describe("truncateLabel", () => {
  it("returns the label unchanged when it fits within maxWidth", () => {
    const ctx = makeMockCtx();
    expect(truncateLabel(ctx, "짧은제목", 100)).toBe("짧은제목");
  });

  it("truncates with an ellipsis when the label exceeds maxWidth", () => {
    const ctx = makeMockCtx();
    // "매우매우매우긴제목입니다" = 12 chars * 6px = 72px > maxWidth(30px, 5칸)
    const result = truncateLabel(ctx, "매우매우매우긴제목입니다", 30);
    expect(result.endsWith("…")).toBe(true);
    expect(result.length).toBeLessThan("매우매우매우긴제목입니다".length);
  });

  it("never exceeds maxWidth after truncation", () => {
    const ctx = makeMockCtx();
    const result = truncateLabel(ctx, "abcdefghijklmnopqrstuvwxyz", 50);
    expect(ctx.measureText(result).width).toBeLessThanOrEqual(50);
  });
});
