# 구현 계획: 그래프 선택 문서 상세 패널 UI/UX 개편 (데스크탑 및 모바일 대응)

## 1. Goal Description
현재 그래프 화면 우측의 선택 문서 상세 패널(`aside.graph-detail-panel`)은 3개 관계 리스트(나를 참조한 문서, 내가 참조한 문서, 관련 문서)가 세로로 장황하게 나열되어 스크롤 폭발을 일으키고, 큰 버튼들이 공간을 비효율적으로 점유하여 지저분해 보입니다.  
이를 해결하기 위해 **"통계 카드 통합 탭 전환(Tab-integrated Stats) + 컴팩트 미니 액션 툴바 + 단일 리스트 뷰"** 구조로 단순하고 강력하게 개편합니다.  
동시에 **데스크탑 및 모바일 환경** 모두에서 UI가 찌그러지거나 수직 공간을 낭비하지 않도록 반응형 스타일링을 정밀하게 적용합니다.

---

## 2. User Review Required
> [!IMPORTANT]
> **반응형(Responsive) UX 대응 사양**
> 1. **모바일 가로 3열 탭 고정**: 기존 모바일 미디어 쿼리(`.graph-detail-stats { grid-template-columns: 1fr; }`)는 탭 카드를 수직으로 길게 늘어뜨려 공간을 심각하게 낭비합니다. 개편 시 모바일 가로폭에서도 탭 명칭이 짧은 점을 이용해 **가로 3열 레이아웃(`repeat(3, 1fr)`)을 유지**하여 스크롤 오버헤드를 막습니다.
> 2. **미니 액션 툴바 균등 정렬**: 모바일 화면에서는 포커스/열기 버튼이 가로 영역을 균등하게 반반씩 나누어 차지하도록 (`flex: 1`) 설정하여 모바일 터치 접근성을 개선합니다.
> 3. **디테일 리스트 단일화**: 클릭된 활성 탭에 해당하는 단일 리스트만 렌더링되어 스크롤 영역이 분리되므로 모바일 뷰에서도 극도로 콤팩트한 사용성을 제공합니다.

---

## 3. Proposed Changes

### 프론트엔드 (React 및 CSS)

#### [MODIFY] dashboard/src/routes/GraphPage.tsx
* `activeTab` 상태(`"inbound" | "outbound" | "neighbors"`)를 추가합니다.
* 노드가 새로 선택될 때 `activeTab` 기본값은 `"inbound"`로 초기화합니다.
* 3개 카드에 클릭 이벤트 및 활성 상태 CSS 클래스를 연결하여 탭으로 작동하게 합니다.
* 세 섹션 리스트 렌더링 로직을 `activeTab` 분기 조건에 따른 단일 리스트 렌더링으로 일원화합니다.

