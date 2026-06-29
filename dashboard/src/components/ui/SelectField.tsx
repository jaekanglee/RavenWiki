// SelectField — 앱 공통 select 입력 (v0.6.29+).
//
// 사용자 원칙 (§13.1): "재사용 컴포넌트 우선". TextField와 동일한 API 패턴.
// 인라인 <label><FieldLabel/><select/><helper/></label> 반복 제거.
//
// Contract:
//  - label: 필드 라벨
//  - required: true면 라벨 옆에 *
//  - helper: 선택 아래 회색 도움말
//  - error: 선택 아래 빨간 에러 (있으면 helper 대신)
//  - options: [{value, label}] 배열
//  - native select attrs 위임 (value, onChange, disabled, ref)
//
// 스타일: globals.css의 .input-base를 그대로 사용 (TextField와 동일).
import { forwardRef, useId } from "react";

export interface SelectOption {
  value: string;
  label: string;
}

export interface SelectFieldProps
  extends Omit<React.SelectHTMLAttributes<HTMLSelectElement>, "size"> {
  label: string;
  options: SelectOption[];
  helper?: string;
  error?: string | null;
  required?: boolean;
}

export const SelectField = forwardRef<HTMLSelectElement, SelectFieldProps>(
  function SelectField(
    {
      label,
      options,
      helper,
      error,
      required,
      id,
      className,
      ...rest
    },
    ref
  ) {
    const generatedId = useId();
    const fieldId = id || generatedId;

    const labelStyle: React.CSSProperties = {
      display: "block",
      marginBottom: 16,
    };
    const labelTextStyle: React.CSSProperties = {
      display: "block",
      fontSize: 13,
      fontWeight: 500,
      marginBottom: 6,
      color: "var(--color-ink)",
    };
    const helperStyle: React.CSSProperties = {
      display: "block",
      fontSize: 12,
      color: error ? "var(--color-error-text)" : "var(--color-muted)",
      marginTop: 4,
    };

    return (
      <label htmlFor={fieldId} style={labelStyle}>
        <span style={labelTextStyle}>
          {label}
          {required && " *"}
        </span>
        <select
          id={fieldId}
          ref={ref}
          className={className || "input-base"}
          {...rest}
        >
          {options.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
        {(error || helper) && (
          <span style={helperStyle}>{error || helper}</span>
        )}
      </label>
    );
  }
);