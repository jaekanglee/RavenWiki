---
title: Multi-Host Vault Repository Switching Plan
created: 2026-07-28
updated: 2026-07-28
type: rule
tags: [system, meta, architecture, plan, multi-host, remote-vault, desktop, ui]
status: completed
---

# Multi-Host Vault Repository Switching Plan

> **BLUF**: Raven 데스크톱 앱( 및 Dashboard UI)을 단일 `localhost:8765` 연결 구조에서 **Multi-Host Thin Client** 아키텍처로 확장합니다. 기존에 Vault(보관소)를 전환하듯, 사용자는 원하는 PC의 IP(`localhost`, `192.168.x.x`, Tailscale IP 등)를 통째로 컨텍스트 전환하여 해당 PC의 `~/Raven/` 루트 지식베이스 전체를 완벽하게 탐색 및 관리할 수 있습니다.

---

## 1. 개요 및 설계 원칙

### 1.1 배경
- 현재 Raven 대시보드는 백엔드 API (`http://127.0.0.1:8765`)가 동일 로컬 머신에 존재한다는 전제로 작동합니다.
- 하지만 사용자는 집 데스크톱, 맥북, VPS, NAS 등 여러 디바이스에서 각각 `~/Raven/` 보관소를 운영할 수 있습니다.
- 데스크톱 앱이 여러 호스트(Remote IP)에 독립적으로 떠 있는 Raven 백엔드 서버를 "볼트 바꾸듯 통째로 전환"할 수 있다면, 복잡한 동기화 프로토콜 없이도 강력한 Multi-PC 지식 관리가 가능해집니다.

### 1.2 핵심 아키텍처 원칙
1. **Thin Client & Simple Switch**:
   - UI는 껍데기(Client)이며 모든 마크다운 파싱, DB 빌드, FTS5 검색, 그래프 생성은 선택된 호스트의 Raven API 서버가 수행합니다.
2. **Context Isolation**:
   - 호스트를 스위칭하면 대시보드 전체의 API Base URL이 변경되며, 해당 호스트의 `~/Raven/` 및 포함된 Vault 목록으로 컨텍스트가 100% 깔끔하게 교체됩니다.
3. **Zero Complexity UI**:
   - 화면을 복잡하게 분할하지 않고, 기존 Vault Picker 부근에 **Host Switcher**를 결합하여 단 한 번의 클릭으로 기기 간 이동이 가능하게 합니다.

---

