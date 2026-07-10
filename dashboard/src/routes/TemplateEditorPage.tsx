import { useState, useEffect } from "react";
import { useOutletContext } from "react-router-dom";
import { PageHeader } from "../components/ui/PageHeader";
import { Button } from "../components/ui/Button";
import { fetchTemplates, updateTemplate, type TemplateItem } from "../lib/api";

const TEMPLATE_TYPES = [
  { type: "concept", label: "concept", desc: "개념 정의", icon: "💡" },
  { type: "person", label: "person", desc: "인물/팀", icon: "👤" },
  { type: "tool", label: "tool", desc: "도구/라이브러리", icon: "🔧" },
  { type: "comparison", label: "comparison", desc: "비교 분석", icon: "⚖️" },
  { type: "project", label: "project", desc: "프로젝트", icon: "📐" },
  { type: "rule", label: "rule", desc: "정책/규칙", icon: "📜" },
  { type: "query", label: "query", desc: "조회/리포트", icon: "📊" },
  { type: "journal", label: "journal", desc: "일지/메모", icon: "📓" },
  { type: "issue", label: "issue", desc: "이슈 추적", icon: "🐛" },
];

const DEFAULT_TEMPLATE = (type: string) => `---
title: {title}
type: ${type}
tags: []
created: {date}
updated: {date}
---

## 요약

<!-- 이 문서의 핵심 내용을 1-2줄로 요약하세요 -->

## 본문

<!-- 상세 내용을 작성하세요 -->

## 관련 문서

<!-- [[wikilink]] 형태로 관련 문서를 연결하세요 -->
`;

