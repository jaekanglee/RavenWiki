# raven v0.7.5 — Dashboard markdown 뷰어 교체 (@uiw/react-md-editor)

> **핵심**: 사용자 (2026-06-30) — "Dashboard에서 만들어진 문서 보는데 1) 너무 조잡함 마크다운 뷰어가 2) 문서내용이 너무 제각각 중구난방임"
>
> Phase A: 마크다운 뷰어 교체. **react-markdown + remark/rehype 스택 청산** → **@uiw/react-md-editor 도입**. (Phase B: 문서 일관성 = 다음 후보)

릴리스 일자: 2026-06-30
이전: v0.7.4 (Tailscale 접속)

---

## 한 줄 요약

Dashboard 마크다운 뷰어를 react-markdown → @uiw/react-md-editor로 교체. 5개 plugin 청산 (remark-gfm, remark-math, rehype-katex, rehype-highlight, unist-util-visit). wikilink는 mdast 트리 변환 → string pre-process로 단순화.

## 1. 변경 사항

### 1-1. `dashboard/package.json` — 의존성 정리

**제거** (5 packages):
- react-markdown ^9.0.0
- remark-gfm ^4.0.0
- remark-math ^6.0.0
- rehype-katex ^7.0.0
- rehype-highlight ^7.0.0
- unist-util-visit ^5.0.0

**추가** (1 package):
- @uiw/react-md-editor ^4.1.1

### 1-2. `dashboard/src/components/MarkdownView.tsx` — 전면 재작성

**Before (v0.7.4)**:
```tsx
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import rehypeHighlight from "rehype-highlight";
import { wikilinkPlugin } from "../lib/wikilink";

export function MarkdownView({ content, vault }: ...) {
    return (
        <article className="prose dark:prose-invert max-w-none">
            <ReactMarkdown
                remarkPlugins={[remarkGfm, remarkMath, wikilinkPlugin(vault)]}
                rehypePlugins={[rehypeKatex, rehypeHighlight]}
            >
                {content}
            </ReactMarkdown>
        </article>
    );
}
```

**After (v0.7.5+)**:
```tsx
import MDEditor from "@uiw/react-md-editor";
import type { FC } from "react";
import { preprocessWikilinks } from "../lib/wikilink";

export const MarkdownView: FC<{...}> = ({ content, vault }) => {
    const processed = preprocessWikilinks(content ?? "", vault);
    return (
        <div className="raven-md-view" data-color-mode="dark">
            <MDEditor.Markdown source={processed} style={{...}} />
        </div>
    );
};
```

→ **6 import → 3 import**. 의존성 6개 → 1개 (모두 청산).

### 1-3. `dashboard/src/lib/wikilink.ts` — pre-process 단순화

**Before**: mdast 트리 변환 (의존성: unist-util-visit). remark plugin으로 주입.
**After**: string → markdown link 단순 변환. 의존성 0.

```ts
// [[slug]] → [slug](/page/{vault}/{slug})
// [[slug!]] → [slug](/page/{vault}/slug?broken=true)
// [[slug?]] → [slug](/page/{vault}/slug?placeholder=true)
// [[slug#heading]] → [slug](/page/{vault}/slug) (anchor v0.7.6+ 후보)
// [[slug|alias]] → [slug](/page/{vault}/slug) (alias dropped)
```

### 1-4. `dashboard/tests/wikilink.test.ts` — 9 tests 재작성

옛 mdast-기반 테스트 (5 tests) → 새 pre-process-기반 테스트 (9 tests):
- simple wikilink → link
- ? placeholder intent
- ! broken intent
- aliased [[slug|alias]]
- anchored [[slug#heading]]
- no-op (no wikilinks)
- URL encoding
- empty content
- multiple wikilinks

## 2. 검증

| 항목 | 결과 |
|---|---|
| dashboard tsc -b --noEmit | ✅ exit 0 |
| dashboard vitest (wikilink) | ✅ 9/9 passed |
| dashboard vite build | ✅ PWA 생성 OK (1.73s) |
| 백엔드 pytest | ✅ 465 passed, 1 skipped (회귀 0) |
| 의존성 | react-markdown/remark/rehype/visit 5개 제거, @uiw/react-md-editor 1개 추가 |

## 3. 의도

사용자 (2026-06-30):
> "Dashboard에서 만들어진 문서 보는데 1) 너무 조잡함 마크다운 뷰어가 2) 문서 내용이 너무 제각각 중구난방임"

**Phase A** (v0.7.5 — 본 릴리스): 마크다운 뷰어 자체 교체 → GitHub Markdown 스타일 자동 + WYSIWYG 토글 가능 + WYSIWYG/Source 모드 (향후)
**Phase B** (v0.7.6+ 후보): 문서 일관성 = Lite bootstrap의 PROJECT-WORKFLOW.md 강화 (BLUF/템플릿 가이드)

→ 옵션 2개 (자체 구현 vs 잘 된 라이브러리) 중 라이브러리 조사 채택 → @uiw/react-md-editor 도입 결정.

## 4. 사용자 옵션 (정리)

| 옵션 | trade-off | 결정 |
|---|---|---|
| A. 자체 구현 | ❌ 비추 (코드량, 버그 가능성) | ❌ |
| B. @uiw/react-md-editor | ✅ 1순위 (WYSIWYG, GitHub 스타일, 활발 유지보수) | ✅ v0.7.5+ |
| C. bytemd | ❌ 차선 (가벼움지만 plugin 적음) | ❌ |
| D. 현재 react-markdown 옵션 강화 | ❌ 차선 (한계) | ❌ |

## 5. 다음 단계

- **v0.7.6 (후보)**: Phase B — Lite bootstrap `PROJECT-WORKFLOW.md`에 BLUF/템플릿 가이드 (문서 일관성). 사용자 vault가 직접 작성하므로 회귀 가드 어려움 → 가이드 강화가 최선.
- **v0.8.0 (후보)**: harumoa 운영자가 만든 페이지 (5phase-workflow, harumoa concept) 검증 + wiki.db 빌드 + lint.

## 6. 호환성

- ✅ **v0.7.4**: 기존 wikilink `[[slug]]` 그대로 동작 (pre-process로 동일 변환)
- ✅ **intent suffix**: `[[x]]!` → `?broken=true`, `[[x]]?` → `?placeholder=true` (URL 파라미터로 보존)
- ✅ **anchor `[[x#h]]`**: v0.7.5에서 anchor 제거 (URL 충돌 방지), v0.7.6+ 별도 후보
- ✅ **alias `[[x|y]]`**: v0.7.5에서 alias 제거, 표시 텍스트 = slug (v0.7.6+ 후보)
- ✅ **Lite bootstrap 4종**: 영향 ❌ (사용자 vault 데이터)
- ⚠️ **react-markdown 의존 코드**: dashboard/src 전체 grep 결과 0건 (MarkdownView.tsx만 사용) — 청산 안전