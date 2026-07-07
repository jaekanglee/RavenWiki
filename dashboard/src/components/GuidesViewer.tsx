// v0.7.89+ — GuidesViewer: Lite bootstrap 3종 split view 본체.
// 페이지(/guides)와 drawer(VaultManage 우측)에서 재사용.
//
// props:
//   - vaults: 등록된 vault 목록 (drawer는 부모가 주입, page는 자체 fetch)
//   - activeVault: 시작 시 선택할 vault. drawer에서는 locked.
//   - vaultLocked: true면 좌측 vault select 비활성화 (drawer 시나리오).
//                  false면 자유 변경 (페이지 시나리오).
//   - defaultKind: 초기 선택 kind (기본: PROJECT-WORKFLOW.md).
//   - onClose: drawer의 ✕ 버튼용 콜백 (없으면 ✕ 미표시).
//
// Lite bootstrap 3종 (read-only) — 편집 ❌. AGENTS.md §4 Tier 2 표면.

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  fetchGuide,
  LITE_GUIDE_KINDS,
  type LiteGuideKind,
  type LiteGuideResult,
  type VaultInfo,
} from "../lib/api";
import { MarkdownView } from "../components/MarkdownView";
import { EmptyState } from "../components/ui/EmptyState";

const KIND_META: Record<
  LiteGuideKind,
  { title: string; desc: string; icon: string }
> = {
  "_meta/agents/SCHEMA.md": {
    title: "SCHEMA.md",
    desc: "데이터 계약 — frontmatter / type 9종 / tag taxonomy / wikilink / raw 권한 / lint",
    icon: "🧬",
  },
  "_meta/agents/PROJECT-WORKFLOW.md": {
    title: "PROJECT-WORKFLOW.md",
    desc: "운영 사실 — 읽기순서 / MCP 매핑 / 권한 / 저장신호 / 협업규칙",
    icon: "🛠",
  },
  "log.md": {
    title: "log.md",
    desc: "작업 이력 — vault create/append/rotate 이벤트 (append-only)",
    icon: "📋",
  },
};

export interface GuidesViewerProps {
  vaults: VaultInfo[];
  activeVault: string;
  vaultLocked?: boolean;
  defaultKind?: LiteGuideKind;
  onClose?: () => void;
  /** drawer 안에서 host 컨테이너 폭이 좁을 때 좌측 list 폭 축소. */
  compact?: boolean;
}

