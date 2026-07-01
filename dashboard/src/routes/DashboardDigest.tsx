import { useEffect, useState } from "react";
import { useOutletContext, Link } from "react-router-dom";
import { fetchDigest, type DigestPayload, type DigestDayBucket } from "../lib/api";
import { DigestCard } from "../components/DigestCard";

/**
 * DashboardDigest — 사람 운영자 진입 시 '오늘 vault 상태' 한 화면 요약 (M5 F5).
 *
 * 4개 카드 grid:
 *   1. 오늘의 활동 — 오늘 작성/수정된 페이지 (log entries, action filter)
 *   2. 이번 주 활동 — 7일간 막대 차트 + 총 카운트
 *   3. Lint 상태 — critical/warning/info + top 3 issues
 *   4. 최근 노트 + vault 통계 — 최근 5개 페이지 + 타입 breakdown
 *
 * active vault 는 Layout 의 outlet context 로 주입됨.
 */
export function DashboardDigest() {
  const { vault } = useOutletContext<{ vault: string }>();
  const [days, setDays] = useState<number>(7);
  const [data, setData] = useState<DigestPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetchDigest(vault, days)
      .then((d) => {
        if (cancelled) return;
        if (!d) {
          setError("digest API 응답 실패");
        } else {
          setData(d);
        }
      })
      .catch((e) => {
        if (!cancelled) setError(`${e}`);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [vault, days]);

  return (
    <div style={{ maxWidth: 1120 }}>
      {/* Header — modest, h1 ≤ 28px */}
      <section style={{ paddingTop: 16, paddingBottom: 32 }}>
        <h1 style={{ marginBottom: 8 }}>Daily Digest</h1>
        <p className="text-body" style={{ fontSize: 16, maxWidth: 640 }}>
          {vault} vault 의 오늘 상태 · 이번 주 활동 · lint 헬스체크를 한 화면에
          모았습니다. 운영자가 매일 Dashboard 를 열 때 가장 먼저 보는 화면입니다.
        </p>
      </section>

      {loading && <p className="text-muted">Loading…</p>}
      {error && <p style={{ color: "var(--color-error-text)" }}>{error}</p>}

      {data && (
        <>
          {/* Meta row + days selector */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 16,
              marginBottom: 16,
              fontSize: 13,
              color: "var(--color-muted)",
              flexWrap: "wrap",
            }}
          >
            <span>generated {data.generated_at}</span>
            <span style={{ marginLeft: "auto" }}>
              윈도우&nbsp;
              <select
                value={days}
                onChange={(e) => setDays(Number(e.target.value))}
                style={{
                  border: "1px solid var(--color-hairline-strong)",
                  borderRadius: "var(--radius-full)",
                  padding: "4px 12px",
                  fontSize: 13,
                  background: "var(--color-canvas)",
                  color: "var(--color-ink)",
                  fontFamily: "inherit",
                  outline: "none",
                }}
              >
                {[3, 7, 14, 30].map((d) => (
                  <option key={d} value={d}>
                    {d}일
                  </option>
                ))}
              </select>
            </span>
          </div>

          {/* 2x2 grid: digest cards */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(360px, 1fr))",
              gap: 16,
            }}
          >
            <TodayCard today={data.today} total={data.today.length} />
            <WeekCard buckets={data.this_week} days={days} />
            <LintCard lint={data.lint} vault={vault} />
            <RecentCard stats={data.stats} vault={vault} />
          </div>
        </>
      )}
    </div>
  );
}

// ────────────────────────── Card 1: 오늘의 활동 ──────────────────────────

function TodayCard({ today, total }: { today: DigestPayload["today"]; total: number }) {
  return (
    <DigestCard
      label="오늘의 활동"
      title={`${total}개 entry`}
      accent={total > 0}
      right={
        <Link to="/log" className="link-muted">
          전체 로그 →
        </Link>
      }
    >
      {today.length === 0 ? (
        <p className="text-muted" style={{ fontSize: 13 }}>
          오늘은 아직 작업이 없습니다.
        </p>
      ) : (
        <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
          {today.slice(0, 10).map((e, i) => (
            <li
              key={i}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                padding: "6px 0",
                borderBottom:
                  i === Math.min(9, today.length - 1)
                    ? "none"
                    : "1px solid var(--color-hairline)",
                fontSize: 13,
              }}
            >
              <span
                className="chip-strong"
                style={{
                  background: actionBg(e.action),
                  fontFamily: "ui-monospace, SFMono-Regular, monospace",
                }}
              >
                {e.action}
              </span>
              <span
                style={{
                  flex: 1,
                  minWidth: 0,
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                  color: "var(--color-ink)",
                }}
                title={e.subject}
              >
                {e.subject}
              </span>
            </li>
          ))}
        </ul>
      )}
    </DigestCard>
  );
}

