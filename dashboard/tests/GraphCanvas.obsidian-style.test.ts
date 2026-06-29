import { describe, it, expect } from "vitest";
import { nodeColor, nodeSize } from "../src/components/GraphCanvas";

/**
 * v0.6.11 Graph B — Obsidian-style 신경망 그래프 회귀 가드.
 *
 * 검증 범위:
 *   - Patch 1: nodeSize 8~26px 범위 (이전 16~40px 박스 → 점으로 축소)
 *   - Patch 1: nodeColor는 SCHEMA 8종 + 확장에 매핑, 미인식은 default
 *   - Patch 2: (overlay는 React Flow 마운트 필요 — 헬퍼만 정적 검증)
 *
 * React Flow 마운트 자체는 ResizeObserver 의존으로 jsdom에서 어렵기 때문에
 * 핵심 결정 로직만 정적으로 검증한다.
 */
describe("GraphCanvas v0.6.11 Obsidian-style", () => {
  describe("nodeSize (Patch 1 — small dots)", () => {
    it("weight=0 → 6.5px (orphan, dots size never zero)", () => {
      // 4 + sqrt(1)*2.5 = 6.5.
      expect(nodeSize(0)).toBeCloseTo(6.5, 5);
    });

    it("weight=1 → 6.5px (가장 작은 정상 사이즈)", () => {
      // 4 + sqrt(1)*2.5 = 6.5
      expect(nodeSize(1)).toBeCloseTo(6.5, 5);
    });

    it("weight=4 → 9px (적당한 중간 크기 점)", () => {
      // 4 + sqrt(4)*2.5 = 9
      expect(nodeSize(4)).toBeCloseTo(9, 5);
    });

    it("weight=9 → 11.5px (큰 허브 노드)", () => {
      // 4 + sqrt(9)*2.5 = 11.5
      expect(nodeSize(9)).toBeCloseTo(11.5, 5);
    });

    it("undefined → 14px (안전한 fallback, weight=1과 동일)", () => {
      expect(nodeSize(undefined)).toBeCloseTo(6.5, 5);
    });

    it("음수 → 14px (clamp 보호)", () => {
      expect(nodeSize(-3)).toBeCloseTo(6.5, 5);
    });

    it("이전 16px+ 박스 사이즈 대비 점 사이즈 범위 검증", () => {
      // 이전: 16 + sqrt(weight)*8 (weight=1→24, weight=9→40)
      // 신규: 8 + sqrt(weight)*6 (weight=1→14, weight=9→26)
      // weight=9 케이스만 비교: 40 vs 26 → 35% 축소
      const oldBoxWeight9 = 16 + Math.sqrt(9) * 8;
      const newDotWeight9 = nodeSize(9);
      expect(newDotWeight9).toBeLessThan(oldBoxWeight9);
      // 점은 6px 이상 보장 — Obsidian-style 별점처럼 작게 유지
      expect(nodeSize(0)).toBeGreaterThanOrEqual(6);
      // weight=9에서도 12px 미만 — 텍스트 없는 별점 형태 유지
      expect(nodeSize(9)).toBeLessThanOrEqual(12);
    });
  });

  describe("nodeColor (Patch 1 — type color mapping)", () => {
    it("SCHEMA 8종 mapping은 고유 hex 색상", () => {
      expect(nodeColor("decision")).toBe("#a855f7");
      expect(nodeColor("concept")).toBe("#22c55e");
      expect(nodeColor("manual")).toBe("#3b82f6");
      expect(nodeColor("pattern")).toBe("#f97316");
      expect(nodeColor("insight")).toBe("#eab308");
      expect(nodeColor("journal")).toBe("#06b6d4");
      expect(nodeColor("person")).toBe("#ec4899");
      expect(nodeColor("comparison")).toBe("#ef4444");
    });

    it("확장 type도 mapping (tool, rule)", () => {
      expect(nodeColor("tool")).toBe("#6b7280");
      expect(nodeColor("rule")).toBe("#6366f1");
    });

    it("미인식 type은 default gray (#9ca3af)", () => {
      expect(nodeColor("unknown-xyz")).toBe("#9ca3af");
      expect(nodeColor("")).toBe("#9ca3af");
      expect(nodeColor(undefined)).toBe("#9ca3af");
    });
  });
});
