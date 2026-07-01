/**
 * NewVaultWizard — v0.6.6: 2-step wizard (3 step → 2 step).
 *
 *   Step 1 — 이름 (path/mode/template 자동)
 *   Step 2 — 확인 + 만들기 (요약 → POST /api/vaults/create → redirect)
 *
 * v0.6.6 simplifications (4가지 user pain 해소):
 *   1. "PWA 캐시/이전 세션 이슈, 강제 reload 안내"
 *   2. "헤더에서 새 vault 만들기" → 이 위저드에서 직접 (VaultPicker 우회 가능)
 *   3. "absolute path 왜 굳이 입력" → v0.6.3에서 이미 readonly, 강제 reload 필요
 *   4. "personal/shared/agent 선택 필요 없음" → personal fixed (shared/agent는
 *      system-internal, 사용자 표면에서 ❌ — AGENTS.md §3 over-promise 회피)
 *
 * Surgical: NewVaultWizard.tsx 본문만 교체. Sidebar.tsx / Layout.tsx /
 * VaultPicker.tsx 변경 0.
 *
 * "안정·심플" 컨셉 부합:
 *   - mode는 personal 한 가지 (사용자 비전 = "1인 vault" 기본)
 *   - template는 raven-v1 (Lite bootstrap 4종 자동)
 *   - path는 ~/Raven/<name>/ 자동 (WIKI_VAULTS_DIR override 가능, 표시)
 *   - 사용자가 입력하는 것: name 한 줄
 *
 * Advanced 옵션 (CLI):
 *   `raven vault create <name> <path> --mode shared|agent --template none`
 */
