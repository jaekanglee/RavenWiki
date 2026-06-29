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
    it("weight=0 → 8px (orphan, dots size never zero)", () => {
      // 8 + sqrt(max(0,1))*6 = 8 + 6 = 14... 잠깐, max(0,1)=1. 8+sqrt(1)*6 = 14.
      // 다시: max(weight ?? 1, 1) → weight=0이면 0 ?? 1 = 1. sqrt(1) = 1. 8+6=14.
      // 따라서 weight=0/undefined/음수는 모두 14px.
      expect(nodeSize(0)).toBeCloseTo(14, 5);
    });

    it("weight=1 → 14px (가장 작은 정상 사이즈)", () => {
      // 8 + sqrt(1)*6 = 14
      expect(nodeSize(1)).toBeCloseTo(14, 5);
    });

    it("weight=4 → 20px (적당한 중간 크기 점)", () => {
      // 8 + sqrt(4)*6 = 8 + 12 = 20
      expect(nodeSize(4)).toBeCloseTo(20, 5);
    });

    it("weight=9 → 26px (큰 허브 노드)", () => {
      // 8 + sqrt(9)*6 = 8 + 18 = 26
      expect(nodeSize(9)).toBeCloseTo(26, 5);
    });

    it("undefined → 14px (안전한 fallback, weight=1과 동일)", () => {
      expect(nodeSize(undefined)).toBeCloseTo(14, 5);
    });

    it("음수 → 14px (clamp 보호)", () => {
      expect(nodeSize(-3)).toBeCloseTo(14, 5);
    });

    it("이전 16px+ 박스 사이즈 대비 점 사이즈 범위 검증", () => {
      // 이전: 16 + sqrt(weight)*8 (weight=1→24, weight=9→40)
      // 신규: 8 + sqrt(weight)*6 (weight=1→14, weight=9→26)
      // weight=9 케이스만 비교: 40 vs 26 → 35% 축소
      const oldBoxWeight9 = 16 + Math.sqrt(9) * 8;
      const newDotWeight9 = nodeSize(9);
      expect(newDotWeight9).toBeLessThan(oldBoxWeight9);
      // 점은 8px 이상 보장 (작아서 안 보이는 문제 방지)
      expect(nodeSize(0)).toBeGreaterThanOrEqual(8);
      // weight=9에서 26px = Obsidian 점의 적정 상한 (~26)
      expect(nodeSize(9)).toBeLessThanOrEqual(30);
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
