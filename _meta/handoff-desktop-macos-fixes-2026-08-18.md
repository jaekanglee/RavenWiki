---
title: 핸드오프 — macOS 데스크톱 3대 증상 (검색 안 됨 / 아이콘 안 뜸 / 흰 화면) 조사·수정
created: 2026-08-18
type: rule
tags: [handoff, desktop, tauri, macos, spotlight, webkit]
audience: agent
confidence: high
status: done (커밋 대기 → 커밋 완료)
sources:
  - 실기 재현 (make desktop-install → /Applications/Raven.app 직접 실행/캡처)
  - desktop/src-tauri, scripts/make-dmg.sh, dashboard/src/main.tsx 조사
---

# 핸드오프 — macOS 데스크톱 3대 증상

> **문의**: `make desktop-install`로 설치하면 (1) Spotlight에서 "raven" 검색이 안 됨,
> (2) 앱 아이콘이 안 뜸, (3) `open /Applications/Raven.app`으로 실행하면 프레임 안이 흰 화면.
> **결론**: 세 증상 모두 조사 완료. (2)·(3)은 코드 결함 확정 + 수정 + 재현 테스트로 검증.
> (1)은 코드 결함이 아니라 macOS Spotlight 인덱싱 백로그 — 완화 조치만 가능.

---

## 핵심 전제 — `.app`은 Tauri 번들러가 안 만든다

`make desktop-build`는 `cargo build --release`로 **바이너리만** 만든다.
`.app` 번들 조립은 `scripts/make-dmg.sh`가 Info.plist를 heredoc으로 직접 써서 손으로 한다
(`cd desktop && npm run desktop:build` = `tauri build`는 어디서도 호출되지 않음).

**따라서 `tauri.conf.json`의 `bundle` 섹션(icon 배열, `macOS.infoPlist` 등)은 죽은 설정이다.**
이 사실을 모르고 `tauri.conf.json`만 고치면 아무 효과가 없다 — 실제로 손대야 할 파일은
`scripts/make-dmg.sh`다.

---

## 증상 2: 아이콘 — 확정 버그, 수정 완료

- **원인**: `scripts/make-dmg.sh`가 쓰는 Info.plist heredoc에 `CFBundleIconFile`이 없었음.
  `icon.icns`는 `Contents/Resources/`에 정상 복사되지만, plist가 가리키질 않으니 macOS가
  존재를 모름 (`icon.icns` 자체는 `iconutil`로 까봐도 16~512×@1x/@2x 표준 10종 정상).
- **수정**: `scripts/make-dmg.sh` Info.plist heredoc에 두 줄 추가.
  ```xml
  <key>CFBundleIconFile</key><string>icon.icns</string>
  <key>CFBundleIconName</key><string>icon</string>
  ```
- **검증**: 재빌드 후 `plutil -extract CFBundleIconFile raw Contents/Info.plist` → `icon.icns` 반환 확인.

## 증상 3: 흰 화면 — PWA 캐시 아님, 실제 원인은 렌더러 소실

사용자 가설("PWA 캐시 때문 아니냐")은 **틀렸다** — `main.tsx`에 이미
`if (!window.__TAURI_INTERNALS__)` 가드가 있어 데스크톱에선 Service Worker를 등록조차
안 한다 (v0.7.183에서 이미 처리됨). WebKit 로그로도 `Imported 0 registrations` 확인.

**진짜 원인**: 이 앱은 창 닫기(X)를 종료가 아니라 `hide()`로 처리한다
(`lib.rs` — `WindowEvent::CloseRequested` → `prevent_close()` + `hide()`, 트레이 상주 앱).
macOS는 오래 숨겨진/서스펜드된 WKWebView의 WebContent(렌더러) 프로세스를 회수하는데,
그 상태에서 창을 다시 보이게 해도 **아무도 리로드를 안 시켜서 창 껍데기만 남고 내용은
영구히 빈 채로 고정**된다.

- **재현 방법**: 실행 중인 Raven의 `com.apple.WebKit.WebContent` 프로세스를 `kill -9`로
  강제 종료 → 창은 그대로인데 내용 영역만 빈 채로 남음 (screencapture로 실측: 정상
  176KB PNG → 28KB로 급락, 스크린샷 확인 결과 완전 공백).
- **1차 수정 시도가 부족했던 이유**: 처음엔 트레이 "show" 메뉴 / `RunEvent::Reopen`
  (Dock 아이콘 재클릭) 시점에만 `location.reload()` 복구 로직을 넣었는데, **창이 이미
  보이는 상태에서 렌더러가 죽는 케이스**(내가 재현한 경로)는 못 잡아서 재현 테스트가
  실패했다. → 범위를 넓혀 `WindowEvent::Focused(true)`(창이 포커스를 받을 때마다,
  즉 사용자가 실제로 쳐다보는 모든 순간)로 옮겨서 다시 재현 테스트 → 통과.
- **수정 (`desktop/src-tauri/src/lib.rs`)**:
  - `RECOVER_IF_BLANK_JS` 상수: `#root`에 자식 노드가 없으면 `location.reload()`
  - 트레이 "show" 클릭, `RunEvent::Reopen`, **`WindowEvent::Focused(true)`** 세 지점에서
    모두 이 JS를 `webview.eval()`로 주입
