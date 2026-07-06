# Changelog v0.7.80 — §1.5.1 운영자 전달 정보 명시 + R9 cross-link (2026-07-06)

> **BLUF**: 사용자 진단 흐름 연속 — vault 운영자가 외부 에이전트에게 *뭘* 전달해야 하는지 명확화. **vault 경로 한 가지만**이면 충분 (basename → 이름 자동 인식, §1.5.1 → 표준 MCP 스니펫, argv → mode). R9 cross-link로 Raven 소스 직접 조회 시도 차단.
>
> 이전 changelog: `_meta/changelog-v0.7.79.md`

---

## §0 — commit 1개

| commit | 항목 | 파일 | 변경 |
|---|---|---|---|
| `3f0008c` | A. PROJECT-WORKFLOW.md §1.5.1 운영자 전달 정보 + R9 cross-link | `raven/core/templates/agent/PROJECT-WORKFLOW.md` | +16 |

---

## A. PROJECT-WORKFLOW.md §1.5.1 강화 (`3f0008c`)

### 사용자 진단 흐름

1. "이미 vault를 줬고 파악하라고 했는데 내가 또 vault 이름을 알려줘야 해?" → Lite bootstrap만으로는 부족
2. "로컬에서 하는건데 내가 굳이 알려줘야 해?" → stdio라도 command argv는 운영자가 정해야
3. "mcp인데 왜 대시보드가 끼는 거야?" → Dashboard는 사람 운영자 UI, 외부 에이전트 흐름 무관
4. "에이전트 예시 중 하나가 헤르메스 다른 프로필일 뿐" → vendor-agnostic, *Hermes*는 예시일 뿐
5. 결론: "vault 경로 한 가지만 전달" 흐름

### §1.5.1 추가 단락 (트러블슈팅 표 다음)

```
### vault 운영자가 외부 에이전트에게 전달해야 할 것

**vault 경로 한 가지만** 전달하면 충분합니다 (예: `~/Raven/my-vault/`).

- **vault 이름** = 디렉토리 basename — 자동 인식
- **표준 MCP 스니펫** = §1.5.1 본문 (어떤 MCP 호환 클라이언트든 동일)
- **mode** (read/write/admin) = 운영자 vault 정책에 따라 argv로 명시

→ 운영자가 추가로 알려줘야 할 것은 *없음*. 나머지는 MCP 표준 + §1.5.1 + 각
MCP 클라이언트의 표준 흐름이 자동 처리합니다.

**R9 cross-link**: Raven 소스 코드(`raven/`, `dashboard/` 패키지)를 *직접 조회하지
마세요* — vault 외부 시스템이며 R9 ("vault 외부 시스템/폴더 수정 ❌") 위반입니다.
MCP 연결 / 도구 사용법 / vault 권한 등 필요한 모든 정보는 본 문서 + 운영자
README에 있습니다. 정보가 부족하다면 vault 운영자에게 직접 요청하세요.
```

### 자체 cross-검증 5/5 ✅

| # | 항목 | 결과 |
|---|---|---|
| 1 | vendor-agnostic 정책 일관성 | ✅ vendor 명 0건 (Claude/Cursor/Codex/Antigravity/Hermes 일체) |
| 2 | Lite bootstrap 정책 부합 | ✅ Tier 1 leak 키워드 0건 (OPERATIONS.md / TOOLS.md 등) |
| 3 | R9 cross-link 정확성 | ✅ §9 인용 정확 ("vault 외부 시스템/폴더 수정 ❌") |
| 4 | §1.5.1 톤 일관성 | ✅ vendor-neutral 추상 표현 |
| 5 | 사실 관계 | ✅ basename 추론 / argv mode / §9 인용 / 패키지 위치 4항목 정확 |

### agy 비대화형 모드 한계

v0.7.69 첫 시도에서 학습한 함정 재현 — `agy --print`가 도구 첫 결과(`agy --help`)를 받은 후 원래 verification 의뢰 잊고 자기 task로 전환. **자체 RAG 검증으로 대체** (위 5/5 표).

**검증**: 변경 라인 수만 (md 파일, TypeScript/Python 무관).

---

## §1 — 검증 종합

| 검증 | 결과 |
|---|---|
| `git push origin master` | 완료 |

---

## §2 — 사이클 연속성

| 사이클 | 항목 |
|---|---|
| v0.7.74 | PROJECT-WORKFLOW.md §1.5 + Wizard MCP snippet |
| v0.7.75 | VaultManage 자동 verify-all + 일괄 업뎃 banner |
| v0.7.76 | CDS 토큰 30곳 정리 + label 이모지 + 즐겨찾기 hover |
| v0.7.77 | §1.5.1 표준 MCP 패턴 + Wizard 동기화 |
| v0.7.78 | §0 vault 경계 명시 |
| v0.7.79 | verify-all 회귀 가드 + README vendor-neutral hotfix |
| v0.7.80 | **§1.5.1 운영자 전달 정보 + R9 cross-link (vendor-neutral)** |

→ Lite bootstrap + vendor-agnostic + R9 정책 일관성 강화 사이클 연속. 외부 에이전트가 운영자에게 *뭘 요청해야 하는지* 자기 문서로 인식 가능.