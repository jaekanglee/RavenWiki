---
title: Raven Desktop Runtime Architecture
created: 2026-07-23
type: rule
tags: [adr, desktop, runtime, tauri, mcp]
audience: agent
confidence: high
status: current
related:
  - README.md
  - raven/api/main.py
  - raven/mcp/cli.py
  - raven/core/lock.py
---

# ADR: Raven Desktop Runtime Architecture

> **결정:** Raven은 Tauri shell이 단일 Python Core를 소유하는 데스크톱 앱으로 간다. 앱 내부 API와 외부 MCP HTTP endpoint는 서로 다른 loopback listener·토큰·수명주기를 사용한다.

## 1. 맥락

현재 개발 환경은 `raven.sh`로 Dashboard, API, MCP를 별도 개발 프로세스로 관리한다. 이는 개발에는 적합하지만, 제품 사용자가 Raven을 실행하기 위해 포트·프로세스·개발 서버를 이해해야 하는 구조는 아니다.

Raven의 Markdown SoT, `wiki.db` 파생 인덱스, Dashboard, MCP라는 제품 경계는 유지한다. 이번 결정은 Python Core를 Rust나 Go로 재작성하는 결정이 아니라, 그 Core를 하나의 데스크톱 제품으로 시작·종료·복구·업데이트하는 runtime 경계를 정하는 결정이다.

## 2. 결정

### 2.1 제품 runtime

```text
Raven.app
├─ Tauri shell
│  ├─ 앱 창과 정적 React Dashboard
│  ├─ 단일 인스턴스와 앱 lifecycle
│  ├─ Core 시작·readiness 확인·종료·crash recovery
│  ├─ 앱 업데이트와 권한 설정
│  └─ runtime 설정 전달
└─ Python Raven Core (앱이 소유하는 child process)
   ├─ Markdown vault I/O
   ├─ wiki.db / 검색 / graph / lint
   ├─ 내부 앱 API listener
   └─ opt-in MCP HTTP listener
```

- Tauri 2는 제품 shell과 lifecycle owner다.
- React Dashboard는 개발용 Vite server가 아니라 정적 빌드 산출물로 앱에 포함한다.
- Tauri shell은 기존 Dashboard를 패키징하는 배포·lifecycle 계층이며, Raven의 다섯 번째 제품 진입점이나 별도 네트워크 surface가 아니다.
- Python Core는 Raven의 Markdown I/O, 파생 DB, 검색, graph, lint, MCP 계약을 계속 소유한다.
- Desktop v1에서 Rust/Go core 재작성은 하지 않는다.
- Tauri는 Core가 준비되기 전 Dashboard를 정상 상태로 보이지 않게 하며, crash 후에는 제한된 재시도와 명확한 복구 UI를 제공한다.

### 2.2 두 loopback listener

동일 Core process 안에 listener를 둘 수 있으나, 내부 앱 surface와 외부 MCP surface는 분리한다.

| surface | bind / port | 인증 | 기본 상태 | 대상 |
|---|---|---|---|---|
| 내부 앱 API | `127.0.0.1:<random-A>` | 실행마다 새 ephemeral session token | 항상 Core와 함께 시작 | Raven.app Dashboard만 |
| 외부 MCP | `127.0.0.1:<configured-B>` | MCP token + Raven permission mode | 기본 OFF, 사용자 opt-in | 외부 MCP client |

- 내부 API의 random port와 ephemeral token은 Tauri가 Core 시작 시 전달하고, Dashboard에는 앱 runtime 설정으로만 전달한다.
- 외부 MCP port는 클라이언트가 재연결할 수 있도록 사용자가 설정한 stable localhost endpoint를 유지할 수 있다. 기본값이나 실제 선택 port는 구현 단계에서 설정 계약으로 확정한다.
- MCP listener가 꺼져 있어도 Raven.app은 정상이다.
- 외부 MCP를 LAN/Tailscale에 노출하거나 `admin` 권한으로 실행하는 것은 Desktop v1의 기본 동작이 아니며, 별도 명시 설정과 보안 검토가 필요하다.

### 2.3 MCP transport 정책

Desktop Runtime이 제공하는 MCP surface는 **opt-in localhost HTTP**다.

- Desktop 앱은 stdio MCP를 시작하거나 UI에 노출하지 않는다.
- 현재 CLI의 stdio transport는 개발·기존 호환 목적의 비-Desktop surface로 유지한다.
- stdio 제거는 기존 MCP client 호환성을 깨는 별도 breaking change이므로, 사용 현황과 deprecation 계획이 확인되기 전에는 이 ADR 범위에 포함하지 않는다.

이 결정으로 앱이 소유한 Core와 MCP client가 동일한 Core process, vault registry, permission mode, audit path를 공유한다.

### 2.4 MCP 권한과 기존 도구 surface

Desktop runtime은 현재 MCP의 read / write / admin 권한 모델을 유지한다. Desktop v1이 새 권한 모델이나 새 협업 workflow를 도입하지는 않는다.

- **Read:** 검색, 페이지 조회, lint, graph, log, advice, relation 조회와 진단 계열 도구.
- **Write:** 기존 문서 update / ingest / archive / draft 흐름과 `wiki_relation_add` / `wiki_relation_remove`를 포함한다.
- **Admin:** 기존 delete / rename처럼 파괴적이거나 광범위한 변경 도구다.

