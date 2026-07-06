/**
 * NewVaultWizard — v0.6.6: 2-step wizard (3 step → 2 step).
 *
 *   Step 1 — 이름 (path/mode/template 자동)
 *   Step 2 — 확인 + 만들기 (요약 → POST /api/vaults → redirect)
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
import { Toast } from "./ui/Toast";

// v0.7.74+: wizard 결과 화면에 MCP 설정 snippet + 클립보드 복사 버튼.
// PROJECT-WORKFLOW.md §1.5 signpost의 구체적 endpoint를 여기서 자동 생성.
// Tier 1 leak 회피: 환경별 snippet만, raven 내부 토픽 참조 ❌.
function buildStdioSnippet() {
  // 표준 MCP 클라이언트 stdio 설정 (Claude Desktop / Cursor / 표준)
  return JSON.stringify(
    {
      command: "python",
      args: ["-m", "raven.mcp.cli", "--transport", "stdio", "--mode", "read"],
    },
    null,
    2
  );
}

function buildHttpSnippet(endpoint: string) {
  return JSON.stringify({ url: endpoint }, null, 2);
}

// kebab-case: 소문자/숫자/하이픈, 시작은 소문자, 연속 하이픈 ❌
const KEBAB_RE = /^[a-z][a-z0-9]*(-[a-z0-9]+)*$/;

/** Canonical vault path under the Raven root. Mirrors
 * `raven.core.registry.VAULTS_ROOT()` default of `~/Raven/`.
 */
function defaultPath(name: string) {
  return `~/Raven/${name}/`;
}

