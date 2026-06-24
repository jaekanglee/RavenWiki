---
title: SQLite vs PostgreSQL (위키 백엔드)
created: 2026-06-25
updated: 2026-06-25
type: comparison
tags: [comparison, search, system, python]
sources: [_meta/system-design.md]
confidence: high
---

# SQLite vs PostgreSQL (위키 백엔드)

## 한 줄 비교

> **SQLite** = 임베디드 DB (파일 1개, $0, 동시성 약함)
> **PostgreSQL** = 서버 DB (서비스, 메모리/CPU 사용, 동시성 강함)

## 7가지 차원 비교

| 차원 | SQLite | PostgreSQL |
|---|---|---|
| **아키텍처** | 임베디드 (in-process) | 서버 (별도 프로세스) |
| **저장** | 파일 1개 (`.db`) | 디렉토리 (data dir) |
| **설치** | `pip install` (Python 내장) | apt + initdb + start |
| **동시성** | writer 1개 (읽기 무제한) | 무제한 |
| **네트워크 접근** | ❌ (로컬만) | ✅ (TCP/IP) |
| **백업** | 파일 복사 | pg_dump / WAL archiving |
| **비용** | $0 | RAM/CPU 점유 (소규모 VPS OK) |

## 우리 선택 (SQLite, 왜?)

[[_meta/system-design]] §2.1 + [[scripts/build_db]]에서 결정.

### 1. 위키 데이터 규모
- 1인 사용자 ([[_meta/system-design]] C4)
- 100~1만 페이지 규모 ([[_meta/system-design]] K1 ≥ 100)
- → SQLite가 **충분히 빠름** (1만 페이지도 MS 단위)

### 2. 비용 = $0
- PostgreSQL은 VPS에서 RAM 점유 (1GB+)
- 우리 VPS = $5/월 (Hetzner CAX11)
- → 임베디드 DB로 RAM 여유 확보 → wiki-mcp/dashboard 동시 운영

### 3. zero-config
- 설치/설정/마이그레이션 ❌
- 백업 = `cp wiki.db wiki.db.bak` 끝
- gitignore에 한 줄 추가 (`wiki.db`)

### 4. FTS5 내장 (검색)
- [[content/bm25-search]] — BM25 검색에 SQLite FTS5 사용
- PostgreSQL은 `tsvector` + GIN 인덱스 별도 구성
- → SQLite가 검색 통합 더 쉬움

### 5. 이식성
- 파일 1개 → VPS 간 이전이 SCP 한 번
- 로컬에서 빌드 → VPS에 그대로 복사
- disaster recovery 시 10분 안에 클론 ([[_meta/system-design]] §2.5)

## PostgreSQL이 더 나은 경우

| 상황 | 추천 |
|---|---|
| 동시 writer 많음 (multi-user wiki) | PostgreSQL |
| 데이터 10GB+ | PostgreSQL |
| 네트워크로 여러 서버 접근 | PostgreSQL |
| 고급 SQL (CTE 재귀, window 함수 다양) | PostgreSQL |
| **1인 사용자, 수천 페이지** | **SQLite** |

## hybrid search 관점

M3에서 vector 검색 추가 시 ([[SCHEMA]] §AI 로드맵):

| 후보 | 적합도 |
|---|---|
| **SQLite + sqlite-vec** | ✅ 우리 채택 |
| PostgreSQL + pgvector | PostgreSQL 사용 시 |
| Qdrant / Milvus (별도) | 대용량, 운영 부담 |

**sqlite-vec** = SQLite의 vector 검색 확장 (~10MB):
- 같은 `wiki.db` 파일 안에 vector 저장
- 별도 서버/포트 불필요
- BM25 + vector를 한 SQL 쿼리로 hybrid 가능

```sql
-- M3 hybrid 예시 (예정)
SELECT slug, bm25(pages_fts) * 0.7 + vec_distance(embedding, ?) * 0.3 AS score
FROM pages_fts JOIN pages_vec ON ...
WHERE pages_fts MATCH ?
ORDER BY score LIMIT 10;
```

→ PostgreSQL이었다면 pgvector 설치 + GIN 인덱스 + 별도 마이그레이션 필요.

## 트레이드오프 인정

| SQLite의 한계 | 우리 완화 |
|---|---|
| 동시 writer 1개 | curator만 write → 충분 |
| 네트워크 접근 ❌ | MCP가 HTTP 노출 ([[content/mcp-server]]) |
| 대용량 (10GB+) 한계 | 페이지 10k 이상 시 PostgreSQL 이관 옵션 ([[_meta/system-design]] §8 결정 후) |
| 백업 hot-copy 제약 | WAL mode + 백업 시 locking 또는 `VACUUM INTO` |

## 우리 시스템의 위치

```
[wiki-mcp]
    ↓ SQLite query (in-process)
[wiki.db] ←── 파일 (gitignore)
    ↑
[wiki-curator]  ←── git pull / push / build_db.py
    ↓
[GitHub]
```

**핵심**:
- 빌드 산출물 = wiki.db (git 추적 ❌)
- 마크다운 = SoT (git 추적 ✅)
- → 마크다운만 동기화되면 wiki.db는 어디서든 재생성 가능

## PostgreSQL 이관 (M6+ 옵션)

페이지 10k+ 또는 multi-user 추가 시:
- 동일 SQL (대부분 호환)
- `wiki.db` → `pg_dump` 형식 변환 도구 필요
- FTS5 → tsvector 마이그레이션 (schema 다름)

→ M5 시점에 결정.

## 결정 사항

| # | 결정 | 선택 |
|---|---|---|
| D-DB-1 | 백엔드 DB | SQLite |
| D-DB-2 | 검색 | FTS5 (BM25) |
| D-DB-3 | vector (M3) | sqlite-vec |
| D-DB-4 | 마이그레이션 시점 | 페이지 10k+ 시 검토 |
| D-DB-5 | 백업 방식 | gitignore + 일 1회 cron (M5) |

## 관련

- [[content/bm25-search]] — SQLite FTS5 기반 BM25
- [[content/mcp-server]] — SQLite를 쿼리하는 MCP
- [[content/react-spa-architecture]] — SQLite 직접 쿼리하는 UI
- [[_meta/system-design]] — Layer 1 (Data Structure) 설계
- [[scripts/build_db]] — SQLite 빌드 스크립트
