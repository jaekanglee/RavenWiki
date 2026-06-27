import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

/**
 * Vault creation wizard — 3-step flow.
 *
 *   Step 1 — 이름 + 경로            (name kebab-case 강제, path 기본 제안)
 *   Step 2 — 모드 + 템플릿          (personal/shared/agent + AI-Agent-Wiki v1.0.0)
 *   Step 3 — 확인 + 만들기          (요약 → POST /api/vaults/create → redirect)
 *
 * 토큰 사용: --color-primary / --color-canvas / --color-surface-soft /
 *            --color-ink / --color-muted / --radius-md / --radius-lg /
 *            --shadow-overlay / --color-error-text
 *
 * API: POST /api/vaults/create
 *      { name, path, mode, description, bootstrap }
 *
 * 응답 ok 시 → navigate(`/page/<name>/index`)
 *       실패 시 → inline 에러 표시 (그 자리에 머무름)
 */

type Mode = "personal" | "shared" | "agent";
type TemplateKey = "none" | "wiki-v1";
type Step = 1 | 2 | 3;

const TEMPLATES: { key: TemplateKey; label: string; desc: string }[] = [
  { key: "none", label: "없음 (빈 vault)", desc: "bootstrap 안 함. 최소한의 메타만 생성." },
  { key: "wiki-v1", label: "AI-Agent-Wiki v1.0.0", desc: "Lite bootstrap (SCHEMA/RULES/AGENTS/log.md 자동 복사)" },
];

const MODES: { key: Mode; label: string; hint: string }[] = [
  { key: "personal", label: "personal", hint: "1인용 vault. 기본값." },
  { key: "shared", label: "shared", hint: "여러 사람/기계가 공유. 동시 쓰기는 사용자 책임." },
  { key: "agent", label: "agent", hint: "단일 에이전트가 owner. scope/provenance 안전장치 활성." },
];

// kebab-case: 소문자/숫자/하이픈, 시작은 소문자, 연속 하이픈 ❌
const KEBAB_RE = /^[a-z][a-z0-9]*(-[a-z0-9]+)*$/;

/**
 * Canonical vault path under the Raven root. Mirrors
 * `raven.core.registry.VAULTS_ROOT()` default of `~/Raven/`.
 *
 * v0.6.3+: The path is auto-determined from the vault name — users no
 * longer type it. The field in Step 1 is rendered as a read-only
 * preview so the user can see where the vault will be created. If
 * the server is configured with `WIKI_VAULTS_DIR=<elsewhere>`, the
 * backend will honor that override (we display the same string but
 * the actual creation uses the env-resolved root).
 */
function defaultPath(name: string) {
  return `~/Raven/${name}/`;
}

