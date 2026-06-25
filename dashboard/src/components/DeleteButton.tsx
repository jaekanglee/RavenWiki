import { useState } from "react";
import { useNavigate } from "react-router-dom";

/**
 * "삭제" 버튼 → 확인 모달 → POST /api/wiki_delete
 *
 * MVP: API 미구현 시 localStorage 정리 + 이동 (정적 데모).
 *   실제 환경에서는 _archive/<slug>-<timestamp>.md로 백업됨.
 */
export function DeleteButton({ slug }: { slug: string }) {
  const [open, setOpen] = useState(false);
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const nav = useNavigate();

  async function del() {
    if (confirm !== slug) {
      setMsg(`확인: "${slug}" 정확히 입력`);
      return;
    }
    setBusy(true);
    setMsg(null);
    try {
      const r = await fetch("/api/wiki_delete", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ slug }),
      });
      if (!r.ok) throw new Error(`API ${r.status}`);
      setMsg("✅ 삭제 완료");
      setTimeout(() => nav("/"), 800);
    } catch {
      // MVP 폴백
      localStorage.removeItem(`wiki:local:${slug}`);
      setMsg(
        "삭제 표시 완료 (localStorage 데모): API 미연결. 다음 단계에서 fetch 붙임.",
      );
      setBusy(false);
      setTimeout(() => nav("/"), 1500);
    }
  }

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="text-sm px-3 py-1 rounded border border-red-300 text-red-700 hover:bg-red-50 dark:hover:bg-red-950"
      >
        🗑 삭제
      </button>

      {open && (
        <div
          className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
          onClick={() => !busy && setOpen(false)}
        >
          <div
            className="bg-white dark:bg-gray-900 rounded-lg p-6 max-w-md w-full"
            onClick={(e) => e.stopPropagation()}
          >
            <h2 className="text-xl font-bold mb-2 text-red-700">페이지 삭제</h2>
            <p className="text-sm mb-3">
              <code className="bg-gray-100 dark:bg-gray-800 px-1 rounded">
                {slug}
              </code>
              을(를) 삭제합니다. 백엔드 연결 시{" "}
              <code>_archive/</code>로 백업 후 DB 재빌드.
            </p>
            <label className="block mb-3">
              <span className="text-sm font-medium">확인 — slug 입력</span>
              <input
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                placeholder={slug}
                className="w-full border rounded px-2 py-1 mt-1 text-sm font-mono"
              />
            </label>
            {msg && (
              <div className="mb-3 p-2 bg-yellow-100 dark:bg-yellow-900 text-sm rounded">
                {msg}
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
                onClick={del}
                disabled={busy}
                className="px-4 py-2 text-sm rounded bg-red-600 text-white hover:bg-red-700 disabled:opacity-50"
              >
                {busy ? "삭제 중…" : "삭제"}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
