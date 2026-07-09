# 구현 계획: 단일 보관소 그래프 폴더 HUD 및 메타데이터 정보 보완 (v3)

## 1. Goal Description
단일 보관소 내 모든 문서가 하나의 위상 평면 위에 같은 레벨의 점으로 그려져 영역 및 위계가 보이지 않는 문제를 해결합니다.  
서버 측 물리 시뮬레이션(gravity) 개입으로 인한 위상 왜곡 및 사용자 지정 좌표(`.graph_positions.json`)와의 불정합 리스크를 원천 차단하기 위해, **"서버 측 폴더 메타데이터 추가 + 클라이언트 측 실시간 Centroid 계산 및 단순 텍스트 표시"** 형태의 안정적이고 가벼운 HUD 구조를 구현합니다.

---

## 2. User Review Required

### ① 아티팩트 저장 경로에 대한 보고 정정
- 본 계획서는 Git 추적 대상인 레포 내의 [graph-reorganization-plan.md](file:///Users/jaekanglee/Dev/Project/Raven/docs/superpowers/plans/graph-reorganization-plan.md)에 저장됩니다.
- 승인 모달에 표시되는 `graph_reorganization_plan.md` 파일은 Antigravity CLI 자체의 격리 디렉토리인 `~/.gemini/antigravity-cli/brain/...` 내부에 생성되어 GUI Proceed 버튼을 트리거하는 도구용 복사본입니다. 따라서 Git 레포 내에서는 검색되지 않는 것이 정상 작동 상태입니다.

### ② 대분류 단순화 통일 (4개)
- 이전 제안의 "2-depth 세부 분류" 코드를 대폭 축소하여, 설명과 완전히 정합되도록 **4대 대분류**(`_meta`, `content`, `raw`, `root`)만 고유 중력 센트로이드로 그룹핑되도록 통일합니다.

### ③ 캔버스 CSS 테마 변수 해석 해결
- Canvas 컨텍스트(`ctx.fillStyle`)는 CSS `var(...)`를 해석하지 못하므로, 컴포넌트 마운트 및 데이터 로드 시점에 `getComputedStyle`로 실제 색상 코드를 1회 구하여 **React Ref에 캐싱**해 두고 프레임 연산에서 오버헤드 없이 호출하여 렌더링합니다.

---

## 3. Proposed Changes

### 백엔드 (Python API 및 분류 엔진)

#### [MODIFY] raven/core/graph.py
* `folder_group_for_slug(slug: str) -> tuple[str, str]` 순수 함수를 추가하여 slug 경로를 deterministic하게 4개 대분류 폴더 그룹 ID 및 한글 라벨 튜플로 매핑합니다.

```python
# raven/core/graph.py 에 추가할 순수 함수

def folder_group_for_slug(slug: str) -> tuple[str, str]:
    """slug 경로에서 4대 대분류 폴더 그룹명과 사용자 표시 라벨을 반환합니다.
    
    결과: (group_id, group_label)
    """
    parts = slug.split('/')
    if not parts or parts[0] == "":
        return "root", "루트 폴더 (root)"

    first = parts[0]
    if first == "_meta":
        return "_meta", "시스템 및 설정 (_meta)"
    if first == "content":
        return "content", "본문 지식 (content)"
    if first == "raw":
        return "raw", "참조 자료 (raw)"

    return first, first
```

#### [MODIFY] raven/api/server.py
* `vault_graph` API 엔드포인트 내의 `wiki.db` 성공 분기와 `rglob` fallback 분기 모두에서 반환되는 각 node 딕셔너리에 `folder_group`과 `folder_label` 메타데이터를 추가합니다.

```python
# raven/api/server.py L932 vault_graph 함수 수정

# Import 문에 folder_group_for_slug 추가
from raven.core.graph import (
    # ...
    folder_group_for_slug as _folder_group_for_slug,
)

# 1) wiki.db 사용 분기 내 nodes 매핑 (L977 부근)
nodes = [
    {
        "id": p["slug"],
        "slug": p["slug"],
        "title": p["title"],  # 기존 title 계약 유지
        "type": p["type"],
        "weight": in_degree.get(p["slug"], 0),
        "folder_group": _folder_group_for_slug(p["slug"])[0],
        "folder_label": _folder_group_for_slug(p["slug"])[1],
    }
    for p in pages
]

# 2) rglob fallback 분기 내 nodes 매핑 (L1079 부근)
nodes.append({
    "id": slug,
    "slug": slug,
    "title": meta.get("title", slug),
    "type": meta.get("type", "?"),
    "folder_group": _folder_group_for_slug(slug)[0],
    "folder_label": _folder_group_for_slug(slug)[1],
})
```

---

### 프론트엔드 (React Dashboard)

#### [MODIFY] dashboard/src/types.ts
* `GraphNode` 인터페이스에 `folder_group` 및 `folder_label` 필드를 추가하며, 기존 `title: string` required 계약을 보존합니다.

```typescript
export interface GraphNode {
  id: string;
  title: string;          // 기존 필수 계약 철저 준수
  slug?: string;
  type?: string;
  weight?: number;
  x?: number;
  y?: number;
  community?: number;
  folder_group?: string;  // [추가]
  folder_label?: string;  // [추가]
}
```

#### [MODIFY] dashboard/src/components/GraphCanvas.tsx
* `resolvedLabelColorRef`와 `resolvedBgColorRef`를 선언해 CSS 변수를 resolve하여 보관합니다.
* `onRenderFramePre` 콜백을 등록하여, 줌 아웃 시점에 HUD 라벨을 그리도록 캔버스 드로잉 코드를 보완하고 **unmount/re-run 시 `onRenderFramePre(null)`로 cleanup**을 명시합니다.

```typescript
// GraphCanvas.tsx 캔버스 HUD 구현부 수정 및 추가

const HUD_LABEL_FONT = "sans-serif";
const HUD_LABEL_BASE_SIZE = 14;

// ... GraphCanvas 컴포넌트 내부 ...
const resolvedLabelColorRef = useRef<string>("rgba(148, 163, 184, 0.7)");
const resolvedBgColorRef = useRef<string>("#0f172a");

// DOM Container 변경 및 테마 변경 시 Computed Style 캐싱
useEffect(() => {
  if (isJSDOM || !containerRef.current) return;
  try {
    const style = window.getComputedStyle(containerRef.current);
    resolvedLabelColorRef.current = style.getPropertyValue("--graph-label-color").trim() || "rgba(148, 163, 184, 0.7)";
    resolvedBgColorRef.current = style.getPropertyValue("--graph-canvas-bg").trim() || "#0f172a";
  } catch (e) {
    // fallback
  }
}, [nodes, isDense]);

useEffect(() => {
  if (isJSDOM) return;
  const graph = graphInstanceRef.current;
  if (!graph) return;

  graph.onRenderFramePre((ctx: CanvasRenderingContext2D, globalScale: number) => {
    const scale = globalScale || 1;
    
    // LOD 임계값: 줌 아웃(scale < 0.6)에서 max(1.0) ~ 줌 인(scale > 1.0)에서 min(0.0)
    const labelOpacity = Math.max(0, Math.min(1, (1.0 - scale) / 0.4));
    if (labelOpacity <= 0.05) return;

    // 1. 실시간 Centroid 연산
    const groupCoords: Record<string, { xSum: number; ySum: number; count: number; label: string }> = {};
    const currentNodes = graph.graphData().nodes;
    
    for (const node of currentNodes) {
      if (typeof node.x !== "number" || typeof node.y !== "number" || !node.folder_group) continue;
      const gid = node.folder_group;
      if (!groupCoords[gid]) {
        groupCoords[gid] = { xSum: 0, ySum: 0, count: 0, label: node.folder_label || gid };
      }
      groupCoords[gid].xSum += node.x;
      groupCoords[gid].ySum += node.y;
      groupCoords[gid].count += 1;
    }

    // 2. HUD 라벨 그리기 (단순 텍스트 + 테마 변수)
    ctx.save();
    const fontSize = Math.max(13, HUD_LABEL_BASE_SIZE / scale);
    ctx.font = `600 ${fontSize}px ${HUD_LABEL_FONT}`;
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";

    for (const gid in groupCoords) {
      const data = groupCoords[gid];
      if (data.count === 0) continue;
      const cx = data.xSum / data.count;
      const cy = data.ySum / data.count;

      const labelText = data.label;

      // 텍스트 시인성 확보를 위한 뒷배경 outline 효과 (테마 변수)
      ctx.fillStyle = resolvedBgColorRef.current;
      ctx.globalAlpha = labelOpacity * 0.8;
      for (let dx = -1.5; dx <= 1.5; dx += 1.5) {
        for (let dy = -1.5; dy <= 1.5; dy += 1.5) {
          if (dx !== 0 || dy !== 0) {
            ctx.fillText(labelText, cx + dx * (0.8 / scale), cy + dy * (0.8 / scale));
          }
        }
      }

      // 본문 텍스트 (테마 변수)
      ctx.fillStyle = resolvedLabelColorRef.current;
      ctx.globalAlpha = labelOpacity * 0.7; // 은은함 유지
      ctx.fillText(labelText, cx, cy);
    }
    ctx.restore();
  });
  
  // onRenderFramePre cleanup 명시
  return () => {
    if (graphInstanceRef.current) {
      graphInstanceRef.current.onRenderFramePre(null);
    }
  };
}, [nodes, edges, isDense]);
```

---

## 4. Verification Plan

### Automated Tests
* **백엔드 테스트 (`tests/test_graph.py`)**:
  - `folder_group_for_slug` 순수 함수의 대분류 4개 분기 로직 테스트 작성.
* **API 계약 통합 테스트 (`tests/test_api.py`)**:
  - `/api/vaults/{name}/graph` 엔드포인트가 **wiki.db 성공 경로**와 **rglob fallback 경로** 양쪽에서 동일하게 `folder_group`과 `folder_label` 메타데이터를 반환하는지 통합 테스트 작성.
* **린트 & 컴파일**:
  - `make typecheck`를 통한 backend 파이썬 타입 정합성 검증.
  - `npm run build` 또는 `npx tsc --noEmit`을 이용해 dashboard TypeScript 빌드 깨짐 없는지 검사.

### Manual Verification
* 대시보드 그래프 뷰어 줌 아웃 시 노드 텍스트가 사라지고 단순 텍스트 기반의 대분류 4개 폴더명 라벨이 은은하게 뜨는지 확인.
* 노드 드래그 시 라벨 위치가 정합성 있게 보정되어 따라 이동하는지 확인.
