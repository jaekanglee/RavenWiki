---
adr_id: adr-2026-06-29-folder-first-class
title: 폴더를 1차 시민으로 승격 — OS 파일시스템을 source of truth
status: proposed
created: 2026-06-29
deciders: wiki-orchestrator (제안) · user (검토 게이트)
related:
  - AGENTS.md §6 (verify-in-loop)
  - AGENTS.md §10 ("사용자 vault 데이터 write ❌" 의도와 충돌하지 않도록 — 이 ADR은 "사용자가 만들 폴더를 1차 시민으로 인정"하자는 것이지, Raven이 사용자 vault에 임의로 파일을 만드는 것은 아님)
  - dashboard/src/components/Layout.tsx (현재 fetchPages → slug split 트리 빌드)
  - dashboard/src/components/Sidebar.tsx (현재 page leaf만 표시)
  - raven/api/server.py:296 (GET /api/vaults/<name>/pages — page only)
  - raven/api/server.py:1153 (POST /api/vaults/<name>/pages — page only)
---

# ADR: 폴더를 1차 시민으로 승격 — OS 파일시스템을 SOT로

## Context (배경)

### 문제

지금 Raven의 폴더는 **page slug의 부산물**임.

- `POST /pages`가 `content/concept/users` slug로 페이지를 만들면, 그제서야 `content/concept/` 폴더가 파일시스템에 생김
- **빈 폴더는 sidebar에서 안 보임** (page가 slug로 폴더를 만들 때만 등장)
- **사용자가 의도적으로 폴더를 만들 길이 없음** — 페이지 slug 우회만 가능
- 폴더 자체에 rename/move/delete 액션 없음

이건 Obsidian/Notion/Craft의 mental model과 어긋남. 사용자 원문 피드백 (2026-06-29):

> "몇 뎁스던 폴더 안에 폴더 만들 수 있어야 하는 거 아니냐고, 자유롭게"
> "Obsidian은 구조를 정의해놓는 게 아니라, 파서처럼 자유로운 폴더를 파싱하는 것일 것 같은데"

### 거부한 대안

| 안 | 요약 | 거부 이유 |
|---|---|---|
| A. placeholder 동반 | 폴더 만들면 그 안에 placeholder 페이지도 같이 생성 | 사용자가 원하지 않는 파일이 vault에 생김. "Raven이 사용자 vault에 아무것도 안 만들수록 라이트" 원칙 위반 |
| B. manifest (`_meta/folders.yaml`) | 폴더 목록을 별도 YAML로 관리 | OS와 manifest 이중 SOT. 동기화 부채. Obsidian 방식이 아님 |
| C. wiki.db folders 테이블 | DB에 폴더 트리 저장 | DB는 cache/index이지 SOT가 아님. 위와 같은 이중 SOT 문제 |

### Obsidian이 실제로 하는 방식 (정확히)

1. vault root를 스캔
2. 폴더 발견 → 안에 `.md` 파일 발견 → tree 구성
3. 폴더에 `.md`가 0개여도 폴더 자체는 표시
4. 사용자가 OS 파일시스템에서 폴더 만들면 Obsidian이 그걸 그대로 읽음
5. 폴더 메타데이터 저장 안 함

## Decision (결정)

**폴더를 1차 시민으로 승격하고, OS 파일시스템을 source of truth로 한다.**

### 1) 데이터 모델

- **폴더 = OS 디렉토리**. metadata 저장 ❌
- **페이지 = `.md` 파일**. 기존 그대로
- **Tree = `os.walk` 결과**. 빈 폴더도 `children: []` 으로 포함

### 2) 새 API

```python
GET  /api/vaults/<name>/tree
POST /api/vaults/<name>/folders
```

`GET /tree`:
- `os.walk` 기반 트리 빌더
- `.md` 파일은 page, 디렉토리는 folder
- 빈 폴더도 반환 (Raven 시스템 폴더 `_meta/`, `_archive/` 제외)
- 응답 shape: `{type: "dir" | "page", path, slug?, title?, pageType?, children?}`
- 기존 `GET /pages` 호환 유지 (다른 endpoint에서 사용 중)

`POST /folders`:
- payload: `{path: "content/users/admin"}`
- `_safe_folder_or_400(path)` 검증 → `mkdir(parents=True, exist_ok=False)`
- 충돌 시 409
- 부수 파일 생성 ❌ (placeholder, README, .folder_meta 등 일체 안 만듦)

### 3) Sidebar / Layout 변경

- `Layout.tsx`: `fetchPages` 제거 → `fetchTree` 사용
- `Sidebar.tsx`: 빈 폴더도 그대로 렌더. 폴더 row 우측 `＋` → "페이지" / "폴더" 메뉴
- `flattenCommonRoot()` 유지 (`content/` 단일 child 압축은 UX 개선으로 보존)

### 4) types.ts

```ts
export interface TreeNode {
  type: "dir" | "page";
  path: string;          // vault-relative
  slug?: string;         // page only — `/page/<vault>/<slug>` URL
  title?: string;        // page only
  pageType?: string;     // page only
  children?: TreeNode[];
}
```

### 5) 신규 컴포넌트

`dashboard/src/components/NewFolderButton.tsx`:
- 폴더 모달 (페이지 모달과 분리)
- 입력: 폴더 경로 1개 (`content/users/admin/`, 슬래시로 끝나도 OK)
- 동작: `POST /folders` → 성공 시 `nav("/page/<vault>/<path>")` 없이 refresh만

## Consequences (영향)

### 가드

1. **Raven이 사용자 vault에 만드는 부수 파일 0개** — 이 원칙 검증: 이번 변경이 만들어내는 vault 내 파일은 **사용자가 명시 요청한 디렉토리 1개**뿐
2. **마이그레이션 코드 0줄** — 기존 vault의 OS 디렉토리는 그대로, 새 tree 빌더가 그대로 읽음. 빈 폴더가 sidebar에 새로 보이기만 함
3. **depth 무제한** — path 문자열 검증만, 트리 빌드 재귀 그대로
4. **충돌 처리** — page와 folder가 같은 path를 가질 수 없음. page 우선, folder 생성 시 409

### 후속 (이번 ADR 범위 외)

- `PATCH /folders/<path>` (rename)
- `DELETE /folders/<path>` (cascade archive 옵션)
- Sidebar 폴더 hover 메뉴 (rename/move/delete)
- Graph 옵션: 폴더를 노드로 포함 (cluster view)

## Verification

- `pytest tests/test_api.py` — tree 빌더 (빈 폴더 포함), folder mkdir (depth 5 정상), 충돌 409
- `vitest run` — Sidebar 빈 폴더 표시, folder ＋ 메뉴
- browser smoke — 폴더 생성 후 sidebar 반영

## References

- Obsidian File explorer: <https://help.obsidian.md/Plugins/File+explorer>
- 사용자 피드백: 2026-06-29 ("원하는 만큼 폴더링")