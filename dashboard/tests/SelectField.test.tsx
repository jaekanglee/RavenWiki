/* v0.6.29+ — SelectField 공통 컴포넌트.
 *
 * 사용자 원칙 (§13.1): 재사용 컴포넌트 우선. 인라인 label+select 반복 제거.
 * TextField와 동일한 API (label/helper/error/required/disabled).
 *
 * Contract:
 *  1. label + select 렌더
 *  2. options 배열 [{value, label}] 받아 <option> 매핑
 *  3. native select attrs 위임 (value, onChange, disabled, ref)
 *  4. helper/error 표시 (TextField와 동일)
 *  5. .input-base 클래스 (좌우 패딩 14px 보장)
 */
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { SelectField } from "../src/components/ui/SelectField";

const OPTIONS = [
  { value: "concept", label: "일반 노트" },
  { value: "person", label: "사람" },
];

describe("SelectField contract (v0.6.29)", () => {
  it("renders label + select with options", () => {
    render(
      <SelectField
        label="문서 분류"
        value="concept"
        onChange={() => {}}
        options={OPTIONS}
      />
    );
    expect(screen.getByText("문서 분류")).toBeTruthy();
    expect(screen.getByRole("combobox")).toBeTruthy();
    // options이 select 안에 매핑됨
    const select = screen.getByRole("combobox") as HTMLSelectElement;
    expect(select.options.length).toBe(2);
    expect(select.options[0].textContent).toBe("일반 노트");
  });

  it("required indicator shows *", () => {
    render(
      <SelectField
        label="분류"
        required
        value="concept"
        onChange={() => {}}
        options={OPTIONS}
      />
    );
    expect(screen.getByText("분류 *")).toBeTruthy();
  });

  it("shows helper text when provided", () => {
    render(
      <SelectField
        label="분류"
        helper="문서 종류를 선택하세요"
        value="concept"
        onChange={() => {}}
        options={OPTIONS}
      />
    );
    expect(screen.getByText(/문서 종류를 선택하세요/)).toBeTruthy();
  });

  it("shows error message when error prop is set", () => {
    render(
      <SelectField
        label="분류"
        error="선택 필요"
        value="concept"
        onChange={() => {}}
        options={OPTIONS}
      />
    );
    expect(screen.getByText(/선택 필요/)).toBeTruthy();
  });

  it("select uses .input-base class (consistent padding)", () => {
    render(
      <SelectField
        label="분류"
        value="concept"
        onChange={() => {}}
        options={OPTIONS}
      />
    );
    const select = screen.getByRole("combobox");
    expect(select.className).toContain("input-base");
  });
});