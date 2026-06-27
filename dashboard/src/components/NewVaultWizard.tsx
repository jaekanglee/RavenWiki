/**
 * NewVaultWizard — v0.6.6: 2-step wizard (3 step → 2 step).
 *
 *   Step 1 — 이름 (path/mode/template 자동)
 *   Step 2 — 확인 + 만들기 (요약 → POST /api/vaults/create → redirect)
 *
 * v0.6.6 simplifications (4가지 user pain 해소):
 *   1. "wiki가 표시되는것도 이상해" → PWA 캐시/이전 세션 이슈, 강제 reload 안내
 *   2. "wiki 눌러서 새 vault 만들기" → 이 위저드에서 직접 (VaultPicker 우회 가능)
 *   3. "absolute path 왜 굳이 입력" → v0.6.3에서 이미 readonly, 강제 reload 필요
 *   4. "personal/shared/agent 선택 필요 없음" → personal fixed (shared/agent는
 *      system-internal, 사용자 표면에서 ❌ — AGENTS.md §3 over-promise 회피)
 *
 * Surgical: NewVaultWizard.tsx 본문만 교체. Sidebar.tsx / Layout.tsx /
 * VaultPicker.tsx 변경 0.
 *
 * "안정·심플" 컨셉 부합:
 *   - mode는 personal 한 가지 (사용자 비전 = "1인 vault" 기본)
 *   - template는 wiki-v1 (Lite bootstrap 4종 자동)
 *   - path는 ~/Raven/<name>/ 자동 (WIKI_VAULTS_DIR override 가능, 표시)
 *   - 사용자가 입력하는 것: name 한 줄
 *
 * Advanced 옵션 (CLI):
 *   `raven vault create <name> <path> --mode shared|agent --template none`
 */
