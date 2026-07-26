---
title: "ADR 2026-07-27: Compose Multiplatform (CMP) Mobile App Architecture"
created: 2026-07-27
type: adr
tags: [mobile, cmp, architecture, ux]
---

# ADR 2026-07-27: Compose Multiplatform (CMP) Mobile App Architecture

> **결정 (BLUF):** Raven 모바일 앱(CMP)은 Zettelkasten 지식 소비와 탐색(Read & Traverse)을 V1.0 MVP의 최우선 가치로 삼으며, 향후 **마크다운 문서 작성 및 부가 확장 기능(Post-MVP)까지 유연하게 수용할 수 있는 확장성**을 고려하여 설계한다. QR 코드 기반 API 연동, SQLDelight 하이브리드 오프라인 캐싱, 그리고 슬라이딩 패널(Stackable Cards) 기반의 프리미엄 다크모드 뷰어로 시작한다.

## 맥락 (Context)

Raven은 사람을 1차 사용자로 하는 local-first 마크다운 PKM입니다. 사용자는 언제 어디서나 구축된 지식(Concept, Rule 등)에 접근하고 복기하기를 원합니다. 
이를 위해 iOS와 Android를 동시에 타겟팅할 수 있는 Compose Multiplatform(CMP) 기반의 네이티브 모바일 앱 프로젝트를 시작하며, 앱의 정체성과 기술 스택을 정의할 필요가 있습니다.

## 결정 (Decision)

### 1. 기능 우선순위 (MVP Scope): 지식 소비 및 연결 (Read & Traverse)
- 모바일 환경의 제약(작은 화면, 잦은 끊김)을 고려하여 첫 릴리즈(v1.0)에서는 복잡한 마크다운 편집 기능을 제외하고, 기 구축된 Vault의 문서를 **빠르게 읽고 검색**하며 오프라인에서도 지식을 쾌적하게 복기하는 **강력한 뷰어(Viewer)**에 집중합니다.

### 2. 내비게이션 UX: 슬라이딩 패널 (Stackable Cards / Andy Matuschak Style)
- Wikilink를 타고 깊이 탐색하는 제텔카스텐의 특성을 반영하여, 화면이 완전히 전환되는 기존 모바일 스택 대신 **슬라이딩 패널(가로 스크롤 스택)**을 채택합니다.
- 링크를 누를 때마다 새 페이지가 우측에서 반쯤 겹치듯 스와이프되며, 스와이프 제스처를 통해 즉각적으로 이전 맥락(Context)을 확인할 수 있습니다.

### 3. UI/UX 테마: Custom Premium (Dark-mode First)
- 구글 머티리얼(M3)이나 애플 쿠퍼티노 표준 가이드라인에 얽매이지 않고, Raven만의 독자적인 세련된 프리미엄 디자인(블러 효과, 유려한 타이포그래피, 다크모드 기반)을 안드로이드와 iOS에 동일하게 적용합니다.

### 4. 페어링 및 보안 (Security): QR 코드 주입 (Static API Key)
- 별도의 복잡한 로그인/회원가입 없이, 데스크톱 대시보드 화면에 나타난 QR 코드를 모바일 카메라로 1회 스캔하여 연결을 완료합니다.
- QR 코드 안에는 데스크톱 API 엔드포인트(Tailscale IP 등)와 `RAVEN_API_KEY`(정적 토큰)가 포함되며, 이후 모든 모바일 요청의 HTTP 헤더에 해당 Key를 담아 통신합니다.

### 5. 데이터 동기화: 하이브리드 캐싱 (SQLDelight)
- KMP 호환 라이브러리인 `SQLDelight`를 사용하여 모바일 내부에 로컬 SQLite를 구축합니다.
- 조회한 문서와 즐겨찾기 문서를 캐싱하여 네트워크가 없는 오프라인 상태에서도 뷰어 역할을 완벽히 수행합니다.

---

## 🚀 향후 로드맵 (Post-MVP 확장성 고려)

뷰어(Viewer) 기능이 성공적으로 안착한 이후, 모바일 앱은 다음과 같은 진화를 염두에 두고 아키텍처를 유연하게 설계합니다:

1. **문서 작성 및 Quick Capture:**
   - 모바일 기기의 강점(음성 입력, 카메라, 공유 확장 등)을 활용하여 이동 중에도 빠르게 아이디어를 캡처하고, `Draft` 형태로 로컬 SQLite 큐에 저장 후 오프라인 상태가 해제되면 데스크톱 Vault로 동기화(Sync)합니다.
2. **모바일 마크다운 에디터:**
   - 뷰어를 넘어 본문을 직접 수정하고 태그를 갱신할 수 있도록, 경량화된 모바일 맞춤형 마크다운 에디터 모듈을 도입합니다.
3. **확장 기능 (에이전트 및 멀티미디어):**
   - 향후 모바일 앱에서도 Layer 2(에이전트) 옵션을 켜서 간단한 대화를 통해 Vault 내 문서를 조회하거나 편집을 위임할 수 있는 인터페이스를 추가합니다.

---

## 🛠 아키텍처 기술 스택 (Architecture Stack)

- **UI Framework:** Compose Multiplatform (CMP)
- **Networking:** Ktor Client (HTTP/API 연동)
- **Local DB (Cache):** SQLDelight (SQLite Multiplatform)
- **Serialization:** `kotlinx.serialization`
- **DI (Dependency Injection):** Koin
- **Camera/QR:** Android(CameraX), iOS(AVFoundation) 브릿지 연동 혹은 ZXing KMP Wrapper 적용