```typescript
// dashboard/src/routes/GraphPage.tsx 수정 계획

// 1. 컴포넌트 내부에 activeTab 상태 추가
const [activeTab, setActiveTab] = useState<"inbound" | "outbound" | "neighbors" >("inbound");

// 노드 선택 변경 시 탭 기본값 리셋
useEffect(() => {
  setActiveTab("inbound");
}, [selectedNodeId]);

// ... 

// 2. aside.graph-detail-panel JSX 구조 개편
<aside className="graph-detail-panel" aria-label="선택 문서 상세">
  {selectedNodeDetail ? (
    <>
      {/* 컴팩트 헤더 */}
      <div className="graph-detail-header">
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: "flex", gap: 6, alignItems: "center", marginBottom: 4 }}>
            <span className="graph-detail-chip">
              {typeLabel(selectedNodeDetail.node.type) || selectedNodeDetail.node.type || "미분류"}
            </span>
            {selectedNodeDetail.node.vault && (
              <span className="graph-vault-chip">{selectedNodeDetail.node.vault}</span>
            )}
          </div>
          <strong className="graph-detail-title">{selectedNodeDetail.node.title}</strong>
          <p className="graph-detail-slug">{nodeSlug(selectedNodeDetail.node)}</p>
        </div>
      </div>

      {/* 미니 액션 툴바 */}
      <div className="graph-detail-mini-actions">
        <Button
          type="button"
          className="graph-detail-action-btn"
          variant="secondary"
          size="sm"
          onClick={() => {
            dispatchFilters({ type: "setQuery", value: selectedNodeDetail.node.title });
            dispatchFilters({ type: "setSelectedType", value: "all" });
          }}
          title="이 문서와 1-hop 연결망 중심으로 그래프를 포커스합니다"
        >
          🎯 그래프 포커스
        </Button>
        <Button
          type="button"
          className="graph-detail-action-btn"
          variant="ghost"
          size="sm"
          onClick={() => openGraphNode(selectedNodeDetail.node.id)}
          title="문서 읽기/편집 페이지로 이동합니다"
        >
          📖 문서 열기
        </Button>
      </div>

      {/* 통계 기반 클릭 인터랙티브 탭 카드 */}
      <div className="graph-detail-stats">
        <button
          type="button"
          className={`graph-detail-stat-card ${activeTab === "inbound" ? "active" : ""}`}
          onClick={() => setActiveTab("inbound")}
        >
          <span>참조됨</span>
          <strong>{selectedNodeDetail.inbound.length}</strong>
        </button>
        <button
          type="button"
          className={`graph-detail-stat-card ${activeTab === "outbound" ? "active" : ""}`}
          onClick={() => setActiveTab("outbound")}
        >
          <span>참조함</span>
          <strong>{selectedNodeDetail.outbound.length}</strong>
        </button>
        <button
          type="button"
          className={`graph-detail-stat-card ${activeTab === "neighbors" ? "active" : ""}`}
          onClick={() => setActiveTab("neighbors")}
        >
          <span>관련</span>
          <strong>{selectedNodeDetail.neighbors.length}</strong>
        </button>
      </div>

      {/* 단일 관계 목록 출력 영역 */}
      <div className="graph-detail-tab-content">
        {activeTab === "inbound" && (
          <div className="graph-detail-section">
            <h3>나를 참조한 문서 ({selectedNodeDetail.inbound.length})</h3>
            {selectedNodeDetail.inbound.length > 0 ? (
              <ul className="graph-detail-list">
                {selectedNodeDetail.inbound.slice(0, 10).map((node) => (
                  <li key={node.id}>
                    <button
                      type="button"
                      className="graph-detail-link"
                      onClick={() => dispatchFilters({ type: "setSelectedNodeId", value: node.id })}
                      onMouseEnter={() => setHoveredInsightNodeId(node.id)}
                      onMouseLeave={() => setHoveredInsightNodeId(null)}
                    >
                      <span>{node.title}</span>
                      <span className="graph-node-meta-badge">{typeLabel(node.type) || node.type || "미분류"}</span>
                    </button>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="graph-insight-empty">이 문서를 참조하는 문서가 없습니다.</p>
            )}
          </div>
        )}

        {activeTab === "outbound" && (
          <div className="graph-detail-section">
            <h3>내가 참조한 문서 ({selectedNodeDetail.outbound.length})</h3>
            {selectedNodeDetail.outbound.length > 0 ? (
              <ul className="graph-detail-list">
                {selectedNodeDetail.outbound.slice(0, 10).map((node) => (
                  <li key={node.id}>
                    <button
                      type="button"
                      className="graph-detail-link"
                      onClick={() => dispatchFilters({ type: "setSelectedNodeId", value: node.id })}
                      onMouseEnter={() => setHoveredInsightNodeId(node.id)}
                      onMouseLeave={() => setHoveredInsightNodeId(null)}
                    >
                      <span>{node.title}</span>
                      <span className="graph-node-meta-badge">{typeLabel(node.type) || node.type || "미분류"}</span>
                    </button>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="graph-insight-empty">이 문서가 참조하는 문서가 없습니다.</p>
            )}
          </div>
        )}

        {activeTab === "neighbors" && (
          <div className="graph-detail-section">
            <h3>관련 문서 ({selectedNodeDetail.neighbors.length})</h3>
            {selectedNodeDetail.neighbors.length > 0 ? (
              <ul className="graph-detail-list">
                {selectedNodeDetail.neighbors.slice(0, 10).map((node) => (
                  <li key={node.id}>
                    <button
                      type="button"
                      className="graph-detail-link"
                      onClick={() => dispatchFilters({ type: "setSelectedNodeId", value: node.id })}
                      onMouseEnter={() => setHoveredInsightNodeId(node.id)}
                      onMouseLeave={() => setHoveredInsightNodeId(null)}
                    >
                      <span>{node.title}</span>
                      <span className="graph-node-meta-badge">{typeLabel(node.type) || node.type || "미분류"}</span>
                    </button>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="graph-insight-empty">관련된 연결 문서가 없습니다.</p>
            )}
          </div>
        )}
      </div>
    </>
  ) : (
    <div className="graph-detail-empty">
      <strong>문서를 선택해 주세요</strong>
      <p>그래프의 노드를 클릭하면 해당 문서의 참조 위계와 이동 도구가 여기에 콤팩트하게 제공됩니다.</p>
    </div>
  )}
</aside>
```

