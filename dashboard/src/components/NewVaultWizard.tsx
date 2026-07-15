import { Link, useNavigate, useOutletContext } from "react-router-dom";
import { useEffect, useState } from "react";
import { setActiveVault } from "../lib/api";
import { TextField } from "./ui/TextField";
import { Button } from "./ui/Button";

const KEBAB_RE = /^[a-z][a-z0-9]*(-[a-z0-9]+)*$/;

function defaultPath(name: string) {
  return `~/Raven/${name}/`;
}

export function NewVaultWizard() {
  const navigate = useNavigate();
  const { refresh } = useOutletContext<{ refresh: () => void }>() || {};
  const [name, setName] = useState("");
  const [path, setPath] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    setPath(name ? defaultPath(name) : "");
  }, [name]);

  async function submit() {
    setError(null);
    if (!name.trim()) {
      setError("vault 이름을 입력하세요.");
      return;
    }
    if (!KEBAB_RE.test(name)) {
      setError("이름은 kebab-case여야 합니다 (예: my-notes, work-2026).");
      return;
    }

    setSubmitting(true);
    try {
      const r = await fetch("/api/vaults", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name,
          path,
          mode: "personal",
          description: "Created via Dashboard",
        }),
      });
      const data = await r.json().catch(() => ({}));
      if (!r.ok || data.ok === false) {
        throw new Error(data?.detail || data?.error || `HTTP ${r.status}`);
      }
      setActiveVault(name);
      refresh?.();
      navigate("/");
    } catch (e) {
      setError(`만들기 실패: ${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div style={{ maxWidth: 560 }}>
      <h1 style={{ marginBottom: 8 }}>새 vault</h1>
      <p className="text-muted" style={{ fontSize: 14, marginBottom: 24 }}>
        빈 Markdown workspace를 만듭니다. 문서와 폴더는 필요한 만큼 직접 추가하세요.
      </p>

      <TextField
        label="이름"
        required
        autoFocus
        value={name}
        onChange={(e) => setName(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter") void submit();
        }}
        placeholder="my-notes"
        helper="소문자, 숫자, 하이픈만 사용할 수 있습니다."
      />

      <TextField
        label="경로"
        readOnly
        value={path}
        placeholder="이름을 입력하면 자동으로 표시됩니다"
        helper="기본 위치 아래에 새 폴더를 만듭니다."
        style={{ marginTop: 16, fontFamily: "ui-monospace, SFMono-Regular, monospace" }}
      />

      {error && (
        <p role="alert" style={{ marginTop: 16, color: "var(--color-danger-text)", fontSize: 13 }}>
          {error}
        </p>
      )}

      <div style={{ display: "flex", justifyContent: "space-between", marginTop: 24 }}>
        <Link to="/" className="link-muted" style={{ fontSize: 13, alignSelf: "center" }}>
          ← 홈으로
        </Link>
        <Button variant="pillPrimary" onClick={() => void submit()} disabled={submitting}>
          {submitting ? "만드는 중…" : "만들기"}
        </Button>
      </div>
    </div>
  );
}