export function GuidesViewer({
  vaults,
  activeVault: initialVault,
  vaultLocked = false,
  defaultKind = LITE_GUIDE_KINDS[1],
  onClose,
  compact = false,
}: GuidesViewerProps) {
  const [activeVault, setActiveVault] = useState<string>(initialVault);
  const [activeKind, setActiveKind] = useState<LiteGuideKind>(defaultKind);
  const [guide, setGuide] = useState<LiteGuideResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // vaultLocked: drawer 외부에서 activeVault 변경 시 (drawer 재오픈 등) 동기화.
  useEffect(() => {
    if (vaultLocked) setActiveVault(initialVault);
  }, [initialVault, vaultLocked]);

  const loadGuide = useCallback(async () => {
    if (!activeVault) return;
    setLoading(true);
    setError(null);
    try {
      const r = await fetchGuide(activeVault, activeKind);
      if (!r) {
        setGuide(null);
        setError("이 파일은 vault에 존재하지 않습니다 (Lite bootstrap 미주입 vault).");
      } else {
        setGuide(r);
      }
    } catch (e) {
      setGuide(null);
      setError(String(e instanceof Error ? e.message : e));
    } finally {
      setLoading(false);
    }
  }, [activeVault, activeKind]);

  useEffect(() => {
    loadGuide();
  }, [loadGuide]);

  const activeMeta = useMemo(() => KIND_META[activeKind], [activeKind]);

  if (vaults.length === 0) {
    return <EmptyState title="보관소가 없습니다" description="먼저 보관소를 생성해 주세요." />;
  }

  return (
    <div
      className="guides-split"
      style={{
        display: "grid",
        gridTemplateColumns: compact
          ? "minmax(200px, 240px) 1fr"
          : "minmax(240px, 320px) 1fr",
        gap: 12,
        alignItems: "stretch",
        height: compact ? "100%" : undefined,
      }}
    >
      {/* ─── 좌측: vault + 3종 파일 리스트 ─── */}
      <aside
        style={{
          background: "var(--color-surface)",
          border: "1px solid var(--color-hairline)",
          borderRadius: "var(--radius-md)",
          padding: 12,
          display: "flex",
          flexDirection: "column",
          gap: 12,
          minHeight: compact ? 0 : 480,
          minWidth: 0,
        }}
      >
        {/* vault 선택 (drawer면 locked) */}
        <div>
          <div
            style={{
              fontSize: 11,
              fontWeight: 700,
              letterSpacing: "0.32px",
              color: "var(--color-muted)",
              fontFamily: "var(--font-display)",
              marginBottom: 6,
            }}
          >
            보관소{vaultLocked ? " (locked)" : ""}
          </div>
          <select
            className="input-base"
            value={activeVault}
            onChange={(e) => setActiveVault(e.target.value)}
            disabled={vaultLocked}
            aria-label="보관소 선택"
            style={{ width: "100%", margin: 0, opacity: vaultLocked ? 0.7 : 1 }}
          >
            {vaults
              .slice()
              .sort((a, b) => {
                if (a.default && !b.default) return -1;
                if (!a.default && b.default) return 1;
                return a.name.localeCompare(b.name);
              })
              .map((v) => (
                <option key={v.name} value={v.name}>
                  {v.default ? "★ " : ""}
                  {v.name}
                </option>
              ))}
          </select>
        </div>

        {/* 3종 파일 리스트 */}
        <div>
          <div
            style={{
              fontSize: 11,
              fontWeight: 700,
              letterSpacing: "0.32px",
              color: "var(--color-muted)",
              fontFamily: "var(--font-display)",
              marginBottom: 6,
            }}
          >
            Lite bootstrap 3종
          </div>
          <ul style={{ listStyle: "none", margin: 0, padding: 0, display: "flex", flexDirection: "column", gap: 4 }}>
            {LITE_GUIDE_KINDS.map((k) => {
              const meta = KIND_META[k];
              const isActive = k === activeKind;
              return (
                <li key={k}>
                  <button
                    type="button"
                    onClick={() => setActiveKind(k)}
                    aria-current={isActive ? "true" : undefined}
                    title={k}
                    style={{
                      width: "100%",
                      textAlign: "left",
                      padding: "8px 10px",
                      borderRadius: "var(--radius-sm)",
                      border: "1px solid",
                      borderColor: isActive
                        ? "var(--color-primary)"
                        : "var(--color-hairline)",
                      background: isActive
                        ? "var(--color-primary-bg)"
                        : "transparent",
                      color: "var(--color-ink)",
                      cursor: "pointer",
                      display: "flex",
                      alignItems: "flex-start",
                      gap: 8,
                    }}
                  >
                    <span aria-hidden style={{ fontSize: 14, lineHeight: 1.4 }}>
                      {meta.icon}
                    </span>
                    <span style={{ display: "flex", flexDirection: "column", minWidth: 0, flex: 1 }}>
                      <span style={{ fontSize: 13, fontWeight: 600 }}>{meta.title}</span>
                      <span
                        style={{
                          fontSize: 11,
                          color: "var(--color-muted)",
                          fontFamily: "ui-monospace, SFMono-Regular, monospace",
                          whiteSpace: "nowrap",
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                        }}
                      >
                        {k}
                      </span>
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        </div>

        {!compact && (
          <div
            style={{
              marginTop: "auto",
              paddingTop: 12,
              borderTop: "1px solid var(--color-hairline)",
              fontSize: 11,
              color: "var(--color-muted)",
              lineHeight: 1.5,
            }}
          >
            Raven이 vault 생성 시 자동 주입하는 3종. 편집이 필요하면
            <code style={{ fontFamily: "ui-monospace, SFMono-Regular, monospace" }}>
              raven meta sync --lite
            </code>
            또는 VaultManage의 '지침 업뎃'을 사용하세요.
            <br />
            <span style={{ opacity: 0.85 }}>
              외부 LLM 에이전트는 표준 MCP
              <code style={{ fontFamily: "ui-monospace, SFMono-Regular, monospace" }}>
                wiki_get_guide(vault, kind)
              </code>
              로도 같은 3종을 조회할 수 있습니다 (v0.7.91+).
            </span>
          </div>
        )}
      </aside>

      {/* ─── 우측: markdown preview ─── */}
      <section
        style={{
          background: "var(--color-surface)",
          border: "1px solid var(--color-hairline)",
          borderRadius: "var(--radius-md)",
          padding: compact ? 16 : 24,
          minHeight: compact ? 0 : 480,
          display: "flex",
          flexDirection: "column",
          gap: 12,
          minWidth: 0,
        }}
      >
        <header
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: 12,
            paddingBottom: 12,
            borderBottom: "1px solid var(--color-hairline)",
          }}
        >
          <div style={{ minWidth: 0, flex: 1 }}>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                fontSize: 15,
                fontWeight: 700,
                color: "var(--color-ink)",
                flexWrap: "wrap",
              }}
            >
              <span aria-hidden>{activeMeta.icon}</span>
              <span>{activeMeta.title}</span>
              <span
                style={{
                  fontSize: 11,
                  fontWeight: 500,
                  color: "var(--color-muted)",
                  fontFamily: "ui-monospace, SFMono-Regular, monospace",
                }}
              >
                {activeKind}
              </span>
            </div>
            <div style={{ fontSize: 12, color: "var(--color-muted)", marginTop: 2 }}>
              {activeMeta.desc}
            </div>
          </div>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              flexShrink: 0,
            }}
          >
            {guide && (
              <span
                style={{
                  fontSize: 11,
                  color: "var(--color-muted)",
                  fontFamily: "ui-monospace, SFMono-Regular, monospace",
                }}
              >
                {guide.size != null ? `${guide.size}B` : "?"}
                {guide.modified ? ` · ${guide.modified}` : ""}
              </span>
            )}
            <button
              type="button"
              onClick={loadGuide}
              className="btn-secondary"
              style={{
                padding: "4px 10px",
                fontSize: 12,
                borderRadius: "var(--radius-sm)",
                border: "1px solid var(--color-hairline)",
                background: "transparent",
                color: "var(--color-ink)",
                cursor: "pointer",
              }}
              title="새로고침"
              aria-label="새로고침"
            >
              ↻
            </button>
            {onClose && (
              <button
                type="button"
                onClick={onClose}
                aria-label="drawer 닫기"
                title="닫기"
                style={{
                  padding: "4px 10px",
                  fontSize: 14,
                  borderRadius: "var(--radius-sm)",
                  border: "1px solid var(--color-hairline)",
                  background: "transparent",
                  color: "var(--color-ink)",
                  cursor: "pointer",
                  lineHeight: 1,
                }}
              >
                ✕
              </button>
            )}
          </div>
        </header>

        {/* read-only 배지 */}
        <div
          style={{
            display: "inline-flex",
            alignSelf: "flex-start",
            alignItems: "center",
            gap: 6,
            padding: "2px 8px",
            borderRadius: 8,
            fontSize: 11,
            fontWeight: 600,
            background: "var(--color-warning-bg, #fff4d6)",
            color: "var(--color-warning-text, #7a5a00)",
          }}
          title="Lite bootstrap 3종은 Raven이 자동 주입/관리 — Dashboard에서 직접 편집하지 않습니다"
        >
          🔒 read-only
        </div>

        <div style={{ flex: 1, overflow: "auto", minHeight: 0 }}>
          {loading ? (
            <div style={{ padding: 16, color: "var(--color-muted)", fontSize: 13 }}>
              불러오는 중…
            </div>
          ) : error ? (
            <EmptyState title="파일이 없습니다" description={error} />
          ) : guide ? (
            <MarkdownView content={guide.content} vault={activeVault} />
          ) : (
            <EmptyState title="선택된 지침이 없습니다" description="좌측에서 파일을 선택하세요." />
          )}
        </div>
      </section>
    </div>
  );
}