import { Link, useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";

/** Default mode for Dashboard-created vaults.
 *
 * Why "personal" only? Because:
 *   - `shared` and `agent` are system-internal ownership concepts (CLI use)
 *   - User persona = "1인 vault" by default (Raven product spec)
 *   - AGENTS.md §3 forbids exposing `agent` mode with "안정" wording
 *   - Multi-vault user can have multiple `personal` vaults (D8 ADR)
 */
const DEFAULT_MODE: "personal" = "personal";

/** Default template — Lite bootstrap (4종: SCHEMA.md / RULES.md / AGENTS.md / log.md).
 *  "none" is also possible via CLI but the Dashboard skips that choice
 *  entirely — every new vault is a real Raven vault.
 */
const DEFAULT_TEMPLATE: "wiki-v1" = "wiki-v1";

// kebab-case: 소문자/숫자/하이픈, 시작은 소문자, 연속 하이픈 ❌
const KEBAB_RE = /^[a-z][a-z0-9]*(-[a-z0-9]+)*$/;

/** Canonical vault path under the Raven root. Mirrors
 * `raven.core.registry.VAULTS_ROOT()` default of `~/Raven/`.
 */
function defaultPath(name: string) {
  return `~/Raven/${name}/`;
}

type Step = 1 | 2;

export function NewVaultWizard() {
  const navigate = useNavigate();

  // state machine — 2 step only
  const [step, setStep] = useState<Step>(1);
  const [name, setName] = useState("");
  const [path, setPath] = useState(""); // readonly display
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [vaultsRoot, setVaultsRoot] = useState<string>("");

  // name이 바뀌면 path 자동 결정 (사용자 입력 0)
  useEffect(() => {
    setPath(name ? defaultPath(name) : "");
  }, [name]);

  // vaultsRoot 조회 (env override 표시)
  useEffect(() => {
    fetch("/api/vaults")
      .then((r) => (r.ok ? r.json() : { vaults_root: "" }))
      .then((d) => {
        if (typeof d.vaults_root === "string") {
          setVaultsRoot(d.vaults_root);
        }
      })
      .catch(() => setVaultsRoot(""));
  }, []);

  // ─── step 1 validation ──────────────────────────────────────
  function validateName(): string | null {
    if (!name.trim()) return "vault 이름을 입력하세요.";
    if (!KEBAB_RE.test(name)) {
      return "이름은 kebab-case여야 합니다 (예: my-notes, work-2026). 소문자/숫자/하이픈만, 하이픈으로 시작 ❌";
    }
    return null;
  }

  function next() {
    setError(null);
    const err = validateName();
    if (err) {
      setError(err);
      return;
    }
    setStep(2);
  }

  function back() {
    setError(null);
    if (step === 2) setStep(1);
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
          path: path, // auto-determined from name (v0.6.3)
          mode: DEFAULT_MODE,
          description: "Created via Dashboard wizard",
          bootstrap: true, // v0.6.6: 항상 Lite bootstrap
        }),
      });
      const data = await r.json().catch(() => ({}));
      if (!r.ok || data.ok === false) {
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

  // ─── step indicator ────────────────────────────────────────
  function stepLabel(s: Step) {
    return s === 1 ? "이름" : "확인";
  }

  return (
    <div style={{ maxWidth: 640 }}>
      {/* ─── step indicator ─────────────────────────────────────── */}
      <div
        style={{
          display: "flex",
          gap: 12,
          alignItems: "center",
          marginBottom: 32,
          fontSize: 12,
          fontWeight: 700,
          letterSpacing: "0.32px",
          textTransform: "uppercase",
          color: "var(--color-muted)",
        }}
        aria-label="wizard step"
      >
        {[1, 2].map((s) => (
          <div
            key={s}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              color: s === step ? "var(--color-primary)" : "var(--color-muted)",
            }}
          >
            <span
              style={{
                display: "inline-flex",
                width: 24,
                height: 24,
                borderRadius: 12,
                background:
                  s === step
                    ? "var(--color-primary)"
                    : "var(--cds-background, #f4f4f4)",
                color: s === step ? "#fff" : "var(--color-muted)",
                alignItems: "center",
                justifyContent: "center",
                fontSize: 12,
                fontWeight: 700,
              }}
            >
              {s}
            </span>
            {stepLabel(s as Step)}
          </div>
        ))}
      </div>

      {step === 1 ? (
        <Step1
          name={name}
          setName={setName}
          path={path}
          vaultsRoot={vaultsRoot}
          error={error}
          onNext={next}
        />
      ) : (
        <Step2
          name={name}
          path={path}
          error={error}
          submitting={submitting}
          onBack={back}
          onSubmit={submit}
        />
      )}

      <div style={{ marginTop: 32 }}>
        <Link to="/" className="link-muted" style={{ fontSize: 13 }}>
          ← 홈으로
        </Link>
      </div>
    </div>
  );
}

// ────────────────────────── Step 1: 이름 ──────────────────────────

function Step1({
  name,
  setName,
  path,
  vaultsRoot,
  error,
  onNext,
}: {
  name: string;
  setName: (n: string) => void;
  path: string;
  vaultsRoot: string;
  error: string | null;
  onNext: () => void;
}) {
  return (
    <section>
      <h1 style={{ marginBottom: 8 }}>새 vault</h1>
      <p
        className="text-body"
        style={{ fontSize: 14, color: "var(--color-muted)", marginBottom: 24 }}
      >
        이름만 정하면 경로와 Lite bootstrap(4종 표준 문서)은 자동으로 만들어집니다.
      </p>

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
        이름 *
      </label>
      <input
        className="input-base"
        autoFocus
        style={{ height: 56, fontSize: 18 }}
        value={name}
        onChange={(e) => setName(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter") onNext();
        }}
        placeholder="my-notes"
        aria-label="vault name"
      />
      <div
        style={{
          fontSize: 12,
          color: "var(--color-muted)",
          marginTop: 6,
        }}
      >
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
        경로 (자동)
      </label>
      <input
        className="input-base"
        readOnly
        style={{
          height: 56,
          fontFamily: "ui-monospace, SFMono-Regular, monospace",
          background: "var(--cds-field-01, #f4f4f4)",
          color: "var(--color-muted)",
          cursor: "default",
        }}
        value={path}
        placeholder="이름을 입력하면 자동으로 표시됩니다"
        aria-label="vault path (auto-determined)"
      />
      <div
        style={{ fontSize: 12, color: "var(--color-muted)", marginTop: 6 }}
      >
        {vaultsRoot && (
          <>
            모든 Raven vault는 <code>{vaultsRoot}/&lt;name&gt;/</code> 패턴으로
            만들어집니다. 서버에 <code>WIKI_VAULTS_DIR</code>가 설정되어 있으면
            그 경로가 우선 적용됩니다.
          </>
        )}
      </div>

      {error && (
        <p
          role="alert"
          style={{
            marginTop: 16,
            color: "var(--cds-support-error, #da1e28)",
            fontSize: 13,
          }}
        >
          {error}
        </p>
      )}

      <div
        style={{
          display: "flex",
          justifyContent: "flex-end",
          marginTop: 24,
        }}
      >
        <button
          type="button"
          className="btn-pill-primary"
          onClick={onNext}
          aria-label="다음 단계로"
        >
          다음 →
        </button>
      </div>
    </section>
  );
}

