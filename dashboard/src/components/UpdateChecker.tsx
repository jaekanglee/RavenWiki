import { useEffect, useState } from "react";

// v0.7.176+: 데스크톱 앱 자동 업데이트 체크 (tauri-plugin-updater).
// 브라우저/Docker 모드에서는 __TAURI_INTERNALS__가 없어 아무 것도 하지 않는다.
type UpdateInfo = { version: string; body?: string };

export function UpdateChecker() {
  const [update, setUpdate] = useState<UpdateInfo | null>(null);
  const [installing, setInstalling] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!(window as any).__TAURI_INTERNALS__) return;
    let cancelled = false;

    import("@tauri-apps/plugin-updater")
      .then(({ check }) => check())
      .then((result) => {
        if (!cancelled && result?.available) {
          setUpdate({ version: result.version, body: result.body });
        }
      })
      .catch((e) => {
        // eslint-disable-next-line no-console
        console.warn("[Raven] 업데이트 확인 실패:", e);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  if (!update) return null;

  const install = async () => {
    setInstalling(true);
    setError(null);
    try {
      const { check } = await import("@tauri-apps/plugin-updater");
      const { relaunch } = await import("@tauri-apps/plugin-process");
      const result = await check();
      if (result?.available) {
        await result.downloadAndInstall();
        await relaunch();
      }
    } catch (e: any) {
      setError(e?.message || String(e));
      setInstalling(false);
    }
  };

  return (
    <div
      style={{
        position: "fixed",
        bottom: 16,
        right: 16,
        zIndex: 100,
        background: "var(--color-canvas)",
        border: "1px solid var(--color-hairline)",
        borderRadius: "var(--radius-md, 8px)",
        boxShadow: "0 4px 16px rgba(0,0,0,0.15)",
        padding: "12px 16px",
        maxWidth: 320,
        fontSize: 13,
      }}
    >
      <div style={{ fontWeight: 600, marginBottom: 4 }}>
        새 버전 {update.version} 사용 가능
      </div>
      {update.body && (
        <div style={{ color: "var(--color-muted)", marginBottom: 8, whiteSpace: "pre-wrap" }}>
          {update.body}
        </div>
      )}
      {error && <div style={{ color: "var(--color-danger, #d33)", marginBottom: 8 }}>{error}</div>}
      <div style={{ display: "flex", gap: 8 }}>
        <button
          type="button"
          onClick={install}
          disabled={installing}
          style={{
            padding: "4px 10px",
            borderRadius: "var(--radius-full)",
            border: "1px solid var(--color-hairline)",
            background: "var(--color-ink)",
            color: "var(--color-canvas)",
            cursor: installing ? "default" : "pointer",
          }}
        >
          {installing ? "설치 중…" : "지금 업데이트"}
        </button>
        <button
          type="button"
          onClick={() => setUpdate(null)}
          disabled={installing}
          style={{
            padding: "4px 10px",
            borderRadius: "var(--radius-full)",
            border: "1px solid var(--color-hairline)",
            background: "transparent",
          }}
        >
          나중에
        </button>
      </div>
    </div>
  );
}