- **부수 개선 (`dashboard/index.html` + `main.tsx`)**: `main.tsx`는 Tauri IPC로
  Python Core 엔드포인트를 확보할 때까지 `ReactDOM.createRoot(...)`를 호출조차 안 하므로,
  그 대기 구간(보통 1~2초, 코어 기동 실패 시 재시도 로직상 이론상 수 분까지 늘어날 수
  있음)엔 `#root`가 텅 비어 CSS 기본값(라이트 배경)이 노출된다. React 마운트 이전에도
  보이는 정적 로더(다크/라이트는 localStorage를 동기 스크립트로 미리 읽어 배경 결정)를
  `index.html`에 추가하고, `main.tsx`가 마운트 성공 시 `#boot-loader`를 제거하도록 수정.
  이건 "고장"은 아니지만 대기 중과 실제 고장(흰 화면)을 시각적으로 구분하기 위함.
- **검증**: `cargo check --release` 통과, `tsc -b --noEmit` 통과, 재빌드·재설치 후
  WebContent kill → `osascript ... activate`로 포커스 부여 → 자동 리로드 → 정상
  렌더링(스크린샷 확인, 보관소 2개로 `probe` 제거도 함께 반영됨) 재현.

## 증상 1: Spotlight 검색 — 코드 결함 아님, 인덱싱 백로그

- `mdls`로 `/Applications/Raven.app`을 조회하면 `kMDItemFSName` 등 기본 속성이 `null` —
  아직 Spotlight 라이브 인덱스에 안 올라간 상태. `mdimport -t -d1`로 강제 파싱하면
  메타데이터 생성 자체는 정상(번들 손상 아님).
- `install-desktop.sh`가 매번 `rm -rf` 후 `cp -R`로 재생성하는 패턴이라, mds 입장에선
  "완전히 새 폴더"로 보여 매 설치마다 재인덱싱 대기열에 다시 선다. 대조군으로
  `/Applications`에 빈 테스트 앱을 만들어봐도 똑같이 `null` — Raven만의 문제가 아니라
  이 macOS 인스턴스 전반의 인덱싱 지연 (이 시점 `mdworker_shared`가 18개 동시 실행 중,
  백로그 확인).
- **완화 수정 (`scripts/install-desktop.sh`)**: 설치 마지막에
  `mdimport -f /Applications/Raven.app || true` 추가 — 재인덱싱을 앞당기려는 best-effort.
  **단, 재검증 결과 이 머신의 백로그가 심해 즉시 반영되진 않았다.** 시간이 지나면
  자연히 해소된다 (코드로 강제할 방법 없음 — mds는 OS 데몬 우선순위 큐라 사용자 툴이
  새치기시킬 수 없음).

---

## 부수 정리 (코드 아님, 런타임 데이터)

`GET /api/vaults/probe/*`가 계속 409를 내고 있었음 — `probe` vault가 이미 사라진
임시 디렉터리(`/private/var/.../tmprwpt0ne0`)를 가리키던 죽은 레지스트리 항목.
`python3 -m raven.cli vault remove probe --force`로 해제 완료 (파일은 원래도 없었으므로
디스크에 영향 없음). 대시보드 쪽 `fetchTree`/`fetchRawList`가 `!ok`를 `null`로 흡수하므로
화면이 깨지진 않았지만, 노이즈 409/404 로그의 원인이었음.

---

## 변경 파일

| 파일 | 변경 |
|---|---|
| `scripts/make-dmg.sh` | Info.plist에 `CFBundleIconFile`/`CFBundleIconName` 추가 |
| `desktop/src-tauri/src/lib.rs` | `Focused(true)`/show/reopen 3곳에서 blank 감지 시 자동 reload |
| `dashboard/index.html` | React 마운트 전 정적 부팅 로더 (테마 동기화) |
| `dashboard/src/main.tsx` | 마운트 성공 시 `#boot-loader` 제거 |
| `scripts/install-desktop.sh` | 설치 후 `mdimport -f` 넛지 |

## 남은 리스크 / 다음에 볼 사람이 알아야 할 것

- Spotlight 지연은 근본 해결이 아니라 완화다. 사용자가 다시 "검색 안 된다"고 하면
  재현 결함이 아니라 "몇 분 기다려보라"가 정답일 가능성이 높다 — 코드를 더 파지 말 것.
- `Focused(true)`마다 `#root.hasChildNodes()` 체크 + 조건부 reload를 건다. 매우 가벼운
  DOM 체크라 성능 영향은 무시할 수준이지만, 향후 `#root`를 감싸는 구조를 바꾸면
  (예: 최상위 wrapper 추가) 이 감지 로직도 같이 갱신해야 한다.
- 코어 기동 자체가 실패하는 경우(포트 충돌, 파이썬 크래시 등) `main.tsx`의 재시도는
  최대 30회 × 15초 타임아웃이라 이론상 수 분간 로더만 보일 수 있다. 이번 작업 범위에는
  없었음 — 별도 이슈로 다룰 것.
