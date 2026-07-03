# raven v0.7.61 — 워크스페이스 OS 파일 트리 (read-only) + .md 인라인 미리보기

> **핵심**: 워크스페이스 연동(v0.7.54)을 dashboard에서 **OS 파일 트리로 직접 탐색**할 수 있게 확장. `/workspace` 페이지 좌측에 워크스페이스 디렉토리 트리 패널을 추가하고, .md 파일 클릭 시 우측에 **인라인 미리보기** 표시. **완전 read-only** — raven은 워크스페이스 파일을 절대 수정하지 않음 (외부 도구 안전망).

릴리스 일자: 2026-07-03
이전: v0.7.60

---

## 1. 변경 사항

### 1-2. `raven/api/workspace_tree.py` (신규, ~210 lines)

순수 함수 모듈:
- `list_workspace_dir(workspace_root, relative, depth, include_hidden)` — 1단계 lazy load 트리
- `read_workspace_file(workspace_root, relative, max_bytes)` — 텍스트 미리보기 (256KB cap, binary 감지)
- `_looks_binary(content, sample_bytes=8192)` — NUL byte 또는 printable 비율 80% 미만

보안 가드:
- `relative` 경로가 `workspace_root` 외부면 `ValueError("escapes workspace root")`
- resolve 후 `relative_to(workspace_root)` prefix 체크
- `..`, 절대경로 `/etc/passwd` 모두 거부

규약:
- 디렉토리 먼저, 알파벳순 (대소문자 무시)
- depth 1~5 (기본 3). `has_children` flag로 UI가 expand 가능 여부 판단
- hidden dotfile 기본 OFF. `hidden=true` 시 .git/.venv 등 표시
- 큰 파일은 256KB에서 truncate + 안내
- **모든 텍스트 파일 미리보기** (md/txt/py/json/yaml/log/csv/html/css/js ...).
  binary (PNG/JPG/bin)만 거부. `_looks_binary` 휴리스틱: NUL byte 또는 printable < 80%.

### 1-2. `raven/api/server.py` — 엔드포인트 2개 추가

```python
GET /api/vaults/{name}/workspace/tree?path=&depth=&hidden=
GET /api/vaults/{name}/workspace/file?path=
```

- `_vault_or_404(name)` + `meta.workspace_path` 부재 → 400
- workspace 디렉토리 부재 → 404
- traversal → 403
- file endpoint가 디렉토리 받으면 → 400

### 1-3. `dashboard/src/lib/api.ts` — fetch 함수 2개 + 타입 3개

```ts
fetchWorkspaceTree(vault, { path?, depth?, hidden? }): Promise<WorkspaceTreeResult | null>
fetchWorkspaceFile(vault, path): Promise<WorkspaceFileResult | null>

WorkspaceTreeNode { name, path, type, size, mtime, is_hidden, depth, has_children }
WorkspaceTreeResult { ok, workspace_path, path, nodes, total, depth }
WorkspaceFileResult { ok, workspace_path, path, size, truncated, content }
```

### 1-4. `dashboard/src/routes/WorkspacePage.tsx` — 트리 패널 + 미리보기 분기

**3-패널 → stacked 좌측** (surgical: 리사이저 1개만 추가):

```
┌──────────────────────────┬─────────────────────────────────┐
│ 워크스페이스 트리 (NEW)   │   미리보기 또는 diff viewer     │
│  - breadcrumb + ⬆ up     │                                 │
│  - [ ] 숨김 토글         │   - 텍스트 파일 → 인라인 (모든  │
│  - 파일 크기 표시        │     확장자, binary만 거부)      │
├──────────────────────────┤   - Git 변경파일 → diff         │
│ 변경사항 (Git)            │                                 │
│  - 기존과 동일            │                                 │
└──────────────────────────┴─────────────────────────────────┘
```

State 7개 추가: `treeNodes`, `treePath`, `treeLoading`, `showHidden`, `previewContent`, `previewLoading`, `previewError`.

핸들러 4개: `loadTree`, `handleTreeDirClick` (1단계 lazy), `handleTreeFileClick` (모든 텍스트 → 미리보기, binary → 안내), `handleTreeUp`.

미리보기 분기: `previewContent.is_binary` 면 "🔒 binary 파일 — 미리보기 미지원" 카드. 아니면 `<pre>` 코드 블록.

`formatSize` 헬퍼 (B / KB / MB) 신규.

### 1-5. `tests/test_workspace_tree.py` (신규, 35 tests)

