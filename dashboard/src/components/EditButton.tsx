import { useState } from "react";
import { updatePage } from "../lib/api";

export function EditButton({
  vault,
  slug,
  content,
  onSaved,
}: {
  vault: string;
  slug: string;
  content: string;
  onSaved?: () => void;
}) {
  const [open, setOpen] = useState(false);
  const [body, setBody] = useState(content);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  async function save() {
    setBusy(true);
    setMsg(null);
    try {
      await updatePage(vault, slug, { content: body });
      setMsg("✅ 저장 완료");
      setTimeout(() => {
        setOpen(false);
        onSaved?.();
      }, 600);
    } catch (e: any) {
      setMsg(`❌ ${e.message}`);
      setBusy(false);
    }
  }

  return (
    <>
      <button
        onClick={() => {
          setBody(content);
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
            <h2 className="text-xl font-bold mb-2">
              편집: <code className="text-sm">{slug}</code>
            </h2>
            <textarea
              value={body}
              onChange={(e) => setBody(e.target.value)}
              className="flex-1 border rounded px-3 py-2 text-sm font-mono min-h-[400px]"
            />
            {msg && (
              <div className="mt-2 p-2 bg-yellow-100 dark:bg-yellow-900 text-sm rounded">{msg}</div>
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