Semantic relation은 이미 MCP 도구 surface에 존재한다. 따라서 Desktop v1에서는 Write 권한의 현재 기능으로 포함하고, relation scope 세분화·review workflow·자동 승인 정책은 후속 결정으로 남긴다.

### 2.5 데이터와 쓰기 경계

- Markdown은 계속 유일한 SoT다.
- `wiki.db`, 검색 인덱스, backlinks와 graph는 Markdown에서 재생성 가능한 파생 상태다.
- backlink은 문서 B에 직접 기록하지 않는다. 문서 A의 `[[문서 B]]` 원본 링크에서 B의 backlink, graph edge, 관계 검색을 계산한다.
- 문서 쓰기는 기존의 atomic replace 경로를 유지한다. Desktop v1은 이에 더해 vault 전체 transaction, workspace writer lock, 작업 큐를 새로 설계하지 않는다.
- schema·대량 Markdown migration·재작성은 preview와 사용자 승인을 먼저 요구한다.

### 2.6 Desktop v1 비목표

다음은 데스크톱 포장이 아니라 협업 저장소 재설계 범위이므로 Desktop v1에서 제외한다.

- vault 전체 writer lock 또는 다중 작성자 충돌 해결
- 작업 큐와 write sequencing
- 새 idempotency / distributed transaction 설계
- multi-agent review workflow와 자동 승인
- CRDT, sync 서비스, remote collaboration
- Python Core의 Rust/Go 재작성
- 상시 background daemon

Tauri가 단일 Core process를 소유하면 동일 앱 인스턴스 안의 중복 실행 위험은 줄어든다. 그러나 여러 MCP client의 동시 쓰기는 기존처럼 experimental이며, 안정 지원으로 표현하지 않는다.

## 3. 결과

### 긍정

- 사용자는 `Raven.app` 하나를 열어 vault 탐색·편집·graph 사용을 시작한다.
- 개발용 고정 포트와 Vite lifecycle이 제품 사용 경험에서 사라진다.
- 내부 앱 API는 매 실행 다른 loopback port와 session token으로 보호된다.
- MCP는 앱과 독립적으로 떠 있는 별도 서버가 아니라, 앱이 소유한 Core의 선택적 외부 surface가 된다.
- Markdown SoT와 기존 4개 진입점의 제품 계약은 유지된다.

### 비용과 위험

- Tauri sidecar packaging, Python runtime bundling, code signing, updater, crash recovery가 새 운영 복잡도다.
- 내부 API와 MCP listener를 같은 process에 두므로 routing·인증 분리의 회귀 테스트가 필요하다.
- stable MCP endpoint의 token 보관·회전·권한 변경 UX를 설정 계약으로 설계해야 한다.
- 실제 여러 앱 인스턴스 또는 외부 MCP client의 동시 write 문제는 이 결정만으로 해결되지 않는다.

## 4. 구현 순서

1. **Runtime spike:** Tauri가 정적 Dashboard와 minimal Python sidecar를 시작·ready-check·종료할 수 있는지 검증한다. 사용자 vault 데이터는 변경하지 않는다.
2. **Internal API:** Core에 random loopback internal listener와 ephemeral token 검증을 추가하고, Dashboard가 runtime config로 연결되게 한다.
3. **MCP opt-in:** Core process 안에서 stable localhost MCP HTTP listener를 설정 기반으로 켜고, MCP token 및 read/write/admin 정책을 적용한다.
4. **Packaging:** macOS `.app` packaging, single-instance, updater, log location, crash recovery를 제품화한다.
5. **Migration UX:** schema 또는 대량 Markdown 변경이 필요한 경우 preview와 명시 승인 흐름을 별도로 추가한다.

각 단계는 독립적으로 동작·종료·실패 복구를 검증한다. Runtime spike 성공은 Desktop 제품 출시나 협업 기능 완료를 의미하지 않는다.

## 5. 검증 기준

- Raven.app 시작 시 단일 Core process가 readiness를 보고하고 Dashboard가 해당 runtime에 연결된다.
- 앱 종료 시 internal API와 MCP listener가 함께 종료되며 orphan process가 남지 않는다.
- 내부 API는 random loopback port와 올바른 session token 없이는 접근할 수 없다.
- MCP OFF 상태에서도 Dashboard와 local vault 기능은 정상이다.
- MCP ON 상태에서 localhost HTTP client가 설정된 permission mode만 사용할 수 있다.
- 기존 CLI stdio transport의 호환 동작은 Desktop runtime 변경으로 깨지지 않는다.
- Markdown write 후 index / graph / backlink 파생 상태가 재빌드 가능하며, `wiki.db` 손상은 Markdown SoT를 훼손하지 않는다.
- 다중 MCP writer 동시성은 experimental로 문서화되고, 안정 보장으로 표현하지 않는다.

## 관련

- [[raven-desktop-runtime-architecture]] — 이 결정 기록
- [[raven-contract-and-user-agent-policy-boundary]] — Raven 계약과 운영자 정책의 소유권 경계