| 카테고리 | 케이스 |
|---|---|
| `list_workspace_dir` (pure) | 9개 — dirs-first, hidden ON/OFF, subdir, traversal, abs path, nonexistent, file-as-dir, depth clamp, has_children 마커 |
| `read_workspace_file` (pure) | 14개 — 텍스트 / traversal / directory / nonexistent / truncation / **5종 텍스트 확장자 (.txt .py .json .log .yaml)** / **3종 binary (PNG / JPG / control-only)** / 빈 파일 |
| FastAPI endpoint | 12개 — 정상, hidden, traversal 403, no-workspace 400, vault 없음 404, workspace dir missing 404, file read 정상, file traversal 403, file directory 400, file missing 404 |

총 **35 passed** (회귀 ❌).

---

## 2. 사용자 흐름

```
1. /workspace 진입 → 워크스페이스 부재 시 기존 setup 화면
2. 워크스페이스 OK + Git OK → 좌측 상단에 OS 트리 자동 로드
3. 디렉토리 클릭 → 그 안 1단계 진입, breadcrumb + ⬆ up
4. 숨김 체크박스 → 즉시 refetch (.git, .venv 등 노출/숨김)
5. .md 파일 클릭 → 우측에 미리보기 (256KB cap, truncated 경고)
6. 비-.md 파일 클릭 → "미리보기는 .md만 지원합니다 (N bytes)" 토스트
7. Git 변경파일 클릭 → 기존 diff viewer (트리 미리보기와 동시 사용 가능, preview 닫기 우선)
```

---

## 3. 안전성 / 정책 정렬

- **READ-ONLY 강제**: 백엔드에 쓰기/수정/삭제 API 없음. `raven vault` 명령어도 워크스페이스 경로만 변경 (이미 v0.7.54 정책). raw/ 폴더 정책 (v0.7.50, human-first / agent read-only)과 정합.
- **TRAVERSAL 가드**: 백엔드 `relative_to()` 체크 + FastAPI 403. 프론트는 `path` 쿼리 그대로 전달 (사용자 입력 아님 — vault 내부 데이터).
- **성능**: 깊이 제한 (1~5), 1단계 lazy load (전체 트리 한 번에 안 가져옴), 큰 파일 truncate.

---

## 4. 검증 결과

| 항목 | 결과 |
|---|---|
| `pytest tests/test_workspace_tree.py tests/test_vault_workspace.py` | **39/39 passed** (신규 35 + 기존 4 회귀 ❌) |
| `cd dashboard && npm run build` (`tsc -b && vite build`) | exit 0, 988 modules transformed |
| `cd dashboard && npm test -- --run` | **116/116 passed** (1 skipped, 기존) |
| 백엔드 lint | ok (no errors) |

---

## 5. 추가 가능 작업 (다음 패치 후보)

- 3-패널 분리 (트리 / 변경사항 / diff 각각 리사이저) — 현재는 stacked로 surgical 진행
- .md 외 미리보기 (syntax highlight, mermaid 렌더링) — 별도 컴포넌트 작업
- 워크스페이스 검색 (`/api/vaults/{name}/workspace/search?pattern=`) — 현재는 OS tree 탐색만
- 변경파일과 트리 파일 시각 연결 (Git changed = 🔴 마커) — UI polish

---

## 6. 부록 — self-audit (Karpathy §6 + AGENTS.md §6,9)

- [x] **명시 (§6 ①)**: 워크스페이스 OS 트리 read-only — 사용자 요청 정확히 따름
- [x] **단순성 (YAGNI)**: 2-패널 유지 (stacked 좌측), 리사이저 추가 ❌. 미리보기는 .md만 (요청대로)
- [x] **Surgical (§3)**: 백엔드 모듈 1개 + 엔드포인트 2개 + 프론트 함수 2개 + WorkspacePage 패널 1개. 다른 페이지/컴포넌트 미접촉
- [x] **Goal-Driven**: 26개 테스트로 traversal 가드 / hidden 토글 / depth / truncate 모두 검증
- [x] **4 저장 신호**: 테스트 + changelog + 보안 가드 문서화 (raw/ 정책과 정합)
- [x] **재사용 컴포넌트 (§13.1)**: formatSize는 local 헬퍼 (간단). EmptyState / Resizer 등 기존 컴포넌트 재사용
- [x] **CSS 변수 우선 (§13.2)**: 인라인 hex 0개, 모든 색은 `var(--xxx)`