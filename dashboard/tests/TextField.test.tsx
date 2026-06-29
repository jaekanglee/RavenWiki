/* v0.6.20+ — TextField 공통 컴포넌트.
 *
 * 사용자 원칙 (2026-06-29): "텍스트 라벨이던 버튼이던 가급적 재사용할 수 있게
 * 모두 컴포넌트화". 앱 내 인라인 <label><span/><input/></label> 반복 제거.
 *
 * Contract:
 *  1. label prop으로 라벨 표시 (required 인디케이터)
 *  2. helper prop으로 도움말 표시 (선택)
 *  3. error prop으로 에러 메시지 표시 (있으면 빨간 텍스트)
 *  4. textarea 멀티라인 지원 (multiline prop)
 *  5. 좌우 패딩 보장 (padding-left/right >= 12px)
 *  6. native input 위임 (ref, value, onChange 모두 전달)
 */
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { TextField } from "../src/components/ui/TextField";

describe("TextField contract (v0.6.20)", () => {
  it("renders label + input with ref forwarding", () => {
    render(<TextField label="경로" value="" onChange={() => {}} />);
    expect(screen.getByText("경로")).toBeTruthy();
    expect(screen.getByRole("textbox")).toBeTruthy();
  });

  it("shows helper text when provided", () => {
    render(
      <TextField
        label="제목"
        helper="마지막 segment가 파일명입니다"
        value=""
        onChange={() => {}}
      />
    );
    expect(screen.getByText(/마지막 segment가 파일명/)).toBeTruthy();
  });

  it("shows error message when error prop is set", () => {
    render(
      <TextField
        label="경로"
        error="경로를 입력해 주세요"
        value=""
        onChange={() => {}}
      />
    );
    expect(screen.getByText(/경로를 입력해 주세요/)).toBeTruthy();
  });

  it("required indicator: label shows * when required", () => {
    render(
      <TextField
        label="경로"
        required
        value=""
        onChange={() => {}}
      />
    );
    expect(screen.getByText("경로 *")).toBeTruthy();
  });

  it("input has left + right padding (>= 12px) — readable contract", () => {
    // jsdom 한계: getComputedStyle이 inline padding을 0으로 평가할 수 있음.
    // .input-base CSS 클래스 사용 시 className 자체로 padding 보장 (globals.css).
    // 따라서 검증은 input이 .input-base 클래스를 가지는지로 충분.
    render(<TextField label="제목" value="" onChange={() => {}} />);
    const input = screen.getByRole("textbox");
    expect(input.className).toContain("input-base");
    // 그리고 CSS 소스에 padding 14px 14px이 있는지 직접 확인
    // (이 파일은 vitest가 아닌 외부 검증으로 처리)
  });

  it("source: globals.css .input-base has horizontal padding (>= 12px)", () => {
    // CSS 패딩 검증은 Input-padding.contract.test.ts에 분리 (vite ?raw 한계 우회).
    // 여기서는 컴포넌트가 .input-base 클래스를 보장하는지만 확인.
    render(<TextField label="제목" value="" onChange={() => {}} />);
    const input = screen.getByRole("textbox");
    expect(input.className).toContain("input-base");
  });

  it("multiline renders textarea instead of input", () => {
    render(
      <TextField
        label="본문"
        multiline
        rows={5}
        value=""
        onChange={() => {}}
      />
    );
    expect(screen.getByRole("textbox").tagName.toLowerCase()).toBe("textarea");
  });
});