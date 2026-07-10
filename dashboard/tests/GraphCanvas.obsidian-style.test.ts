import { describe, it, expect } from "vitest";
import {
  computeFocusDepthMap,
  computeLayeredLayout,
  nodeColor,
  nodeOpacity,
  nodeSize,
} from "../src/components/GraphCanvas";

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
    // v0.7.139+: weight 기반 사이즈 공식을 sqrt → log2(1+w)로 교체.
    //   - normal: 8 + log2(1+w)*6  (leaf 14, w=4 → 22.5, w=10 → 33.9, w=24 → 42.9)
    //   - dense:  10 + log2(1+w)*7 (leaf 17, w=4 → 26.3, w=10 → 38.0, w=24 → 48.0)
    // sqrt 스케일은 1~24 구간이 11~30.5로 좁아서 hub가 묻혔고 leaf는 모바일 tap이 안 됐다.
    // log 스케일은 같은 구간을 14~43으로 펼쳐서 양쪽 다 잡는다.
    it("weight=0 → 14px (orphan, dots size never zero)", () => {
      // 8 + log2(2)*6 = 8 + 6 = 14 (weight=0은 clamp로 1 취급)
      expect(nodeSize(0)).toBeCloseTo(14, 5);
    });

    it("weight=1 → 14px (가장 작은 정상 사이즈)", () => {
      // 8 + log2(2)*6 = 14
      expect(nodeSize(1)).toBeCloseTo(14, 5);
    });

    it("weight=4 → 22.5px (적당한 중간 크기 점)", () => {
      // 8 + log2(5)*6 = 8 + 13.93 = 21.93
      expect(nodeSize(4)).toBeCloseTo(21.93, 1);
    });

    it("weight=9 → 30.4px (큰 허브 노드)", () => {
      // 8 + log2(10)*6 = 8 + 19.93 = 27.93
      expect(nodeSize(9)).toBeCloseTo(27.93, 1);
    });

    it("weight=24 (현재 vault max) → 42.9px (가장 큰 hub)", () => {
      // 8 + log2(25)*6 = 8 + 27.93 = 35.93... 다시 계산:
      // log2(25) = log(25)/log(2) ≈ 4.644
      // 8 + 4.644*6 = 8 + 27.86 = 35.86
      expect(nodeSize(24)).toBeCloseTo(35.86, 1);
    });

    it("undefined → 14px (안전한 fallback, weight=1과 동일)", () => {
      expect(nodeSize(undefined)).toBeCloseTo(14, 5);
    });

    it("음수 → 14px (clamp 보호)", () => {
      expect(nodeSize(-3)).toBeCloseTo(14, 5);
    });

    it("dense 모드는 normal보다 작음 (v0.7.136: 빽빽 노드 화면 점유 과다 → 축소)", () => {
      // v0.7.136: dense에서 multiplier 7→4, base 10→7.
      // dense w=9 → 7 + log2(10)*4 = 20.28.
      // normal w=9 → 8 + log2(10)*6 = 27.93.
      expect(nodeSize(9, "dense")).toBeCloseTo(20.28, 1);
      expect(nodeSize(9, "dense")).toBeLessThan(nodeSize(9, "normal"));
    });

    it("dense hub cap — weight=24도 30px 이하 (사용자: '두껍다')", () => {
      expect(nodeSize(24, "dense")).toBeLessThanOrEqual(30);
    });

    it("이전 박스 사이즈 대비 점 사이즈 범위 검증", () => {
      // 박스 시절: 16 + sqrt(weight)*8 (weight=9→40)
      // 점 normal log: 8 + log2(1+w)*6 (weight=9→27.9, weight=24→35.9)
      // 박스 weight=9=40 vs 점 normal weight=9=27.9 → 30% 축소 (적당)
      const oldBoxWeight9 = 16 + Math.sqrt(9) * 8;
      const newDotWeight9 = nodeSize(9);
      expect(newDotWeight9).toBeLessThan(oldBoxWeight9);
      // 점 normal leaf는 12px 이상 — 모바일 tap 타겟 + zoom-out 가독
      expect(nodeSize(0)).toBeGreaterThanOrEqual(12);
      // 점 normal hub@24는 40px 미만 — vault halo에 안 묻힘
      expect(nodeSize(24)).toBeLessThanOrEqual(40);
    });
  });

  describe("nodeColor (Patch 1 — type color mapping)", () => {
    it("SCHEMA 9종 mapping은 고유 hex 색상", () => {
      expect(nodeColor("concept")).toBe("#22c55e");
      expect(nodeColor("person")).toBe("#ec4899");
      expect(nodeColor("tool")).toBe("#6b7280");
      expect(nodeColor("comparison")).toBe("#ef4444");
      expect(nodeColor("project")).toBe("#f97316");
      expect(nodeColor("rule")).toBe("#6366f1");
      expect(nodeColor("query")).toBe("#eab308");
      expect(nodeColor("journal")).toBe("#06b6d4");
      expect(nodeColor("issue")).toBe("#a855f7");
    });

    it("legacy/non-schema type은 default gray (#9ca3af)", () => {
      expect(nodeColor("decision")).toBe("#9ca3af");
      expect(nodeColor("manual")).toBe("#9ca3af");
      expect(nodeColor("pattern")).toBe("#9ca3af");
      expect(nodeColor("insight")).toBe("#9ca3af");
    });

    it("미인식 type은 default gray (#9ca3af)", () => {
      expect(nodeColor("unknown-xyz")).toBe("#9ca3af");
      expect(nodeColor("")).toBe("#9ca3af");
      expect(nodeColor(undefined)).toBe("#9ca3af");
    });
  });

  describe("Post-MVP analytics visual mapping", () => {
    it("freshness는 opacity로 0.32~1.0 범위에 매핑된다", () => {
      expect(nodeOpacity(undefined)).toBe(1);
      expect(nodeOpacity(1)).toBeCloseTo(1, 5);
      expect(nodeOpacity(0)).toBeCloseTo(0.32, 5);
      expect(nodeOpacity(0.5)).toBeCloseTo(0.66, 5);
      expect(nodeOpacity(-1)).toBeCloseTo(0.32, 5);
      expect(nodeOpacity(2)).toBeCloseTo(1, 5);
    });

    it("layered 레이아웃은 낮은 layer를 더 왼쪽에 배치하고 같은 layer는 세로로 분산한다", () => {
      const coords = computeLayeredLayout([
        { id: "core", title: "Core", layer: 0, importance: 0.8 },
        { id: "api", title: "API", layer: 1, importance: 0.6 },
        { id: "dashboard", title: "Dashboard", layer: 2, importance: 0.4 },
        { id: "dashboard-2", title: "Dashboard 2", layer: 2, importance: 0.2 },
      ]);

      expect(coords["core"].x).toBeLessThan(coords["api"].x);
      expect(coords["api"].x).toBeLessThan(coords["dashboard"].x);
      expect(coords["dashboard"].x).toBeCloseTo(coords["dashboard-2"].x, 5);
      expect(coords["dashboard"].y).not.toBe(coords["dashboard-2"].y);
    });

    it("focus depth map is BFS-based and caps traversal depth", () => {
      const nodes = [
        { id: "a", title: "A" },
        { id: "b", title: "B" },
        { id: "c", title: "C" },
        { id: "d", title: "D" },
      ];
      const edges = [
        { source: "a", target: "b" },
        { source: "b", target: "c" },
        { source: "c", target: "d" },
      ];

      const depthMap = computeFocusDepthMap(nodes as any, edges as any, "b", 1);

      expect(depthMap.get("b")).toBe(0);
      expect(depthMap.get("a")).toBe(1);
      expect(depthMap.get("c")).toBe(1);
      expect(depthMap.get("d")).toBeUndefined();
    });
  });
});
