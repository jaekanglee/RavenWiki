/**
 * v0.7.5+ — wikilink pre-processor (string → markdown link).
 *
 * Before (v0.7.4 이전):
 *   - remark plugin으로 mdast 트리 변환 (의존성: unist-util-visit)
 *   - react-markdown remarkPlugins로 주입
 *
 * After (v0.7.5+):
 *   - Pre-process: `[[slug]]` → `[slug](/page/{vault}/{slug})` 문자열 치환
 *   - @uiw/react-md-editor는 raw markdown source → 즉시 렌더링
 *   - 의존성 0 (TypeScript 표준)
 *
 * Wikilink intent suffix 보존:
 *   - `[[x]]`   → `/page/{vault}/x` (정상)
 *   - `[[x]]!`  → `/page/{vault}/x?broken=true` (broken intent)
 *   - `[[x]]?`  → `/page/{vault}/x?placeholder=true` (placeholder)
 */
export function preprocessWikilinks(content: string, vault: string): string {
    if (!content) return "";
    // `[[slug]]` 또는 `[[slug#heading]]` 또는 `[[slug|alias]]` 패턴
    // trailing suffix: `!` (broken) / `?` (placeholder) — 0 또는 1개
    // slug 자체에는 |, #, ], !, ? 가 들어갈 수 없다고 가정 (wikilink intent와 충돌 방지)
    const regex = /\[\[([^\]|#!?]+)(?:#[^\]|]+)?(?:\|[^\]]+)?(!|\?)?\]\]/g;
    return content.replace(regex, (_match, slug, suffix) => {
        let url = `/page/${encodeURIComponent(vault)}/${encodeURIComponent(slug)}`;
        if (suffix === "!") url += "?broken=true";
        if (suffix === "?") url += "?placeholder=true";
        // 표시 텍스트는 slug 그대로 (사용자가 alias 명시 시 그 텍스트 보이게 가능, v0.7.6+ 후보)
        return `[${slug}](${url})`;
    });
}

/**
 * v0.7.4 이전 wikilinkPlugin 함수 호환 stub.
 * 더 이상 mdast 변환 안 함. pre-process로 대체됨.
 * 기존 import 위치에서 호출되어도 no-op.
 */
export function wikilinkPlugin(_vault: string): () => void {
    return () => {
        /* no-op: replaced by preprocessWikilinks() in v0.7.5+ */
    };
}