export function TemplateEditorPage() {
  const { vault } = useOutletContext<{ vault: string; refresh: () => void }>();

  const [templates, setTemplates] = useState<TemplateItem[]>([]);
  const [selectedType, setSelectedType] = useState<string>("concept");
  const [editContent, setEditContent] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [toastMsg, setToastMsg] = useState<string | null>(null);
  const [toastType, setToastType] = useState<"success" | "error">("success");

  useEffect(() => {
    setLoading(true);
    fetchTemplates(vault)
      .then((ts) => {
        setTemplates(ts);
        const cur = ts.find((t) => t.type === selectedType);
        setEditContent(cur?.content || DEFAULT_TEMPLATE(selectedType));
        setDirty(false);
      })
      .catch(() => setTemplates([]))
      .finally(() => setLoading(false));
  }, [vault]);

  useEffect(() => {
    if (!toastMsg) return;
    const t = setTimeout(() => setToastMsg(null), 2400);
    return () => clearTimeout(t);
  }, [toastMsg]);

  const selectType = (type: string) => {
    if (dirty) {
      if (!window.confirm("저장하지 않은 변경 사항이 있습니다. 계속하시겠습니까?")) return;
    }
    setSelectedType(type);
    const cur = templates.find((t) => t.type === type);
    setEditContent(cur?.content || DEFAULT_TEMPLATE(type));
    setDirty(false);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await updateTemplate(vault, selectedType, editContent);
      // Update local state
      setTemplates((prev) =>
        prev.map((t) =>
          t.type === selectedType ? { ...t, exists: true, content: editContent } : t
        )
      );
      setDirty(false);
      setToastType("success");
      setToastMsg(`✅ '${selectedType}' 템플릿 저장 완료`);
    } catch (e: any) {
      setToastType("error");
      setToastMsg(`❌ 저장 실패: ${e.message || e}`);
    } finally {
      setSaving(false);
    }
  };

  const handleReset = () => {
    if (!window.confirm("기본 템플릿으로 초기화하시겠습니까?")) return;
    setEditContent(DEFAULT_TEMPLATE(selectedType));
    setDirty(true);
  };

  const selectedInfo = TEMPLATE_TYPES.find((t) => t.type === selectedType);
  const currentTemplate = templates.find((t) => t.type === selectedType);

  return (
    <div style={{ maxWidth: 1200 }}>
      {/* Toast */}
      {toastMsg && (
        <div
          style={{
            position: "fixed",
            bottom: 24,
            right: 24,
            background: toastType === "success" ? "var(--color-ink)" : "#ef4444",
            color: "var(--color-canvas)",
            padding: "12px 24px",
            borderRadius: 8,
            boxShadow: "0 4px 12px rgba(0,0,0,0.15)",
            zIndex: 1000,
            fontSize: 14,
            fontWeight: 500,
          }}
        >
          {toastMsg}
        </div>
      )}

      <PageHeader
        title="⚙️ 템플릿 편집기"
        contextLabel={`in ${vault}`}
        subtitle={`타입별 초안 템플릿(vault/_templates/{type}.md)을 인라인으로 편집·저장합니다. AI 초안 작성기에서 이 템플릿을 자동 참조합니다.`}
        bottomSpacing={24}
      />

      {loading ? (
        <p style={{ color: "var(--color-muted)", fontSize: 14 }}>템플릿 목록 불러오는 중…</p>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "220px 1fr", gap: 24 }}>
          {/* Left: type list */}
          <div
            style={{
              background: "var(--color-surface)",
              border: "1px solid var(--color-hairline)",
              borderRadius: 10,
              overflow: "hidden",
              height: "fit-content",
            }}
          >
            <div
              style={{
                padding: "12px 16px",
                borderBottom: "1px solid var(--color-hairline)",
                fontSize: 11,
                fontWeight: 700,
                textTransform: "uppercase",
                letterSpacing: "0.08em",
                color: "var(--color-muted)",
              }}
            >
              문서 타입 (9종)
            </div>
            {TEMPLATE_TYPES.map((t) => {
              const tpl = templates.find((tp) => tp.type === t.type);
              const isActive = selectedType === t.type;
              const hasTemplate = tpl?.exists;
              return (
                <button
                  key={t.type}
                  onClick={() => selectType(t.type)}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 10,
                    width: "100%",
                    padding: "10px 16px",
                    border: "none",
                    borderBottom: "1px solid var(--color-hairline)",
                    background: isActive ? "var(--bg-soft)" : "transparent",
                    cursor: "pointer",
                    textAlign: "left",
                    transition: "background 0.15s ease",
                  }}
                  onMouseEnter={(e) => {
                    if (!isActive) (e.currentTarget as HTMLElement).style.background = "var(--bg-soft)";
                  }}
                  onMouseLeave={(e) => {
                    if (!isActive) (e.currentTarget as HTMLElement).style.background = "transparent";
                  }}
                >
                  <span style={{ fontSize: 16 }}>{t.icon}</span>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div
                      style={{
                        fontSize: 13,
                        fontWeight: isActive ? 600 : 400,
                        color: isActive ? "var(--color-ink)" : "var(--color-ink)",
                      }}
                    >
                      {t.label}
                    </div>
                    <div style={{ fontSize: 11, color: "var(--color-muted)" }}>{t.desc}</div>
                  </div>
                  {hasTemplate ? (
                    <span
                      style={{
                        width: 7,
                        height: 7,
                        borderRadius: "50%",
                        background: "#22c55e",
                        flexShrink: 0,
                      }}
                      title="템플릿 저장됨"
                    />
                  ) : (
                    <span
                      style={{
                        width: 7,
                        height: 7,
                        borderRadius: "50%",
                        background: "var(--color-hairline)",
                        flexShrink: 0,
                      }}
                      title="템플릿 없음"
                    />
                  )}
                </button>
              );
            })}
          </div>

          {/* Right: editor */}
          <div
            style={{
              background: "var(--color-surface)",
              border: "1px solid var(--color-hairline)",
              borderRadius: 10,
              display: "flex",
              flexDirection: "column",
              overflow: "hidden",
            }}
          >
            {/* Editor header */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "14px 20px",
                borderBottom: "1px solid var(--color-hairline)",
                gap: 12,
              }}
            >
              <div>
                <h3 style={{ margin: 0, fontSize: 15, fontWeight: 600, color: "var(--color-ink)" }}>
                  {selectedInfo?.icon} {selectedType} 템플릿
                </h3>
                <span style={{ fontSize: 12, color: "var(--color-muted)" }}>
                  vault/_templates/{selectedType}.md
                  {currentTemplate?.exists ? (
                    <span style={{ color: "#22c55e", marginLeft: 8 }}>● 저장됨</span>
                  ) : (
                    <span style={{ color: "var(--color-muted)", marginLeft: 8 }}>○ 미저장</span>
                  )}
                  {dirty && (
                    <span style={{ color: "#f59e0b", marginLeft: 8 }}>● 수정됨</span>
                  )}
                </span>
              </div>
              <div style={{ display: "flex", gap: 8 }}>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleReset}
                  disabled={saving}
                >
                  🔄 기본값 복원
                </Button>
                <Button
                  variant="primary"
                  size="sm"
                  onClick={handleSave}
                  disabled={saving || !dirty}
                >
                  {saving ? "저장 중…" : "💾 저장"}
                </Button>
              </div>
            </div>

            {/* Help text */}
            <div
              style={{
                padding: "8px 20px",
                background: "rgba(99, 102, 241, 0.05)",
                borderBottom: "1px solid var(--color-hairline)",
                fontSize: 12,
                color: "var(--color-muted)",
                lineHeight: 1.5,
              }}
            >
              💡 <strong>{"{title}"}</strong>은 초안 생성 시 실제 제목으로, <strong>{"{date}"}</strong>는 오늘 날짜로 자동 치환됩니다.
              AI 초안 작성기는 이 템플릿을 기반으로 구조를 참조합니다.
            </div>

            {/* Textarea editor */}
            <textarea
              value={editContent}
              onChange={(e) => {
                setEditContent(e.target.value);
                setDirty(true);
              }}
              style={{
                flex: 1,
                width: "100%",
                minHeight: 480,
                fontFamily: "var(--font-mono, Monaco, 'Cascadia Code', monospace)",
                fontSize: 13,
                lineHeight: 1.65,
                color: "var(--color-ink)",
                background: "var(--color-canvas)",
                border: "none",
                outline: "none",
                padding: 20,
                resize: "vertical",
                boxSizing: "border-box",
              }}
              placeholder={`${selectedType} 타입 템플릿을 입력하세요. Frontmatter + 마크다운 형식으로 작성하세요.`}
            />
          </div>
        </div>
      )}
    </div>
  );
}
