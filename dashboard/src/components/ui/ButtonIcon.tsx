// ButtonIcon — Button 안에 들어가는 inline SVG 아이콘 세트 (v0.7.96+).
//
// EmptyIcon (40×40 hero icon)이랑 분리: Button size="sm" = 34px 높이에
// 40px 아이콘이 들어가서 버튼보다 아이콘이 커 보이는 문제 해결 (§13.1).
//
// 기본 size 14 (Button size="sm"/"md" 모두에서 자연스러움). size prop으로
// 오버라이드 가능. currentColor 상속 → 버튼 텍스트 색과 자동 일치.
import React from "react";

const STROKE = {
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 2,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
};

export interface ButtonIconProps {
  size?: number;
}

const baseSvg = (size: number) => ({
  width: size,
  height: size,
  viewBox: "0 0 24 24",
  "aria-hidden": true as const,
  style: { flexShrink: 0 } as React.CSSProperties,
});

export const ButtonIcon = {
  Refresh: ({ size = 14 }: ButtonIconProps = {}) => (
    <svg {...baseSvg(size)} {...STROKE}>
      <path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8" />
      <path d="M21 3v5h-5" />
      <path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16" />
      <path d="M8 16H3v5" />
    </svg>
  ),
};