function actionBg(a: string): string {
  // destructive actions 는 Rausch accent, 나머지는 ink
  if (a === "archive" || a === "delete") return "var(--color-primary)";
  return "var(--color-ink)";
}

// ────────────────────────── Card 2: 이번 주 활동 ──────────────────────────

function WeekCard({ buckets, days }: { buckets: DigestDayBucket[]; days: number }) {
  const max = Math.max(1, ...buckets.map((b) => b.count));
  const total = buckets.reduce((acc, b) => acc + b.count, 0);
  return (
    <DigestCard
      label="이번 주 활동"
      title={`${total}개 entry · 최근 ${days}일`}
    >
      <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
        {buckets.map((b) => {
          const w = `${(b.count / max) * 100}%`;
          const isToday = b.date === todayIso();
          return (
            <div
              key={b.date}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                fontSize: 12,
              }}
            >
              <span
                style={{
                  fontFamily: "ui-monospace, SFMono-Regular, monospace",
                  color: isToday ? "var(--color-primary)" : "var(--color-muted)",
                  fontWeight: isToday ? 700 : 400,
                  width: 72,
                  flexShrink: 0,
                }}
              >
                {b.date.slice(5)}
                {isToday && " · today"}
              </span>
              <div
                style={{
                  flex: 1,
                  background: "var(--color-surface-strong)",
                  borderRadius: 4,
                  height: 10,
                  overflow: "hidden",
                }}
              >
                <div
                  style={{
                    width: w,
                    height: "100%",
                    background: isToday
                      ? "var(--color-primary)"
                      : "var(--color-ink)",
                    transition: "width 0.2s ease",
                  }}
                  title={`${b.count} entries`}
                />
              </div>
              <span
                style={{
                  fontFamily: "ui-monospace, SFMono-Regular, monospace",
                  width: 24,
                  textAlign: "right",
                  color: "var(--color-ink)",
                  fontWeight: b.count > 0 ? 600 : 400,
                }}
              >
                {b.count}
              </span>
            </div>
          );
        })}
      </div>
      {total === 0 && (
        <p className="text-muted" style={{ fontSize: 12, marginTop: 8 }}>
          최근 {days}일간 활동 없음
        </p>
      )}
    </DigestCard>
  );
}

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

// ────────────────────────── Card 3: Lint 상태 ──────────────────────────

