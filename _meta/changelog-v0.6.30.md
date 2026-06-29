# raven v0.6.30 — Button 확장 (pill 변형) + HomePage/NewVaultWizard 교체

> **핵심**: Button에 pill 변형 추가 (pillPrimary/pillSecondary/pill), HomePage/NewVaultWizard의 pill 버튼 교체.

릴리스 일자: 2026-06-29
이전: v0.6.29 (SelectField)

---

## 한 줄 요약

`<Button>` 에 `pillPrimary`/`pillSecondary`/`pill` 3개 variant 추가. HomePage 2개 / NewVaultWizard 3개 인라인 버튼 교체 (-30 / +10줄).

## 1. Button 확장

| variant | class | 기본 height | 용도 |
|---|---|---|---|
| primary | btn-primary | 40 | 모달 메인 액션 |
| secondary | btn-secondary | 40 | 모달 보조 |
| danger | btn-primary + 빨강 | 40 | 위험 액션 |
| ghost | btn-tertiary | (자유) | 텍스트만 |
| **pillPrimary** | btn-pill-primary | (자유) | **카드 메인 액션** |
| **pillSecondary** | btn-pill-secondary | (자유) | **카드 보조** |
| **pill** | btn-pill | (자유) | **카드 일반** |

size prop 미지정 시 variant 기본 height 사용 (size 지정 시 sm/md/lg 우선).

## 2. 변경 사항

### 2-1. `dashboard/src/components/ui/Button.tsx`

- VARIANT_CLASS에 pill* 3개 추가
- VARIANT_DEFAULT_HEIGHT 신규 — pill은 height 자유 (CSS .btn-pill-* 정의 사용)
- mergedStyle: height/conditional + size prop 조건부

### 2-2. `dashboard/src/routes/HomePage.tsx` (-13 / +5)

VaultCard의 "열기" / "관리" 버튼 교체.

### 2-3. `dashboard/src/components/NewVaultWizard.tsx` (-27 / +6)

"다음 →" / "← 이전" / "만들기" 버튼 3개 교체.

## 3. 회귀 검증

| 항목 | 결과 |
|---|---|
| vitest | **20 파일 / 102 tests + 1 skip** (회귀 0) |
| tsc -b | **exit 0** |
| 브라우저 smoke | "열기" = btn-pill-primary, "관리" = btn-pill ✅ |

## 4. 효과

| 항목 | 효과 |
|---|---|
| 인라인 `<button className="btn-pill-*">` | 5개 → 0개 (surgical) |
| 코드 라인 | -30 / +10 (HomePage + NewVaultWizard 합산) |
| 버튼 variant 일관성 | 4 모달 + 페이지 2개 = 6곳 통일 |

## 5. 누적 공통 컴포넌트 (v0.6.20~30, 5종 + 7 variant)

| 컴포넌트 | variant |
|---|---|
| `<TextField>` | — |
| `<SelectField>` | — |
| `<PageMetaRow>` | — |
| `<Modal>` | — |
| `<Button>` | primary/secondary/danger/ghost + **pillPrimary/pillSecondary/pill** |

## 6. 후속 작업

- `<Link>` 도 Button화 (LinkButton?) — `<Link className="btn-...">` 1개 잔존 (HomePage 첫 vault 만들기)
- 자가 사용 위임