#### [MODIFY] dashboard/src/styles/globals.css
* 스타일 토큰화 원칙(AGENTS.md §13)을 준수해 하드코딩된 색상을 지양하고 CSS 변수를 적용합니다.
* `.graph-detail-stats` 하위 카드를 클릭 가능한 탭 스타일로 디자인하고, 호버 및 활성(`active`) 상태에 따른 인터랙션 피드백을 강화합니다.
* `.graph-detail-mini-actions` 컴팩트 툴바 스타일을 추가합니다.
* 모바일 미디어 쿼리 내의 세로 정렬 오버라이드 항목을 수정합니다.

```css
/* globals.css 추가 및 수정할 스타일 */

.graph-detail-mini-actions {
  display: flex;
  gap: 6px;
  border-bottom: 1px solid var(--color-hairline);
  padding-bottom: 12px;
}

.graph-detail-mini-actions .graph-detail-action-btn {
  flex: 1; /* 모바일/데스크탑 모두 균등 분할로 터치 면적 확보 */
  justify-content: center;
}

/* 통계 카드를 클릭형 버튼으로 개편 */
.graph-detail-stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}

.graph-detail-stat-card {
  border-radius: 8px;
  padding: 10px 8px;
  background: var(--graph-surface);
  border: 1px solid var(--graph-border);
  text-align: center;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  transition: border-color 0.15s ease, background-color 0.15s ease, transform 0.1s ease;
}

.graph-detail-stat-card:hover {
  border-color: var(--color-info-border);
  background: var(--graph-surface-strong);
  transform: translateY(-1px);
}

.graph-detail-stat-card:active {
  transform: translateY(0);
}

.graph-detail-stat-card.active {
  background: var(--cds-background-brand);
  border-color: var(--color-info-border);
  box-shadow: 0 0 0 1px var(--color-info-border);
}

.graph-detail-stat-card span {
  display: block;
  font-size: 11px;
  color: var(--color-muted);
}

.graph-detail-stat-card strong {
  font-size: 16px;
  color: var(--color-ink);
}

/* 관계 리스트 컴팩트 스타일 */
.graph-detail-tab-content {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  margin-top: 4px;
}

.graph-node-meta-badge {
  font-size: 10.5px;
  font-weight: 600;
  padding: 1px 6px;
  border-radius: 4px;
  background: var(--color-surface-soft);
  color: var(--color-muted);
  border: 1px solid var(--color-hairline);
}

/* ──────────────────────────────────────────────────────────────────────────── */
/* responsive 미디어 쿼리 오버라이드 및 보완 */
/* ──────────────────────────────────────────────────────────────────────────── */

@media (max-width: 744px) {
  /* [수정] 모바일 1열 세로 축소 제거 -> 모바일에서도 3열 가로 탭 유지하여 공간 낭비 방지 */
  .graph-detail-stats {
    grid-template-columns: repeat(3, minmax(0, 1fr)) !important;
  }
}
```

---

## 4. Verification Plan

### Automated Tests
* `npm run build` 또는 `npx tsc --noEmit`을 통해 React 컴파일 에러 유무 확인.
* `vitest --run GraphPage` 실행으로 리액트 라우팅 및 렌더링 회귀 검사.
  - 2026-07-10: `dashboard/tests/GraphPage.detail-panel.test.tsx` 추가 및 `npm test -- --run tests/GraphPage.detail-panel.test.tsx tests/PageView.graph-scope.test.tsx tests/GraphCanvas.obsidian-style.test.ts` 통과.

### Manual Verification
1. 대시보드를 띄우고 그래프 페이지 진입.
2. 데스크탑 창 크기 및 크롬 개발자 도구의 **모바일 디바이스 뷰포트(iPhone, Galaxy 등 375px~430px)**에서 정상 렌더링 여부 점검. (2026-07-10: 사용자 지시로 실제 화면/브라우저 검증은 미실행, 코드 테스트만 수행)
3. 모바일 뷰에서도 "참조됨/참조함/관련" 탭 버튼 3개가 가로로 가지런히 1행 배치되며, 각 터치 영역이 정상 기능하는지 검사. (미실행)
4. 모바일 뷰에서 툴바 버튼들이 50%씩 균등 배분되는지 확인. (미실행)
5. 탭 변경에 따라 상세 내용 스크롤뷰가 캔버스 아래 영역을 침범하지 않고 정상적으로 내부 스크롤되는지 검증. (미실행)
