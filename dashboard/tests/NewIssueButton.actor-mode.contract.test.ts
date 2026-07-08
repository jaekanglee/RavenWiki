/* v0.7.113 — NewIssueButton agent 자율 발행 모드 (ADR-2026-07-08)
 *
 * v0.7.112 폼은 사람 운영자만 호출 가능했지만, ADR-2026-07-08로 agent가
 * `actor="agent"` 모드로도 호출 가능. 발행 시 status=draft default,
 * tags에 draft 자동, log.md audit은 사람/agent 공통.
 */
import { describe, it, expect } from "vitest";
import NewIssueButtonSrc from "../src/components/NewIssueButton.tsx?raw";

describe("NewIssueButton agent autonomy (ADR-2026-07-08)", () => {
  it("accepts actor: 'human' | 'agent' prop", () => {
    expect(NewIssueButtonSrc).toMatch(/actor\?:\s*"human"\s*\|\s*"agent"/);
  });

  it("emits status=draft as default (draft tag included)", () => {
    expect(NewIssueButtonSrc).toContain('"issue", severity, kind, "draft"');
  });

  it("stamps actor metadata into published body (audit trail)", () => {
    expect(NewIssueButtonSrc).toContain("actor=${actor}");
    expect(NewIssueButtonSrc).toContain("published_at=");
  });

  it("shows actor-aware tooltip", () => {
    expect(NewIssueButtonSrc).toContain("agent 자율");
    expect(NewIssueButtonSrc).toContain("사람 운영자");
  });
});
