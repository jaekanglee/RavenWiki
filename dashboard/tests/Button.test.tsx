/* v0.6.28+ — Button 공통 컴포넌트.
 *
 * 사용자 원칙 (2026-06-29 §13): 재사용 컴포넌트 우선. 인라인 버튼 스타일 반복 제거.
 * 4개 모달의 일관된 primary/secondary 버튼 패턴 추출.
 *
 * Contract:
 *  1. variant: "primary" | "secondary" | "danger" | "ghost"
 *  2. native button attrs 위임 (onClick, disabled, type, aria-label, ref)
 *  3. size: "sm" (34px) | "md" (40px) | "lg" (48px) — 기본 md
 *  4. fullWidth: true면 width 100%
 *  5. color: 텍스트 색 오버라이드 (variant=primary의 danger 등)
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { Button } from "../src/components/ui/Button";

describe("Button contract (v0.6.28)", () => {
  it("renders with label", () => {
    render(<Button variant="primary">저장</Button>);
    expect(screen.getByRole("button", { name: /저장/ })).toBeTruthy();
  });

  it("applies className based on variant", () => {
    render(<Button variant="primary">Primary</Button>);
    const btn = screen.getByRole("button", { name: /Primary/ });
    expect(btn.className).toContain("btn-primary");
  });

  it("renders secondary variant", () => {
    render(<Button variant="secondary">취소</Button>);
    const btn = screen.getByRole("button", { name: /취소/ });
    expect(btn.className).toContain("btn-secondary");
  });

  it("renders danger variant (red background)", () => {
    render(<Button variant="danger">삭제</Button>);
    const btn = screen.getByRole("button", { name: /삭제/ });
    expect(btn.className).toContain("btn-primary"); // base class
    expect(btn.style.background).toBe("var(--color-error-text)");
  });

  it("disabled state disables click handler", () => {
    const onClick = vi.fn();
    render(<Button variant="primary" disabled onClick={onClick}>저장</Button>);
    fireEvent.click(screen.getByRole("button", { name: /저장/ }));
    expect(onClick).not.toHaveBeenCalled();
  });

  it("size sm applies smaller height", () => {
    render(<Button variant="secondary" size="sm">세부 옵션</Button>);
    const btn = screen.getByRole("button", { name: /세부 옵션/ });
    expect(btn.style.height).toBe("34px");
  });

  it("fullWidth applies width 100%", () => {
    render(<Button variant="primary" fullWidth>저장</Button>);
    const btn = screen.getByRole("button", { name: /저장/ });
    expect(btn.style.width).toBe("100%");
  });
});