function LintCard({
  lint,
  vault,
}: {
  lint: DigestPayload["lint"];
  vault: string;
}) {
  const { counts, top_issues } = lint;
  const allIssues = [
    ...top_issues.critical,
    ...top_issues.warning,
    ...top_issues.info,
  ];
  return (
    <DigestCard
      label="Lint 상태"
      title={lint.ok ? "✓ critical 없음" : `⚠ critical ${counts.critical}건`}
      accent={!lint.ok}
      right={
        <Link to="/lint" className="link-muted">
          Lint 페이지 →
        </Link>
      }
    >
      {/* severity counts */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(3, 1fr)",
          gap: 8,
        }}
      >
        <SeverityCell label="critical" count={counts.critical} accent />
        <SeverityCell label="warning" count={counts.warning} />
        <SeverityCell label="info" count={counts.info} />
      </div>

      {/* top issues */}
      {allIssues.length > 0 ? (
        <ul style={{ listStyle: "none", padding: 0, margin: "12px 0 0" }}>
          {allIssues.map((iss, i) => (
            <li
              key={i}
              style={{
                padding: "4px 0",
                fontSize: 12,
                borderTop: i === 0 ? "1px solid var(--color-hairline)" : "none",
                display: "flex",
                gap: 8,
                alignItems: "center",
              }}
            >
              <span
                style={{
                  fontFamily: "ui-monospace, SFMono-Regular, monospace",
                  fontSize: 11,
                  fontWeight: 700,
                  color: "var(--color-muted)",
                  width: 24,
                }}
              >
                {iss.id}
              </span>
              <Link
                to={`/page/${vault}/${iss.slug}`}
                className="link-ink"
                style={{
                  fontFamily: "ui-monospace, SFMono-Regular, monospace",
                  fontSize: 12,
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                  flex: 1,
                  minWidth: 0,
                }}
                title={`${iss.slug} — ${iss.message}`}
              >
                {iss.slug}
              </Link>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-muted" style={{ fontSize: 12, marginTop: 8 }}>
          모든 check 통과 ({counts.total} 이슈 없음)
        </p>
      )}
    </DigestCard>
  );
}

function SeverityCell({
  label,
  count,
  accent = false,
}: {
  label: string;
  count: number;
  accent?: boolean;
}) {
  return (
    <div
      style={{
        background: accent && count > 0 ? "var(--cds-tag-blue-bg)" : "var(--cds-background)",
        border: "1px solid var(--cds-border-subtle)",
        borderRadius: "var(--radius-md)",
        padding: 12,
      }}
    >
      <div
        style={{
          fontSize: 10,
          fontWeight: 700,
          letterSpacing: "0.32px",
          textTransform: "uppercase",
          color: "var(--color-muted)",
        }}
      >
        {label}
      </div>
      <div
        style={{
          fontSize: 22,
          fontWeight: 700,
          color: accent && count > 0 ? "var(--color-primary)" : "var(--color-ink)",
          marginTop: 4,
        }}
      >
        {count}
      </div>
    </div>
  );
}

// ────────────────────────── Card 4: 최근 노트 + 통계 ──────────────────────────

function RecentCard({
  stats,
  vault,
}: {
  stats: DigestPayload["stats"];
  vault: string;
}) {
  const typeEntries = Object.entries(stats.types).sort((a, b) => b[1] - a[1]);
  return (
    <DigestCard
      label="최근 노트"
      title={`${stats.total_pages} pages · ${typeEntries.length} types`}
      right={
        <Link to="/search" className="link-muted">
          검색 →
        </Link>
      }
    >
      {/* recent pages */}
      {stats.recent_pages.length === 0 ? (
        <p className="text-muted" style={{ fontSize: 13 }}>
          아직 페이지가 없습니다.
        </p>
      ) : (
        <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
          {stats.recent_pages.map((p, i) => (
            <li
              key={p.slug}
              style={{
                padding: "8px 0",
                borderBottom:
                  i === stats.recent_pages.length - 1
                    ? "none"
                    : "1px solid var(--color-hairline)",
                display: "flex",
                alignItems: "center",
                gap: 8,
              }}
            >
              <span className="chip" style={{ flexShrink: 0 }}>
                {p.type}
              </span>
              <Link
                to={`/page/${vault}/${p.slug}`}
                className="link-ink"
                style={{
                  flex: 1,
                  minWidth: 0,
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                  fontSize: 13,
                  fontWeight: 500,
                }}
                title={p.slug}
              >
                {p.title}
              </Link>
              {p.updated && (
                <span
                  style={{
                    fontSize: 11,
                    color: "var(--color-muted)",
                    fontFamily: "ui-monospace, SFMono-Regular, monospace",
                    flexShrink: 0,
                  }}
                >
                  {p.updated.slice(5)}
                </span>
              )}
            </li>
          ))}
        </ul>
      )}

      {/* vault summary footer */}
      <div
        style={{
          display: "flex",
          gap: 12,
          marginTop: 12,
          paddingTop: 12,
          borderTop: "1px solid var(--color-hairline)",
          fontSize: 12,
          color: "var(--color-muted)",
          flexWrap: "wrap",
        }}
      >
        <span>
          broken: <strong style={{ color: stats.broken_links > 0 ? "var(--color-primary)" : "var(--color-ink)" }}>{stats.broken_links}</strong>
        </span>
        <span>
          missing: <strong style={{ color: "var(--color-ink)" }}>{stats.missing_links}</strong>
        </span>
        <span style={{ marginLeft: "auto", fontSize: 11 }}>
          vault: <code style={{ color: "var(--color-ink)" }}>{vault}</code>
        </span>
      </div>
    </DigestCard>
  );
}