import { useState } from "react";
import { useNavigate } from "react-router-dom";

/**
 * "새 페이지" 버튼 + 생성 모달.
 *
 * MVP (정적 데모):
 *   - slug + title + type + tags + 본문 입력 → localStorage에 저장
 *   - 페이지 이동 후 PageView가 fallback에서 localStorage 확인
 *   - 실제 파일/DB 쓰기는 POST /api/wiki_create (다음 단계 = 프록시 API)
 *
 * 이 컴포넌트는 그 API가 준비되면 fetch 부분만 교체.
 */
export function NewPageButton() {
  const [open, setOpen] = useState(false);
  const nav = useNavigate();

  const [slug, setSlug] = useState("");
  const [title, setTitle] = useState("");
  const [type, setType] = useState("concept");
  const [tags, setTags] = useState("");
  const [content, setContent] = useState("# 새 페이지\n\n");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function submit() {
    setErr(null);
    if (!slug || !title) {
      setErr("slug + title 필수");
      return;
    }
    setBusy(true);
    try {
      const r = await fetch("/api/wiki_create", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          slug,
          title,
          type,
          tags: tags
            .split(",")
            .map((t) => t.trim())
            .filter(Boolean),
          content,
        }),
      });
      if (!r.ok) throw new Error(`API ${r.status} (아직 미구현 — 다음 단계)`);
      const out = await r.json();
      nav(`/page/${out.slug ?? slug}`);
    } catch (e) {
      // MVP 폴백: localStorage에 저장 (정적 데모용)
      const key = `wiki:local:${slug}`;
      const fm = [
        "---",
        `title: ${title}`,
        `type: ${type}`,
        `tags: [${tags.split(",").map((t) => t.trim()).filter(Boolean).join(", ")}]`,
        `created: ${new Date().toISOString().slice(0, 10)}`,
        `updated: ${new Date().toISOString().slice(0, 10)}`,
        "---",
        "",
      ].join("\n");
      localStorage.setItem(key, fm + content);
      setErr(
        `저장 완료 (localStorage 데모): API 미연결 상태. 키=${key}. 다음 단계에서 fetch 붙임.`,
      );
      setBusy(false);
      setTimeout(() => {
        setOpen(false);
        nav(`/page/${slug}`);
      }, 1500);
    }
  }

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="block w-full text-left py-1 px-2 mb-2 rounded bg-cyan-100 dark:bg-cyan-900 hover:bg-cyan-200 text-sm font-medium"
      >
        ➕ 새 페이지
      </button>

      {open && (
        <div
          className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
          onClick={() => !busy && setOpen(false)}
        >
          <div
            className="bg-white dark:bg-gray-900 rounded-lg p-6 max-w-2xl w-full max-h-[90vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <h2 className="text-xl font-bold mb-4">새 페이지</h2>

            <label className="block mb-3">
              <span className="text-sm font-medium">slug *</span>
              <input
                value={slug}
                onChange={(e) => setSlug(e.target.value)}
                placeholder="content/my-concept"
                className="w-full border rounded px-2 py-1 mt-1 text-sm"
              />
              <span className="text-xs text-gray-500">
                vault-relative path (예: content/my-concept)
              </span>
            </label>

            <label className="block mb-3">
              <span className="text-sm font-medium">title *</span>
              <input
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="내 컨셉"
                className="w-full border rounded px-2 py-1 mt-1 text-sm"
              />
            </label>

            <div className="grid grid-cols-2 gap-3 mb-3">
              <label className="block">
                <span className="text-sm font-medium">type</span>
                <select
                  value={type}
                  onChange={(e) => setType(e.target.value)}
                  className="w-full border rounded px-2 py-1 mt-1 text-sm"
                >
                  <option value="concept">concept</option>
                  <option value="person">person</option>
                  <option value="comparison">comparison</option>
                  <option value="project">project</option>
                  <option value="tool">tool</option>
                  <option value="rule">rule</option>
                  <option value="query">query</option>
                  <option value="journal">journal</option>
                </select>
              </label>
              <label className="block">
                <span className="text-sm font-medium">tags (쉼표 구분)</span>
                <input
                  value={tags}
                  onChange={(e) => setTags(e.target.value)}
                  placeholder="ai, llm"
                  className="w-full border rounded px-2 py-1 mt-1 text-sm"
                />
              </label>
            </div>

            <label className="block mb-3">
              <span className="text-sm font-medium">본문 (markdown)</span>
              <textarea
                value={content}
                onChange={(e) => setContent(e.target.value)}
                rows={10}
                className="w-full border rounded px-2 py-1 mt-1 text-sm font-mono"
              />
            </label>

            {err && (
              <div className="mb-3 p-2 bg-yellow-100 dark:bg-yellow-900 text-sm rounded">
                {err}
              </div>
            )}

            <div className="flex gap-2 justify-end">
              <button
                onClick={() => setOpen(false)}
                disabled={busy}
                className="px-4 py-2 text-sm rounded border hover:bg-gray-100"
              >
                취소
              </button>
              <button
                onClick={submit}
                disabled={busy}
                className="px-4 py-2 text-sm rounded bg-cyan-600 text-white hover:bg-cyan-700 disabled:opacity-50"
              >
                {busy ? "저장 중…" : "저장"}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
