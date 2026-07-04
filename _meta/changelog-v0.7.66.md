# Changelog v0.7.66 — 제품 평가 기반 P0/P1 보완 (2026-07-04)

> **BLUF**: 제품 전수 평가(6축, 실행 검증)에서 나온 백로그 24건 중 P0 3건 + P1 11건을
> 수정. "성공이라고 말하면서 실패하는" silent failure 3곳 제거, 에이전트 지식 누적
> 루프 개통, 새 vault lint 노이즈 8W → 0W.

평가 문서: `docs/evaluations/2026-07-04-raven-product-evaluation.md` (기준/채점표/백로그 전체)

---

## P0 — 데이터 위험 / 핵심 루프

1. **export 수리** (`scripts/export_static.py`, `raven/cli/__main__.py`)
   - `__main__`이 argv를 무시하고 저장소 루트를 vault로 간주 + 실패해도 exit 0
     → 모든 실제 vault의 `raven export`가 성공으로 위장된 채 아무것도 쓰지 않았음.
   - argparse 도입, `out_dir` 파라미터 신설, DB 부재 시 exit 1, CLI 실패 사유 표시.

2. **wiki_update upsert** (`raven/mcp/tools/write.py`, `raven/mcp/cli.py`)
   - 기존: 신규 slug 거부 + "Use wiki_ingest for new pages" 안내 — 그러나 wiki_ingest는
     raw/ 전용 + 사람 명시 명령 필수(ADR-2026-07-02)라 **에이전트가 새 노트를 만들
     MCP 경로가 없었음** (North Star의 "compounding knowledge" 루프 차단).
   - 신규 slug 생성 허용. LLM Wiki vault에선 9종 type 스키마 가드 통과가 생성 조건.
     raw/, _meta/, log.md는 기존 immutable 가드가 계속 차단.

3. **frontmatter 오염 방어** (`raven/mcp/tools/write.py`)
   - 에이전트가 frontmatter 포함 전체 md 문서를 content로 보내면, 검증은 기존 메타로
     통과시키고 블록을 본문에 이중 기록(SoT 조용히 오염)했음.
   - content 선두 `---` 블록을 메타로 승격 (우선순위: frontmatter 파라미터 > 임베디드 >
     기존 파일). 임베디드 불량 type도 이제 검증에 걸림.

## P1 — 일상 마찰

- **lint #11 `log` 영구 오탐 제거** — log.md는 페이지가 아니라 인프라. index_builder
  카탈로그에서도 동일 기준으로 제외.
- **build 1회 수렴** — index.md/_index/* 생성 시 같은 build 안에서 재색인
  (`index_builder.build_index`가 변경 여부 반환, `db.build_db`가 조건부 재빌드).
  이전엔 두 번 빌드해야 #11이 사라졌음.
- **`_core_tags()` 부활** — 옛 경로(`_meta/SCHEMA.md`, 존재한 적 없음) →
  `_meta/agents/SCHEMA.md`. 섹션 헤더 파싱을 실제 템플릿(`### Core (...)`)에 맞춤,
  한글 태그 승격 지원. **vault SCHEMA.md core 목록 추가가 이제 실제로 동작.**
- **core taxonomy에 `index`, `home` 추가** — build가 만드는 index 페이지가 자기
  자신에게 #9 경고를 내던 self-noise 제거 (fallback + 템플릿 동기화).
- **`archive restore`가 원래 slug 수용** — 여러 벌이면 최신본 복원.
- **검색에서 자동 카탈로그 제외** — `content/index`, `content/_index/*`가 모든
  제목·요약을 복제해 실제 노트를 밀어냈음 (API 검색 + MCP FTS 모두).
- **garden DB 신선도 감지** (`garden.db_is_stale`) — 낡은 wiki.db 기준 "정리 대상
  없음" 거짓 안심 방지, CLI 진입 시 경고.
- **PROJECT-WORKFLOW 템플릿 보강** — wiki_update 사용 규약(§1), §7.5 큐레이션 기본
  점검(조치 수준 명시: 수리 가능/발의만/사람 전용), 경계 선언의 garden/curator
  오안내 정직화.
- **watchfiles 의존성 명시** — 클린 체크아웃에서 테스트 스위트 red였던 원인.

## 검증

- 전체 테스트 **599 passed** (기존 578 + 신규 회귀 가드 21, watcher 5 포함 복구)
- E2E: 새 vault + 페이지 1개 → lint **0C / 0W / 4I** (이전: build 2회 후에도 8W)
- MCP 실주행: 에이전트 신규 노트 생성 성공, 불량 type 거부, 이중 frontmatter 없음

## 남은 백로그

P2 9건 (평가 문서 §5 참조): CLI search 추가, #9 severity 재고, 모순 처리 절차 1줄,
draft 태그 연결, 태그 승격 issue 경로, aliases/분할 안내, 승격 추천 구현 여부 결정,
curator 문서 정합, #13 이중 보고 정리. 추가 발견: `_index/*`의 `type: index`가
9종 taxonomy 외 (시스템 자기모순 — 결정 필요).
