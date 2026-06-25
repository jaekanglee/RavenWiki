import { useState } from "react";
import { deletePage } from "../lib/api";

export function DeleteButton({
  vault,
  slug,
  onDeleted,
}: {
  vault: string;
  slug: string;
  onDeleted?: () => void;
}) {
  const [open, setOpen] = useState(false);
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  async function del() {
    if (confirm !== slug) {
      setMsg(`확인: "${slug}" 정확히 입력`);
      return;
    }
    setBusy(true);
    setMsg(null);
    try {
      const r = await deletePage(vault, slug);
      setMsg(`✅ 삭제 (archive: ${r.archived_to?.split("/").pop()})`);
      setTimeout(() => {
        setOpen(false);
        onDeleted?.();
      }, 600);
    } catch (e: any) {
      setMsg(`❌ ${e.message}`);
      setBusy(false);
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
              <code className="bg-gray-100 dark:bg-gray-800 px-1 rounded">{slug}</code>
              을(를) vault <strong>{vault}</strong>에서 삭제합니다. <code>_archive/</code>로 백업됨.
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
              <div className="mb-3 p-2 bg-yellow-100 dark:bg-yellow-900 text-sm rounded">{msg}</div>
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