function defaultMcpEndpoint() {
  if (typeof window === "undefined") return "http://127.0.0.1:8766/mcp";
  return `http://${window.location.hostname || "127.0.0.1"}:8766/mcp`;
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
  const mcpEndpoint = defaultMcpEndpoint();

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
      const r = await fetch("/api/vaults", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name,
          path: path, // display path; API rebases to runtime mount when needed
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
      const createdPath = data?.vault?.path || path;
      // v0.6.8: 성공 → 새 vault를 active로 설정 (Dashboard가
      // 옛 default를 가리키는 문제 해결). 그리고 첫 페이지(index.md)
      // 를 자동 생성해 사용자가 즉시 페이지에 진입할 수 있게 한다.
      setActiveVault(name);
      if (refresh) refresh();

      try {
        const indexBody =
          `# ${name}\n\n` +
          `> [BLUF] 이 볼트는 **${mode}** 모드로 동작하는 Raven 지식 저장소입니다.\n\n` +
          `## 📊 볼트 정보 (Metadata)\n\n` +
          `| 항목 | 세부 정보 |\n` +
          `| :--- | :--- |\n` +
          `| **보관소 이름** | \`${name}\` |\n` +
          `| **로컬 경로** | \`${createdPath}\` |\n` +
          `| **소유/접근 모드** | \`${mode}\` |\n` +
          `| **부트스트랩 프로필** | \`${profile}\` |\n\n` +
          `## 📁 볼트 내부 구조 안내\n\n` +
          `이 볼트는 아래와 같이 구조화된 로컬 디렉터리로 구성되어 있습니다:\n\n` +
          `* **\`content/\`**: 사람이 읽고 에이전트가 관리하는 모든 마크다운 문서가 보관됩니다. (\`type: frontmatter\`로 분류)\n` +
          `* **\`raw/\`**: 웹 클리핑, 논문, 대화 기록 등 변경할 수 없는 1차 소스 데이터를 보관하는 불변의 공간입니다.\n` +
          `* **\`_meta/\`**: 볼트의 규약과 규칙을 담고 있습니다.\n` +
          `  * \`system/SCHEMA.md\`: 태그 및 프런트매터 분류 규칙\n` +
          `  * \`system/RULES.md\`: 인지 거버넌스 및 편집 정책\n` +
          `  * \`system/README.md\`: 보관소 사용자 가이드\n` +
          `  * \`agents/PROJECT-WORKFLOW.md\`: 에이전트가 문서를 수정할 때 따라야 하는 작업 템플릿\n` +
          `* **\`log.md\`**: 볼트에 발생한 문서의 생성, 수정, 인제스트 이력이 시간 순으로 기록되는 타임라인 파일입니다.\n\n` +
          `## 🚀 Agent / MCP Quick Start\n\n` +
          `이 vault를 붙일 MCP client는 Raven MCP endpoint(\`${mcpEndpoint}\`)를 추가한 뒤, 이 볼트 경로(\`${createdPath}\`)를 작업 기준으로 사용하면 됩니다.\n\n` +
          `- **MCP endpoint**: \`${mcpEndpoint}\`\n` +
          `- **Transport**: streamable HTTP\n` +
          `- **대상 client**: Claude Code, Cursor, 기타 MCP 호환 agent\n\n` +
          `1. **인제스트 (Ingest)**: 새 소스(URL, 파일)를 볼트에 추가합니다.\n` +
          `2. **린트 (Lint)**: 페이지 간 깨진 링크나 모순을 검증합니다.\n` +
          `3. **그래프 (Graph)**: 상단 메뉴의 **⬡ 그래프**를 눌러 지식 간의 상호 연결망을 한눈에 살펴보세요.\n`;
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
          mcpEndpoint={mcpEndpoint}
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
          background: "var(--color-surface-soft)",
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
            color: "var(--color-error-text)",
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
  mcpEndpoint,
  onBack,
  onSubmit,
}: {
  name: string;
  path: string;
  mode: string;
  profile: string;
  error: string | null;
  submitting: boolean;
  mcpEndpoint: string;
  onBack: () => void;
  onSubmit: () => void;
}) {
  // v0.7.74+: 클립보드 복사 확인 toast (v0.7.71 race-free auto-close 패턴 동일).
  const [copyToast, setCopyToast] = useState<
    { message: string; type: "success" | "error" } | null
  >(null);
  useEffect(() => {
    if (!copyToast) return;
    const timer = window.setTimeout(() => setCopyToast(null), 2400);
    return () => window.clearTimeout(timer);
  }, [copyToast]);

  const copyToClipboard = async (label: string, text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopyToast({ message: `✅ ${label} 복사 완료`, type: "success" });
    } catch (e) {
      setCopyToast({
        message: `❌ 복사 실패 — 직접 선택해 복사하세요`,
        type: "error",
      });
    }
  };

  const stdioSnippet = buildStdioSnippet();
  const httpSnippet = buildHttpSnippet(mcpEndpoint);

  return (
    <section>
      <Toast
        open={Boolean(copyToast)}
        message={copyToast?.message ?? ""}
        type={copyToast?.type ?? "success"}
      />
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
          background: "var(--color-surface-soft)",
          borderRadius: 8,
          border: "1px solid var(--color-hairline)",
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

      <div
        style={{
          marginTop: 16,
          padding: 16,
          background: "var(--color-surface-soft)",
          borderRadius: 8,
          border: "1px solid var(--color-hairline)",
        }}
      >
        <div
          style={{
            fontSize: 12,
            fontWeight: 700,
            textTransform: "uppercase",
            letterSpacing: "0.32px",
            color: "var(--color-muted)",
            marginBottom: 8,
          }}
        >
          Agent 연결 (MCP)
        </div>
        <p style={{ margin: 0, fontSize: 14, color: "var(--color-body)" }}>
          이 vault는 표준 <strong>Model Context Protocol (JSON-RPC)</strong>로 노출됩니다.
          아래 snippet을 당신의 MCP 클라이언트 설정 파일에 붙여넣으세요.
        </p>

        {/* stdio snippet — 권장 (로컬 sub-process) */}
        <div style={{ marginTop: 12 }}>
          <div
            style={{
              fontSize: 11,
              fontWeight: 700,
              letterSpacing: "0.32px",
              textTransform: "uppercase",
              color: "var(--color-muted)",
              marginBottom: 4,
            }}
          >
            stdio (권장 — 로컬)
          </div>
          <div
            style={{
              display: "flex",
              gap: 8,
              alignItems: "flex-start",
            }}
          >
            <pre
              data-testid="mcp-stdio-snippet"
              style={{
                flex: 1,
                margin: 0,
                padding: 10,
                background: "var(--color-surface-soft)",
                border: "1px solid var(--color-hairline)",
                borderRadius: "var(--radius-sm)",
                fontFamily: "ui-monospace, SFMono-Regular, monospace",
                fontSize: 12,
                color: "var(--color-ink)",
                overflowX: "auto",
                whiteSpace: "pre",
              }}
            >
              {stdioSnippet}
            </pre>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => copyToClipboard("stdio snippet", stdioSnippet)}
              aria-label="stdio snippet 복사"
              style={{ flexShrink: 0 }}
            >
              복사
            </Button>
          </div>
        </div>

        {/* HTTP snippet — 원격 (Tailscale 등) */}
        <div style={{ marginTop: 12 }}>
          <div
            style={{
              fontSize: 11,
              fontWeight: 700,
              letterSpacing: "0.32px",
              textTransform: "uppercase",
              color: "var(--color-muted)",
              marginBottom: 4,
            }}
          >
            streamable-http (원격)
          </div>
          <div style={{ display: "flex", gap: 8, alignItems: "flex-start" }}>
            <pre
              data-testid="mcp-http-snippet"
              style={{
                flex: 1,
                margin: 0,
                padding: 10,
                background: "var(--color-surface-soft)",
                border: "1px solid var(--color-hairline)",
                borderRadius: "var(--radius-sm)",
                fontFamily: "ui-monospace, SFMono-Regular, monospace",
                fontSize: 12,
                color: "var(--color-ink)",
                overflowX: "auto",
                whiteSpace: "pre",
              }}
            >
              {httpSnippet}
            </pre>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => copyToClipboard("HTTP snippet", httpSnippet)}
              aria-label="HTTP snippet 복사"
              style={{ flexShrink: 0 }}
            >
              복사
            </Button>
          </div>
          <div style={{ marginTop: 6, fontSize: 11, color: "var(--color-muted)" }}>
            endpoint: {mcpEndpoint}
          </div>
        </div>

        <div
          style={{
            marginTop: 12,
            padding: 10,
            background: "var(--color-surface-soft)",
            border: "1px solid var(--color-hairline)",
            borderRadius: "var(--radius-sm)",
            fontSize: 12,
            color: "var(--color-body)",
          }}
        >
          <div style={{ fontWeight: 600, color: "var(--color-ink)", marginBottom: 6 }}>
            표준 MCP 연결 흐름
          </div>
          1. 위 snippet을 당신의 MCP 클라이언트 설정에 추가 (vendor 무관 — JSON-RPC 표준)
          <br />
          2. <code>tools/list</code> 호출 → 9개 도구 schema 자동 discovery
          <br />
          3. 첫 도구 호출 시 <code>vault=&quot;{`{`}이름{`}`}&quot;</code> 인자 필수 (다중 vault 지원)
          <br />
          <br />
          <div style={{ fontWeight: 600, color: "var(--color-ink)", marginBottom: 6 }}>
            권한 모드
          </div>
          <code>read</code> (기본, 6종) · <code>write</code> (+3종, 페이지 CRUD/격리) · <code>admin</code> (+2종, 사람 운영자 전용)
          <br />
          <br />
          <div style={{ fontWeight: 600, color: "var(--color-ink)", marginBottom: 6 }}>
            연결 안 될 때
          </div>
          - <code>command not found: python</code> → 운영자에게 <code>python3</code> 또는 venv path 확인
          <br />
          - <code>address already in use</code> → 다른 포트 사용 또는 기존 프로세스 종료
          <br />
          - <code>permission_denied</code> → <code>write</code>/<code>admin</code> 모드로 재시작 필요
          <br />
          - <code>vault not found</code> → <code>vault</code> 인자값 등록된 이름과 일치 확인
        </div>
      </div>

      {error && (
        <p
          role="alert"
          style={{
            marginTop: 16,
            color: "var(--color-error-text)",
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
