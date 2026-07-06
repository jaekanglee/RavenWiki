// EmptyIcon — Lucide-style SVG icon set (v0.7.74+, §13 §P 준수).
//
// EmptyState prop으로 전달할 ReactNode icon 모음. HomePage/VaultManage의
// ActionIcon 패턴과 동일 — 24x24 viewBox, currentColor → var(--color-ink) 자동 상속.
//
// 사용처: dashboard/src/components/ui/EmptyState.tsx 호출처 13곳 (SearchPage,
// PageView, GraphPage, LintPage, WorkspacePage, GardenPage, RawPanel).
import React from "react";

const STROKE = {
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.75,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
};

const baseSvg = (size: number) => ({
  width: size,
  height: size,
  viewBox: "0 0 24 24",
  "aria-hidden": true as const,
});

export const EmptyIcon = {
  // SearchPage 1 — 검색어 입력 유도
  Search: () => (
    <svg {...baseSvg(40)} {...STROKE}>
      <circle cx="11" cy="11" r="8" />
      <path d="m21 21-4.3-4.3" />
    </svg>
  ),
  // SearchPage 2 — 검색 결과 없음
  Folder: () => (
    <svg {...baseSvg(40)} {...STROKE}>
      <path d="M4 20h16a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.93a2 2 0 0 1-1.66-.9l-.82-1.2A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13c0 1.1.9 2 2 2Z" />
    </svg>
  ),
  // PageView — 문서 못 찾음
  File: () => (
    <svg {...baseSvg(40)} {...STROKE}>
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14 2 14 8 20 8" />
      <line x1="9" y1="13" x2="15" y2="13" />
      <line x1="9" y1="17" x2="13" y2="17" />
    </svg>
  ),
  // 새로고침 (LintPage/LogPage/WorkspacePage)
  Refresh: () => (
    <svg {...baseSvg(40)} {...STROKE}>
      <path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8" />
      <path d="M21 3v5h-5" />
      <path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16" />
      <path d="M8 16H3v5" />
    </svg>
  ),
  // GraphPage 1 — 그래프 로딩 중 (스피너 대용)
  Spinner: () => (
    <svg {...baseSvg(40)} {...STROKE}>
      <path d="M21 12a9 9 0 1 1-6.219-8.56" />
    </svg>
  ),
  // GraphPage 2 — 그래프 로드 실패 / WorkspacePage 오류 / RawPanel 오류
  AlertTriangle: () => (
    <svg {...baseSvg(40)} {...STROKE}>
      <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z" />
      <line x1="12" y1="9" x2="12" y2="13" />
      <line x1="12" y1="17" x2="12.01" y2="17" />
    </svg>
  ),
  // GraphPage 3 — 노드 없음
  Database: () => (
    <svg {...baseSvg(40)} {...STROKE}>
      <ellipse cx="12" cy="5" rx="9" ry="3" />
      <path d="M3 5v14a9 3 0 0 0 18 0V5" />
      <path d="M3 12a9 3 0 0 0 18 0" />
    </svg>
  ),
  // GraphPage 4 — 모두 고아 (안개)
  Fog: () => (
    <svg {...baseSvg(40)} {...STROKE}>
      <path d="M17 18a4 4 0 0 0 0-8 6 6 0 0 0-11-2 4 4 0 0 0-.97 7.91" />
      <line x1="8" y1="20" x2="16" y2="20" />
      <line x1="6" y1="22" x2="14" y2="22" />
    </svg>
  ),
  // LintPage — 이슈 없음 (체크)
  Check: () => (
    <svg {...baseSvg(40)} {...STROKE}>
      <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
      <polyline points="22 4 12 14.01 9 11.01" />
    </svg>
  ),
  // GardenPage 1 — 잡초 없음 (반짝임)
  Sparkles: () => (
    <svg {...baseSvg(40)} {...STROKE}>
      <path d="m12 3-1.9 5.8a2 2 0 0 1-1.3 1.3L3 12l5.8 1.9a2 2 0 0 1 1.3 1.3L12 21l1.9-5.8a2 2 0 0 1 1.3-1.3L21 12l-5.8-1.9a2 2 0 0 1-1.3-1.3L12 3z" />
    </svg>
  ),
  // GardenPage 2 — 고아 없음 (네트워크/연결)
  Network: () => (
    <svg {...baseSvg(40)} {...STROKE}>
      <circle cx="12" cy="12" r="3" />
      <circle cx="4" cy="6" r="2" />
      <circle cx="20" cy="6" r="2" />
      <circle cx="4" cy="18" r="2" />
      <circle cx="20" cy="18" r="2" />
      <line x1="9" y1="10" x2="6" y2="7" />
      <line x1="15" y1="10" x2="18" y2="7" />
      <line x1="9" y1="14" x2="6" y2="17" />
      <line x1="15" y1="14" x2="18" y2="17" />
    </svg>
  ),
  // RawPanel — 로딩 중
  Loader: () => (
    <svg {...baseSvg(40)} {...STROKE}>
      <circle cx="12" cy="12" r="10" />
      <polyline points="12 6 12 12 16 14" />
    </svg>
  ),
};