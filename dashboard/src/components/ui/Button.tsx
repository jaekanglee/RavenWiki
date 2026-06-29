// Button — 앱 공통 버튼 (v0.6.28+).
//
// 사용자 원칙 (§13.1): "재사용 컴포넌트 우선". 4개 모달의 일관된
// primary/secondary 버튼 패턴 + DeleteButton의 danger 변형 추출.
//
// Variants:
//  - primary: btn-primary 클래스 (브랜드 색)
//  - secondary: btn-secondary 클래스 (보더/투명)
//  - danger: btn-primary + 빨간 배경 (삭제 등 위험 액션)
//  - ghost: btn-tertiary 클래스 (텍스트만)
//
// Sizes (높이):
//  - sm: 34px (보조 액션, "세부 옵션" 같은 토글)
//  - md: 40px (기본 — 모달 버튼)
//  - lg: 48px (메인 CTA)
//
// native button attrs 그대로 위임 (onClick, disabled, type, aria-*, ref).
import { forwardRef } from "react";

export interface ButtonProps
  extends Omit<React.ButtonHTMLAttributes<HTMLButtonElement>, "size"> {
  variant?: "primary" | "secondary" | "danger" | "ghost";
  size?: "sm" | "md" | "lg";
  fullWidth?: boolean;
}

const SIZE_HEIGHT: Record<NonNullable<ButtonProps["size"]>, number> = {
  sm: 34,
  md: 40,
  lg: 48,
};

const VARIANT_CLASS: Record<NonNullable<ButtonProps["variant"]>, string> = {
  primary: "btn-primary",
  secondary: "btn-secondary",
  danger: "btn-primary",
  ghost: "btn-tertiary",
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  function Button(
    {
      variant = "primary",
      size = "md",
      fullWidth = false,
      className,
      style,
      children,
      ...rest
    },
    ref
  ) {
    const height = SIZE_HEIGHT[size];
    const variantClass = VARIANT_CLASS[variant];

    const mergedStyle: React.CSSProperties = {
      height,
      padding: "10px 20px",
      fontSize: 14,
      ...(fullWidth ? { width: "100%" } : {}),
      // danger는 btn-primary 위에 빨간 배경
      ...(variant === "danger" ? { background: "var(--color-error-text)" } : {}),
      ...style,
    };

    return (
      <button
        ref={ref}
        className={`${variantClass}${className ? ` ${className}` : ""}`}
        style={mergedStyle}
        {...rest}
      >
        {children}
      </button>
    );
  }
);