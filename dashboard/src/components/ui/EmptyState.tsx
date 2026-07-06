// EmptyState — 앱 공통 빈 상태 (v0.6.10+).
//
// 사용자 원칙 (AGENTS.md §15.1): 빈 상태는 텍스트만 ❌, 일러스트 또는 CTA 포함.
// 사용자 원칙 (ui-ux 스킬 §P): 이모지 ❌ (다크모드 깨짐, OS별 렌더링 차이).
//
// v0.7.73+: icon prop 타입을 string → React.ReactNode로 확장. SVG component
// 직접 전달 가능. 기본값도 📭 이모지 → Lucide-style SVG (Inbox).
//
// Contract:
//  - icon: React.ReactNode (SVG 컴포넌트 권장). 미지정 시 기본 Inbox SVG.
//  - title: 빈 상태 제목 (필수)
//  - description: 보조 설명 (선택)
//  - action: CTA 버튼 등 (선택)
import React from "react";

interface EmptyStateProps {
  /** SVG 컴포넌트 권장. 미지정 시 기본 Inbox SVG. */
  icon?: React.ReactNode;
  title: string;
  description?: string;
  action?: React.ReactNode;
}

// Lucide-style SVG (currentColor → var(--color-ink) 자동 상속).
const DefaultInboxIcon = () => (
  <svg
    width="40"
    height="40"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="1.5"
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden="true"
  >
    <polyline points="22 12 16 12 14 15 10 15 8 12 2 12" />
    <path d="M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z" />
  </svg>
);

export function EmptyState({ icon, title, description, action }: EmptyStateProps) {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: "48px 24px",
        textAlign: "center",
        background: "var(--color-surface-soft)",
        border: "1px dashed var(--color-hairline-strong)",
        borderRadius: "var(--radius-md)",
        color: "var(--color-ink)",
      }}
    >
      <span style={{ marginBottom: 12, userSelect: "none" }} aria-hidden>
        {icon ?? <DefaultInboxIcon />}
      </span>
      <h3 style={{ fontSize: 16, fontWeight: 600, margin: 0, color: "var(--color-ink)" }}>
        {title}
      </h3>
      {description && (
        <p style={{ fontSize: 13, color: "var(--color-muted)", marginTop: 6, marginBottom: 0, maxWidth: 360 }}>
          {description}
        </p>
      )}
      {action && <div style={{ marginTop: 16 }}>{action}</div>}
    </div>
  );
}