import { Link, useNavigate, useOutletContext } from "react-router-dom";
import { useEffect, useState } from "react";
import { setActiveVault } from "../lib/api";
import { TextField } from "./ui/TextField";
import { Button } from "./ui/Button";
import { SelectField } from "./ui/SelectField";

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
  const { refresh } = useOutletContext<{ refresh: () => void }>() || {};

  // state machine — 2 step only
  const [step, setStep] = useState<Step>(1);
  const [name, setName] = useState("");
  const [path, setPath] = useState(""); // readonly display
  const [mode, setMode] = useState<"personal" | "shared" | "agent">("personal");
  const [profile, setProfile] = useState<"basic" | "llm-wiki">("llm-wiki");
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
          mode,
          description: "Created via Dashboard wizard",
          bootstrap: true, // v0.6.6: 항상 Lite bootstrap
          profile,
        }),
      });
      const data = await r.json().catch(() => ({}));
      if (!r.ok || data.ok === false) {
        throw new Error(data?.detail || data?.error || `HTTP ${r.status}`);
      }
      // v0.6.8: 성공 → 새 vault를 active로 설정 (Dashboard가
      // 옛 default를 가리키는 문제 해결). 그리고 첫 페이지(index.md)
      // 를 자동 생성해 사용자가 즉시 페이지에 진입할 수 있게 한다.
      setActiveVault(name);
      if (refresh) refresh();

      try {
        const indexBody =
          `# ${name}\n\n` +
          `> Vault 홈 — 첫 페이지입니다. 자유롭게 편집하세요.\n\n` +
          `## 시작하기\n\n` +
          `- 새 페이지는 **사이드바 → ➕ 새 페이지** 또는 헤더의 **✚ 새 페이지** Quick Action에서 만드세요.\n` +
          `- **🔍 검색**으로 vault 전체를 BM25 검색할 수 있습니다.\n` +
          `- **⬡ 그래프**에서 페이지 간 연결을 시각화할 수 있습니다.\n`;
        const createPageRes = await fetch(
          `/api/vaults/${encodeURIComponent(name)}/pages`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              slug: "index",
              title: name,
              type: "concept",
              tags: ["home"],
              content: indexBody,
            }),
          }
        );
        if (!createPageRes.ok) {
          // index.md 생성이 실패해도 vault 자체는 만들어졌으므로
          // 사용자에게 알림만 띄우고 redirect는 진행한다.
          const errBody = await createPageRes.json().catch(() => ({}));
          console.warn("index.md auto-create failed:", errBody);
        }
      } catch (e) {
        console.warn("index.md auto-create error:", e);
      }

      // 성공 → vault index 페이지로 redirect.
      // v0.6.8: POST /api/vaults/{name}/pages applies slug normalization
      // (bare "index" → "content/index"). We mirror that here so
      // PageView's GET /api/vaults/{name}/pages/{slug} resolves.
      navigate(`/page/${name}/content/index`);
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
          mode={mode}
          setMode={setMode}
          profile={profile}
          setProfile={setProfile}
        />
      ) : (
        <Step2
          name={name}
          path={path}
          mode={mode}
          profile={profile}
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
  mode,
  setMode,
  profile,
  setProfile,
}: {
  name: string;
  setName: (n: string) => void;
  path: string;
  vaultsRoot: string;
  error: string | null;
  onNext: () => void;
  mode: "personal" | "shared" | "agent";
  setMode: (m: "personal" | "shared" | "agent") => void;
  profile: "basic" | "llm-wiki";
  setProfile: (p: "basic" | "llm-wiki") => void;
}) {
  return (
    <section>
      <h1 style={{ marginBottom: 8 }}>새 vault</h1>
      <p
        className="text-body"
        style={{ fontSize: 14, color: "var(--color-muted)", marginBottom: 24 }}
      >
        이름을 정하고 모드와 템플릿(프로필)을 선택하면 볼트가 자동으로 만들어집니다.
      </p>

      <TextField
        label="이름"
        required
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

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginTop: 16 }}>
        <SelectField
          label="모드"
          value={mode}
          onChange={(e) => setMode(e.target.value as any)}
          options={[
            { value: "personal", label: "개인용 (personal)" },
            { value: "shared", label: "공유용 (shared)" },
            { value: "agent", label: "에이전트용 (agent)" },
          ]}
          helper="볼트의 소유권 및 접근 모드를 설정합니다."
        />
        <SelectField
          label="프로필 (템플릿)"
          value={profile}
          onChange={(e) => setProfile(e.target.value as any)}
          options={[
            { value: "llm-wiki", label: "에이전트 위키 (llm-wiki)" },
            { value: "basic", label: "기본 (basic)" },
          ]}
          helper="llm-wiki: 5종 표준 문서 생성 | basic: WELCOME.md만 생성"
        />
      </div>
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
            (v0.6.10 이전 env 호환) 그 경로가 우선 적용됩니다.
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
        <Button variant="pillPrimary" onClick={onNext} aria-label="다음 단계로">
          다음 →
        </Button>
      </div>
    </section>
  );
}

// ────────────────────────── Step 2: 확인 ──────────────────────────

function Step2({
  name,
  path,
  mode,
  profile,
  error,
  submitting,
  onBack,
  onSubmit,
}: {
  name: string;
  path: string;
  mode: string;
  profile: string;
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
        아래 정보로 vault를 만듭니다.
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
        <dd style={{ margin: 0, fontWeight: 600 }}>{mode}</dd>

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
          {profile === "llm-wiki" ? "Lite 5종 자동 복사 (llm-wiki)" : "WELCOME.md 1장 생성 (basic)"}
          {profile === "llm-wiki" && (
            <div
              style={{
                fontSize: 11,
                color: "var(--color-muted)",
                fontFamily: "ui-monospace, SFMono-Regular, monospace",
                marginTop: 4,
              }}
            >
              _meta/system/SCHEMA.md, _meta/system/RULES.md,
              _meta/system/README.md, _meta/agents/PROJECT-WORKFLOW.md, log.md
            </div>
          )}
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
        <Button variant="pillSecondary" onClick={onBack} disabled={submitting} aria-label="이전 단계로">
          ← 이전
        </Button>
        <Button variant="pillPrimary" onClick={onSubmit} disabled={submitting} aria-label="vault 만들기">
          {submitting ? "만드는 중..." : "만들기"}
        </Button>
      </div>
    </section>
  );
}
