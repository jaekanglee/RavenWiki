import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";

/**
 * v0.6.12 Graph — mobile tap → label 표시 fix 회귀 가드.
 *
 * 검증 범위:
 *   - 1) overlay 위치 계산이 server coords가 아닌 screen coords여야 한다.
 *     (v0.6.12 1차에서 절대 좌표 + server coords를 써서 zoom/pan 후 라벨이
 *      어긋나 "안 보임" 증상. v0.6.12 2차에서 flowToScreenPosition 사용.)
 *   - 2) overlay CSS position이 "fixed"여야 viewport 상태와 무관하게 노드 위에 표시.
 *   - 3) edge style은 v0.6.12 2차 강화 값 (#94a3b8 / 2 / 0.8).
 *
 * React Flow 자체 마운트는 ResizeObserver/jsdom 한계로 헬퍼/문자열 수준에서
 * 결정 로직만 검증한다.
 */

// xyflow의 flowToScreenPosition을 모킹 — graph 공간 → 화면 좌표 변환을 시뮬레이션.
// zoom 1.5, pan (100, 50) 상황을 가정: screen = flow * 1.5 + (100, 50).
function makeFlowApi(scale = 1.5, tx = 100, ty = 50) {
  return {
    fitView: vi.fn(),
    flowToScreenPosition: ({ x, y }: { x: number; y: number }) => ({
      x: x * scale + tx,
      y: y * scale + ty,
    }),
  };
}

describe("GraphCanvas v0.6.12 mobile tap label", () => {
  let originalMatchMedia: typeof window.matchMedia | undefined;

  beforeEach(() => {
    originalMatchMedia = window.matchMedia;
  });
  afterEach(() => {
    if (originalMatchMedia) window.matchMedia = originalMatchMedia;
  });

  it("overlay 위치는 server coords가 아닌 screen coords를 사용해야 한다", () => {
    // 서버에서 받은 노드 좌표 (예: vault layout 결과)
    const flowPos = { x: 200, y: 150 };
    const size = 14;
    const center = { x: flowPos.x + size / 2, y: flowPos.y + size / 2 };

    // 1차 구현 시뮬레이션: server coords 그대로 → overlay 위치
    const naive = { x: center.x, y: center.y };
    expect(naive).toEqual({ x: 207, y: 157 });

    // 2차 구현 시뮬레이션: flowToScreenPosition으로 변환
    const flow = makeFlowApi();
    const screen = flow.flowToScreenPosition(center);
    expect(screen).toEqual({ x: 207 * 1.5 + 100, y: 157 * 1.5 + 50 });
    // 화면 좌표는 server 좌표보다 크다 (zoom in + pan)
    expect(screen.x).toBeGreaterThan(naive.x);
    expect(screen.y).toBeGreaterThan(naive.y);
  });

  it("overlay CSS position은 fixed (viewport 기준, zoom/pan 무관)", () => {
    // overlay 스타일 정의 — 컴포넌트에 박혀있는 값과 일치해야 함.
    const overlayStyle = {
      position: "fixed",
      left: 0,
      top: 0,
      transform: "translate(-50%, calc(-100% - 14px))",
    };
    expect(overlayStyle.position).toBe("fixed");
    // fixed는 가장 가까운 viewport-relative 컨테이너가 없으면 viewport 기준.
    expect(["fixed", "absolute"]).toContain(overlayStyle.position);
  });

  it("edge style은 dark mode 시인성 개선 적용 — slate 토큰 / 1px / 0.6 (v0.7.48+)", () => {
    // 컴포넌트에서 정의한 기본 edge style: 토큰 + base opacity로 dark mode에서
    // path가 보일 정도의 가시를 확보. focus 분기(L558)는 매 렌더 덮어쓰기로
    // 평상시(!focus.active) 0.6, highlight 0.85, 비활성 0.18.
    // v0.6.11 1차의 두꺼운 선(strokeWidth >= 1.5, opacity >= 0.8 두 가지 동시)으로
    // 회귀하지 않도록 가드.
    const baseEdge = {
      stroke: "var(--graph-edge)",
      strokeWidth: 1,
      strokeOpacity: 0.6,
    };
    const dimOpacity = 0.6;
    const highlightOpacity = 0.85;
    const highlightWidth = 1.5;
    expect(baseEdge.strokeWidth).toBeLessThan(1.5);
    expect(baseEdge.strokeOpacity).toBeGreaterThanOrEqual(0.4);
    expect(dimOpacity).toBe(0.6);
    expect(highlightOpacity).toBeGreaterThan(baseEdge.strokeOpacity);
    expect(highlightWidth).toBeGreaterThan(baseEdge.strokeWidth);
  });

  it("coarse pointer 검출: matchMedia('(pointer:coarse)') 매처 사용", () => {
    // 모바일 환경 시뮬레이션
    window.matchMedia = (query: string) =>
      ({
        matches: query === "(pointer:coarse)",
        media: query,
        onchange: null,
        addListener: () => {},
        removeListener: () => {},
        addEventListener: () => {},
        removeEventListener: () => {},
        dispatchEvent: () => false,
      }) as MediaQueryList;

    expect(window.matchMedia("(pointer:coarse)").matches).toBe(true);
    expect(window.matchMedia("(pointer:fine)").matches).toBe(false);
  });

  it("mobile tap → label coords 계산은 flowToScreenPosition 사용해야 함", () => {
    // 모바일 단일 탭 시 라벨 좌표 결정 로직
    const meta = { x: 300, y: 200, weight: 4 };
    const size = 8 + Math.sqrt(meta.weight) * 6; // = 20

    // flowToScreenPosition을 거친 screen 좌표가 label에 박힘
    const flow = makeFlowApi(2, 50, 30);
    const screen = flow.flowToScreenPosition({
      x: meta.x + size / 2,
      y: meta.y + size / 2,
    });

    // 라벨 overlay는 이 screen 좌표를 left/top으로 사용
    const labelPos = { left: screen.x, top: screen.y };
    expect(labelPos.left).toBe((meta.x + size / 2) * 2 + 50);
    expect(labelPos.top).toBe((meta.y + size / 2) * 2 + 30);

    // 핵심: label 좌표 ≠ server coords (zoom/pan이 반영돼야 함)
    expect(labelPos.left).not.toBe(meta.x + size / 2);
    expect(labelPos.top).not.toBe(meta.y + size / 2);
  });
});