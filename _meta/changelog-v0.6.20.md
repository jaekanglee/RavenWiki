# raven v0.6.20 — TextField 공통 컴포넌트 + 좌우 패딩

> **핵심**: 앱 내 인라인 `<label><span/><input/></label>` 반복 패턴을 `<TextField>` 공통 컴포넌트로 추출. `globals.css` `.input-base` 패딩을 `14px 0` → `14px 14px` 로 변경해 좌우 답답함 해소.

릴리스 일자: 2026-06-29
이전: v0.6.19 (path picker)

---

## 한 줄 요약

`dashboard/src/components/ui/TextField.tsx` 신규 — label + input + helper + error + multiline을 한 컴포넌트로. NewPageButton/NewFolderButton 3개 인라인 입력 필드를 `<TextField>` 로 교체. `globals.css` 의 `.input-base` 좌우 패딩 0 → 14px.

## 1. 사용자 원칙 (확정, 2026-06-29)

> "개발하면서 텍스트 라벨이던 버튼이던 가급적 재사용할 수 있게 모두 컴포넌트화 하고, 컬러 폰트 스타일 등도 가급적 구조화하면서 재사용할 수 있게 하자. 꼭 기억해."

→ 이번 패치는 첫 적용. surgical — 1 컴포넌트 + 2 사용처만. 나머지 3개(`NewVaultWizard`, `NewPageInline`, `DeleteButton`)는 후속 패치.

## 2. 변경 사항

### 2-1. `dashboard/src/components/ui/TextField.tsx` (신규)

```tsx
<TextField
  label="경로"
  required
  value={slug}
  onChange={...}
  placeholder="content/my-concept"
  helper="좌측에서 폴더를 클릭하거나 직접 입력하세요"
  error={err}  // 있으면 helper 대신 표시
  multiline    // true면 textarea
  autoFocus    // native input attrs 그대로 위임
  onKeyDown={...}
/>
```

- `forwardRef` — native input/textarea ref 그대로 노출
- `Omit<InputHTMLAttributes, "size">` 상속 — value, onChange, placeholder, autoFocus, onKeyDown 등 모두 위임
- `useId()` — 라벨-인풋 연결 자동
- `labelStyle` / `labelTextStyle` / `helperStyle` — 인라인이지만 토큰 변수 사용 (`var(--color-ink)` 등)
- `multiline` true 시 textarea, 아니면 input

### 2-2. `dashboard/src/styles/globals.css` (1 라인)

```diff
- padding: 14px 0;
+ padding: 14px 14px;
+ box-sizing: border-box;
```

- 좌우 패딩 0 → 14px (좌우 답답함 해소)
- `box-sizing: border-box` 추가 (height 56px 안에 패딩 포함)

### 2-3. `dashboard/src/components/NewPageButton.tsx` (-59 / +30)

- `<TextField label="경로" required ... helper="좌측에서 폴더..." />`
- `<TextField label="제목" required ... placeholder="내 컨셉" />`

### 2-4. `dashboard/src/components/NewFolderButton.tsx` (-40 / +17)

- `<TextField label="폴더 이름" autoFocus onKeyDown={Enter→submit} helper="예: ..." />`

## 3. 회귀 가드

### 3-1. `dashboard/tests/TextField.test.tsx` (신규, 6 tests)

1. label + input 렌더 + ref forwarding
2. helper 텍스트 표시
3. error prop 시 에러 메시지 표시
4. required 시 라벨 옆 `*`
5. .input-base 클래스 보장 (CSS 패딩 검증은 globals.css 직접 확인)
6. multiline 시 textarea 렌더

## 4. 검증

| 항목 | 결과 |
|---|---|
| vitest | **14 파일 / 75 tests pass** (회귀 0) |
| tsc -b | **exit 0** |
| 브라우저 smoke | `.input-base` 좌우 패딩 14px 정상 적용 확인 |

## 5. 효과

| 항목 | 이전 | 이후 |
|---|---|---|
| NewPageButton 인라인 input | 60줄 (label + span + input + helper) | 12줄 (TextField 한 줄) |
| NewFolderButton 인라인 input | 30줄 | 9줄 |
| 좌우 패딩 | 0px (글자 left/right에 붙음) | 14px (가독성) |
| 코드 추적 | 한 곳 수정 시 3+ 곳 동기화 | 한 곳 (TextField) |

## 6. 후속 작업 후보

- `NewVaultWizard`, `NewPageInline`, `DeleteButton` 도 TextField 교체 (이번엔 surgical로 미포함)
- `<SelectField>`, `<TextAreaField>`, `<Button>` 등 다른 공통 컴포넌트 — 사용자 원칙
- CSS 토큰 객체화 (`var(--color-ink)` → `tokens.color.ink` 같은 JS 객체로) — 점진
- 메모리 §다음 큐: Type ADR + 📑 Index + folder hover 메뉴, MiniMax 회귀 검증