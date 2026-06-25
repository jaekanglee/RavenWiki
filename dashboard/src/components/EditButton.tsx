import { useState } from "react";
import { useNavigate } from "react-router-dom";

/**
 * "편집" 버튼 → textarea 모달 → POST /api/wiki_update
 *
 * MVP: API 미구현 시 localStorage fallback (정적 데모).
 *   → fetch URL 교체만으로 백엔드 연결됨.
 */
export function EditButton({ page }: { page: { slug: string; content: string } }) {
  const [open, setOpen] = useState(false);
  const [body, setBody] = useState(page.content);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const nav = useNavigate();

  async function save() {
    setBusy(true);
    setMsg(null);
    try {
      const r = await fetch("/api/wiki_update", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ slug: page.slug, content: body }),
      });
      if (!r.ok) throw new Error(`API ${r.status}`);
      setMsg("✅ 저장 완료");
      setTimeout(() => {
        setOpen(false);
        nav(`/page/${page.slug}`);
        window.location.reload(); // 정적 JSON 캐시 갱신
      }, 800);
    } catch {
      // MVP 폴백
      const key = `wiki:local:${page.slug}`;
      localStorage.setItem(key, body);
      setMsg(
        `저장 완료 (localStorage 데모): API 미연결. 키=${key}. 다음 단계에서 fetch 붙임.`,
      );
      setBusy(false);
      setTimeout(() => {
        setOpen(false);
        nav(`/page/${page.slug}`);
      }, 1500);
    }
  }

  return (
    <>
      <button
        onClick={() => {
          setBody(page.content);
          setOpen(true);
        }}
        className="text-sm px-3 py-1 rounded border hover:bg-gray-100 dark:hover:bg-gray-800"
      >
        ✏️ 편집
      </button>

      {open && (
        <div
          className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
          onClick={() => !busy && setOpen(false)}
        >
          <div
            className="bg-white dark:bg-gray-900 rounded-lg p-6 max-w-4xl w-full max-h-[90vh] flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            <h2 className="text-xl font-bold mb-2">편집: {page.slug}</h2>
            <textarea
              value={body}
              onChange={(e) => setBody(e.target.value)}
              className="flex-1 border rounded px-3 py-2 text-sm font-mono min-h-[400px]"
            />
            {msg && (
              <div className="mt-2 p-2 bg-yellow-100 dark:bg-yellow-900 text-sm rounded">
                {msg}
              </div>
            )}
            <div className="flex gap-2 justify-end mt-3">
              <button
                onClick={() => setOpen(false)}
                disabled={busy}
                className="px-4 py-2 text-sm rounded border hover:bg-gray-100"
              >
                취소
              </button>
              <button
                onClick={save}
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