## 2. 데이터 모델 및 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                Raven Desktop / Dashboard App                │
│                                                             │
│  Host Connection Store (localStorage / connections.json)     │
│  - Active Host: "Home Desktop" (http://192.168.0.15:8765)   │
│  - Hosts: [Local, Home Desktop, VPS]                        │
└──────────────────────────────┬──────────────────────────────┘
                               │ Dynamic API Dispatch
                               ▼
 ┌─────────────────────────────┴─────────────────────────────┐
 │                       Target Host                         │
 │                                                           │
 │  Host: Home Desktop (192.168.0.15:8765)                   │
 │  Vaults Root: ~/Raven/                                    │
 │  ├── Vault A (personal)   ──► wiki.db / content / _meta   │
 │  └── Vault B (work-2026)  ──► wiki.db / content / _meta   │
 └───────────────────────────────────────────────────────────┘
```

### 2.1 Host 연결 데이터 구조 (Client-side)

```typescript
export interface HostConnection {
  id: string;             // e.g. "local", "home-desktop"
  name: string;           // e.g. "내 Mac", "집 데스크톱"
  endpoint: string;       // e.g. "http://127.0.0.1:8765", "http://192.168.0.15:8765"
  isLocal: boolean;       // 로컬 백엔드 여부
  lastConnectedAt?: string;
  token?: string;         // (Phase 4 선택) Bearer Auth 토큰
}
```

---

## 3. 단계별 상세 구현 계획 (Implementation Steps)

### Phase 1: Dynamic API Dispatcher (`dashboard/src/lib/api.ts`)
- [x] `getBaseUrl()` 헬퍼 도입: `localStorage`의 `raven:active_host_url`을 감지하여 모든 fetch 요청의 prefix로 사용.
- [x] 상대 경로 (`/api/vaults`) 호출 방식을 동적 절대 경로 (`${getBaseUrl()}/api/vaults`) 또는 커스텀 fetch wrapper로 통일.
- [x] 호스트 상태 변경 시 캐시 클리어 및 리액트 컴포넌트 갱신 트리거 구축.

### Phase 2: Host Manager & Switcher UI (`dashboard/src/components/`)
- [x] `HostPicker` / `VaultPicker` 연동:
  - Header/Sidebar의 VaultPicker 영역 상단에 `HostPicker` 배치.
- [x] `HostAddModal` (새 호스트 등록):
  - 호스트 별칭 (Name) 및 URL (IP:Port) 입력 폼.
  - "연결 테스트 (Ping)" 버튼: `GET ${url}/api/vaults` 호출 후 성공 시만 저장.
- [x] 호스트 전환 시 액션:
  1. `raven:active_host_url` 갱신
  2. 대상 호스트의 첫 번째 Vault 자동 선택 (`raven:active_vault` 갱신)
  3. 전체 대시보드 state/route 초기화 (`navigate("/")`)

### Phase 3: Server CORS & Connectivity Support (`raven/api/server.py`)
- [x] `raven/api/server.py` CORS 미들웨어 점검:
  - 타 PC의 데스크톱/웹 브라우저에서 원격 접속 시 CORS 블로킹 방지를 위한 Allow-Origin 허용 (`CORSMiddleware`).
- [x] Tauri Desktop HTTP 보안 정책 검증 (`desktop/src-tauri/tauri.conf.json`):
  - 외부 IP 대상 HTTP/HTTPS 요청 허용 범위 확정.

### Phase 4: 안전 장치 & 오프라인 처리 (Fallback & Safety)
- [x] 원격 호스트 연결 해제/네트워크 오류 시 에러 바너 및 "로컬 호스트로 복귀" 원클릭 버튼 제공.
- [x] 호스트별 헬스 체크 인디케이터 (초록/빨강 뱃지) 표시.

---

## 4. 완성도 체크리스트 (Completeness Checklist)

| 구분 | 검증 항목 | 기준 및 확인 방법 | 완료 여부 |
|---|---|---|:---:|
| **API** | API Base URL 동적 Dispatch | `api.ts` 및 `api-base.ts`를 통해 모든 API 호출이 `active_host_url`로 전송되는가 | [x] |
| **API** | 백엔드 CORS 통신 | 타 IP에서 API 호출 시 CORS 에러가 발생하지 않는가 (`RAVEN_ALLOW_ALL_CORS=1`) | [x] |
| **UI** | 호스트 등록/삭제 마법사 | 모달을 통해 이름과 IP/Port를 입력하여 성공적으로 등록/삭제 가능한가 | [x] |
| **UI** | 핑(Ping) 헬스체크 | 등록 전 `GET /api/vaults` 테스트로 접속 불가능한 IP 방지 | [x] |
| **UI** | 호스트 통째 스위칭 | 호스트 전환 시 Vault 목록, 페이지 트리, 지식 그래프가 해당 호스트의 `~/Raven/`으로 즉시 교체되는가 | [x] |
| **안전성** | 연결 끊김 Fallback | 원격 호스트 오프라인 시 로컬 호스트로 즉시 복귀 가능 | [x] |
| **빌드** | TypeScript & Vite 빌드 | `cd dashboard && npm run build` 컴파일 경고/에러 없음 | [x] |
| **테스트** | Python Backend 테스트 | `pytest tests/test_multi_host_api.py -q` 통과 | [x] |

---

## 5. 연관 문서 및 참고 사항
- `README.md` — Multi-vault & WIKI_VAULTS_DIR 정체성
- `_meta/deployment.md` — Tailscale 기반 원격 배포 및 IP 가이드
- `dashboard/src/lib/api.ts` — API 연동 모듈