export function NewVaultWizard() {
  const navigate = useNavigate();

  // state machine
  const [step, setStep] = useState<Step>(1);
  const [name, setName] = useState("");
  const [path, setPath] = useState("");
  const [mode, setMode] = useState<Mode>("personal");
  const [template, setTemplate] = useState<TemplateKey>("wiki-v1");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [pathTouched, setPathTouched] = useState(false);

  // name이 바뀌면 path 기본값 자동 제안 (사용자가 직접 만지지 않은 경우에만)
  useEffect(() => {
    if (!pathTouched && step === 1) {
      setPath(name ? defaultPath(name) : "");
    }
  }, [name, pathTouched, step]);

  // ─── validation ──────────────────────────────────────────
  function validateStep1(): string | null {
    if (!name.trim()) return "vault name은 필수입니다.";
    if (!KEBAB_RE.test(name)) {
      return "name은 kebab-case여야 합니다 (예: my-notes, work-2026). 소문자/숫자/하이픈만, 하이픈으로 시작 ❌";
    }
    if (!path.trim()) return "path는 필수입니다.";
    if (!path.startsWith("/") && !path.startsWith("~")) {
      return "path는 절대경로여야 합니다 (~/ 또는 / 로 시작).";
    }
    return null;
  }

  // ─── step transitions ─────────────────────────────────────
  function next() {
    setError(null);
    if (step === 1) {
      const err = validateStep1();
      if (err) {
        setError(err);
        return;
      }
      setStep(2);
    } else if (step === 2) {
      setStep(3);
    }
  }

  function back() {
    setError(null);
    if (step === 2) setStep(1);
    else if (step === 3) setStep(2);
  }

  // ─── submit ───────────────────────────────────────────────
  async function submit() {
    setError(null);
    setSubmitting(true);
    try {
      const r = await fetch("/api/vaults/create", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name,
          path,
          mode,
          description: `Created via Dashboard wizard (${template})`,
          bootstrap: template === "wiki-v1",
        }),
      });
      const data = await r.json().catch(() => ({}));
      if (!r.ok || !data.ok) {
        throw new Error(data?.detail || data?.error || `HTTP ${r.status}`);
      }
      // 성공 → vault index 페이지로 redirect
      navigate(`/page/${name}/index`);
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setError(`만들기 실패: ${msg}`);
      setSubmitting(false);
    }
  }

  // ─── step indicator ───────────────────────────────────────
  const StepIndicator = (
    <div
      style={{
        display: "flex",
        gap: 8,
        marginBottom: 24,
        fontSize: 12,
        fontWeight: 700,
        letterSpacing: "0.32px",
        textTransform: "uppercase",
        color: "var(--color-muted)",
      }}
      aria-label="wizard step"
    >
      {([1, 2, 3] as const).map((n) => {
        const active = n === step;
        const done = n < step;
        return (
          <div
            key={n}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 6,
              padding: "6px 12px",
              borderRadius: "var(--radius-full)",
              background: active
                ? "var(--cds-layer-accent)"
                : done
                  ? "var(--cds-tag-blue-bg)"
                  : "var(--color-surface-soft)",
              color: active
                ? "var(--color-on-primary)"
                : done
                  ? "var(--cds-tag-blue-text)"
                  : "var(--color-muted)",
            }}
          >
            <span>{done ? "✓" : n}</span>
            <span>
              {n === 1 ? "이름 + 경로" : n === 2 ? "모드 + 템플릿" : "확인"}
            </span>
          </div>
        );
      })}
    </div>
  );

  // ─── step 1: name + path ──────────────────────────────────
  if (step === 1) {
    return (
      <div
        className="card-flat"
        style={{
          padding: 24,
          borderRadius: "var(--radius-lg)",
          boxShadow: "var(--shadow-overlay)",
        }}
      >
        {StepIndicator}

        <label
          style={{
            display: "block",
            fontSize: 12,
            fontWeight: 700,
            letterSpacing: "0.32px",
            textTransform: "uppercase",
            color: "var(--color-muted)",
            marginBottom: 8,
          }}
        >
          Vault 이름 *
        </label>
        <input
          autoFocus
          className="input-base"
          style={{ height: 64 }}
          value={name}
          onChange={(e) => setName(e.target.value.toLowerCase().trim())}
          placeholder="my-notes"
          aria-label="vault name"
        />
        <div style={{ fontSize: 12, color: "var(--color-muted)", marginTop: 6 }}>
          kebab-case 강제: <code>{`^[a-z][a-z0-9]*(-[a-z0-9]+)*$`}</code>
        </div>

        <label
          style={{
            display: "block",
            fontSize: 12,
            fontWeight: 700,
            letterSpacing: "0.32px",
            textTransform: "uppercase",
            color: "var(--color-muted)",
            marginTop: 24,
            marginBottom: 8,
          }}
        >
          경로 (자동 결정됨)
        </label>
        <input
          className="input-base"
          readOnly
          style={{
            height: 64,
            fontFamily: "ui-monospace, SFMono-Regular, monospace",
            background: "var(--cds-field-01, #f4f4f4)",
            color: "var(--color-muted)",
            cursor: "default",
          }}
          value={path}
          placeholder="이름을 입력하면 자동으로 표시됩니다"
          aria-label="vault path (auto-determined)"
        />
        <div style={{ fontSize: 12, color: "var(--color-muted)", marginTop: 6 }}>
          v0.6.3+: 모든 Raven vault는 <code>~/Raven/&lt;name&gt;/</code> 패턴으로 자동 생성됩니다
          (백엔드 <code>VAULTS_ROOT</code> 기본값). 서버에 <code>WIKI_VAULTS_DIR</code> 환경변수가
          설정되어 있으면 그 경로가 우선 적용됩니다.
        </div>

        {error && (
          <div
            role="alert"
            style={{
              marginTop: 16,
              padding: 12,
              borderRadius: "var(--radius-md)",
              background: "var(--color-surface-soft)",
              color: "var(--color-error-text)",
              fontSize: 13,
            }}
          >
            {error}
          </div>
        )}

        <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 32 }}>
          <button
            className="btn-primary"
            onClick={next}
            disabled={!name || !path}
            style={{ minWidth: 120 }}
          >
            다음 →
          </button>
        </div>
      </div>
    );
  }

  // ─── step 2: mode + template ──────────────────────────────
  if (step === 2) {
    return (
      <div
        className="card-flat"
        style={{
          padding: 24,
          borderRadius: "var(--radius-lg)",
          boxShadow: "var(--shadow-overlay)",
        }}
      >
        {StepIndicator}

        <div
          style={{
            fontSize: 12,
            fontWeight: 700,
            letterSpacing: "0.32px",
            textTransform: "uppercase",
            color: "var(--color-muted)",
            marginBottom: 12,
          }}
        >
          모드
        </div>
        <div role="radiogroup" style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {MODES.map((m) => {
            const selected = mode === m.key;
            return (
              <label
                key={m.key}
                style={{
                  display: "flex",
                  alignItems: "flex-start",
                  gap: 12,
                  padding: 16,
                  border: `2px solid ${selected ? "var(--cds-border-interactive)" : "var(--cds-border-subtle)"}`,
                  borderRadius: "var(--radius-md)",
                  cursor: "pointer",
                  background: selected
                    ? "var(--cds-tag-blue-bg)"
                    : "var(--cds-background)",
                  transition: "border-color 0.12s ease, background-color 0.12s ease",
                }}
              >
                <input
                  type="radio"
                  name="mode"
                  value={m.key}
                  checked={selected}
                  onChange={() => setMode(m.key)}
                  style={{ marginTop: 3 }}
                />
                <div>
                  <div style={{ fontWeight: 700, color: "var(--color-ink)" }}>
                    {m.label}
                  </div>
                  <div style={{ fontSize: 12, color: "var(--color-muted)", marginTop: 2 }}>
                    {m.hint}
                  </div>
                </div>
              </label>
            );
          })}
        </div>

        <div
          style={{
            fontSize: 12,
            fontWeight: 700,
            letterSpacing: "0.32px",
            textTransform: "uppercase",
            color: "var(--color-muted)",
            marginTop: 28,
            marginBottom: 12,
          }}
        >
          템플릿
        </div>
        <div role="radiogroup" style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {TEMPLATES.map((t) => {
            const selected = template === t.key;
            return (
              <label
                key={t.key}
                style={{
                  display: "flex",
                  alignItems: "flex-start",
                  gap: 12,
                  padding: 16,
                  border: `2px solid ${selected ? "var(--cds-border-interactive)" : "var(--cds-border-subtle)"}`,
                  borderRadius: "var(--radius-md)",
                  cursor: "pointer",
                  background: selected
                    ? "var(--cds-tag-blue-bg)"
                    : "var(--cds-background)",
                  transition: "border-color 0.12s ease, background-color 0.12s ease",
                }}
              >
                <input
                  type="radio"
                  name="template"
                  value={t.key}
                  checked={selected}
                  onChange={() => setTemplate(t.key)}
                  style={{ marginTop: 3 }}
                />
                <div>
                  <div style={{ fontWeight: 700, color: "var(--color-ink)" }}>
                    {t.label}
                  </div>
                  <div style={{ fontSize: 12, color: "var(--color-muted)", marginTop: 2 }}>
                    {t.desc}
                  </div>
                </div>
              </label>
            );
          })}
        </div>

        <div style={{ display: "flex", justifyContent: "space-between", marginTop: 32 }}>
          <button className="btn-secondary" onClick={back}>
            ← 뒤로
          </button>
          <button className="btn-primary" onClick={next} style={{ minWidth: 120 }}>
            다음 →
          </button>
        </div>
      </div>
    );
  }

  // ─── step 3: confirm ──────────────────────────────────────
  const templateLabel =
    TEMPLATES.find((t) => t.key === template)?.label ?? template;
  const modeLabel = MODES.find((m) => m.key === mode)?.label ?? mode;

  return (
    <div
      className="card-flat"
      style={{
        padding: 24,
        borderRadius: "var(--radius-lg)",
        boxShadow: "var(--shadow-overlay)",
      }}
    >
      {StepIndicator}

      <div
        style={{
          fontSize: 12,
          fontWeight: 700,
          letterSpacing: "0.32px",
          textTransform: "uppercase",
          color: "var(--color-muted)",
          marginBottom: 12,
        }}
      >
        요약
      </div>
      <dl
        style={{
          margin: 0,
          padding: 16,
          background: "var(--color-surface-soft)",
          borderRadius: "var(--radius-md)",
          display: "grid",
          gridTemplateColumns: "120px 1fr",
          rowGap: 12,
          columnGap: 16,
          fontSize: 14,
        }}
      >
        <dt style={{ color: "var(--color-muted)", fontWeight: 500 }}>이름</dt>
        <dd
          style={{
            margin: 0,
            color: "var(--color-ink)",
            fontFamily: "ui-monospace, SFMono-Regular, monospace",
            fontWeight: 600,
          }}
        >
          {name}
        </dd>

        <dt style={{ color: "var(--color-muted)", fontWeight: 500 }}>경로</dt>
        <dd
          style={{
            margin: 0,
            color: "var(--color-ink)",
            fontFamily: "ui-monospace, SFMono-Regular, monospace",
          }}
        >
          {path}
        </dd>

        <dt style={{ color: "var(--color-muted)", fontWeight: 500 }}>모드</dt>
        <dd style={{ margin: 0, color: "var(--color-ink)" }}>
          <span className="chip-strong">{modeLabel}</span>
        </dd>

        <dt style={{ color: "var(--color-muted)", fontWeight: 500 }}>템플릿</dt>
        <dd style={{ margin: 0, color: "var(--color-ink)" }}>
          <span className="chip">{templateLabel}</span>
        </dd>
      </dl>

      <div
        style={{
          marginTop: 16,
          padding: 12,
          background: "var(--cds-tag-blue-bg)",
          color: "var(--cds-tag-blue-text)",
          borderRadius: "var(--radius-md)",
          fontSize: 13,
        }}
      >
        ℹ️ 만들기 후 <code>/page/{name}/index</code>로 이동합니다.
      </div>

      {error && (
        <div
          role="alert"
          style={{
            marginTop: 16,
            padding: 12,
            borderRadius: "var(--radius-md)",
            background: "var(--color-surface-soft)",
            color: "var(--color-error-text)",
            fontSize: 13,
          }}
        >
          {error}
        </div>
      )}

      <div style={{ display: "flex", justifyContent: "space-between", marginTop: 32 }}>
        <button
          className="btn-secondary"
          onClick={back}
          disabled={submitting}
        >
          ← 뒤로
        </button>
        <button
          className="btn-primary"
          onClick={submit}
          disabled={submitting}
          style={{ minWidth: 160 }}
        >
          {submitting ? "만드는 중…" : "만들기"}
        </button>
      </div>
    </div>
  );
}