// ────────────────────────── Step 2: 확인 ──────────────────────────

function Step2({
  name,
  path,
  error,
  submitting,
  onBack,
  onSubmit,
}: {
  name: string;
  path: string;
  error: string | null;
  submitting: boolean;
  onBack: () => void;
  onSubmit: () => void;
}) {
  return (
    <section>
      <h1 style={{ marginBottom: 8 }}>확인</h1>
      <p
        className="text-body"
        style={{ fontSize: 14, color: "var(--color-muted)", marginBottom: 24 }}
      >
        아래 정보로 vault를 만듭니다. Lite bootstrap(4종 표준 문서) 자동 복사.
      </p>

      <dl
        style={{
          display: "grid",
          gridTemplateColumns: "120px 1fr",
          gap: "12px 16px",
          padding: 20,
          background: "var(--cds-field-01, #fafafa)",
          borderRadius: 8,
          border: "1px solid var(--cds-border-subtle-01, #e0e0e0)",
          fontSize: 14,
        }}
      >
        <dt
          style={{
            color: "var(--color-muted)",
            fontWeight: 700,
            fontSize: 12,
            textTransform: "uppercase",
            letterSpacing: "0.32px",
          }}
        >
          이름
        </dt>
        <dd style={{ margin: 0, fontWeight: 600 }}>{name}</dd>

        <dt
          style={{
            color: "var(--color-muted)",
            fontWeight: 700,
            fontSize: 12,
            textTransform: "uppercase",
            letterSpacing: "0.32px",
          }}
        >
          경로
        </dt>
        <dd
          style={{
            margin: 0,
            fontFamily: "ui-monospace, SFMono-Regular, monospace",
            fontSize: 13,
          }}
        >
          {path}
        </dd>

        <dt
          style={{
            color: "var(--color-muted)",
            fontWeight: 700,
            fontSize: 12,
            textTransform: "uppercase",
            letterSpacing: "0.32px",
          }}
        >
          모드
        </dt>
        <dd style={{ margin: 0 }}>personal (1인용 — 기본값)</dd>

        <dt
          style={{
            color: "var(--color-muted)",
            fontWeight: 700,
            fontSize: 12,
            textTransform: "uppercase",
            letterSpacing: "0.32px",
          }}
        >
          Bootstrap
        </dt>
        <dd style={{ margin: 0 }}>
          Lite 4종 자동 복사
          <div
            style={{
              fontSize: 11,
              color: "var(--color-muted)",
              fontFamily: "ui-monospace, SFMono-Regular, monospace",
              marginTop: 4,
            }}
          >
            _meta/system/SCHEMA.md, _meta/system/RULES.md,
            _meta/system/AGENTS.md, log.md
          </div>
        </dd>
      </dl>

      {error && (
        <p
          role="alert"
          style={{
            marginTop: 16,
            color: "var(--cds-support-error, #da1e28)",
            fontSize: 13,
          }}
        >
          {error}
        </p>
      )}

      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          marginTop: 24,
        }}
      >
        <button
          type="button"
          className="btn-pill-secondary"
          onClick={onBack}
          disabled={submitting}
          aria-label="이전 단계로"
        >
          ← 이전
        </button>
        <button
          type="button"
          className="btn-pill-primary"
          onClick={onSubmit}
          disabled={submitting}
          aria-label="vault 만들기"
        >
          {submitting ? "만드는 중..." : "만들기"}
        </button>
      </div>
    </section>
  );
}
