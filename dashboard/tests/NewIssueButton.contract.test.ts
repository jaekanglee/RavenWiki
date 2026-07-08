/* v0.7.112 — NewIssueButton 사람 운영자 발행 폼 contract.
 *
 * Agent는 `type: issue` 페이지를 직접 만들 수 없다 (PWW §7.1). 사람 운영자가
 * Dashboard에서 발행할 때 SCHEMA 9종 issue 본문 템플릿, severity/kind 메타,
 * wikilink footer를 정해진 형태로 자동 채워주는지가 핵심.
 */
import { describe, it, expect } from "vitest";
import NewIssueButtonSrc from "../src/components/NewIssueButton.tsx?raw";
import SidebarSrc from "../src/components/Sidebar.tsx?raw";

describe("NewIssueButton issue publisher", () => {
  it("is wired into the Sidebar vault row", () => {
    expect(SidebarSrc).toContain('<NewIssueButton vault={vault.name}');
  });

  it("uses SCHEMA issue template (BLUF / 상태 / 문제 / 원인 / 해결 / 관련)", () => {
    expect(NewIssueButtonSrc).toContain("## 상태");
    expect(NewIssueButtonSrc).toContain("## 문제 상황");
    expect(NewIssueButtonSrc).toContain("## 원인 분석");
    expect(NewIssueButtonSrc).toContain("## 해결 방안");
    expect(NewIssueButtonSrc).toContain("## 관련");
  });

  it("forces type: issue + emits severity/kind tags", () => {
    expect(NewIssueButtonSrc).toContain('type: "issue"');
    expect(NewIssueButtonSrc).toContain('"issue", severity, kind');
  });

  it("auto-generates dated slug (YYYY-MM-DD-{slugified-title})", () => {
    expect(NewIssueButtonSrc).toContain("ISO_TODAY");
    expect(NewIssueButtonSrc).toMatch(/today.*safe|today.*-.*safe/);
  });

  it("exposes only the people-only severity + kind dimensions", () => {
    expect(NewIssueButtonSrc).toContain('"high"');
    expect(NewIssueButtonSrc).toContain('"medium"');
    expect(NewIssueButtonSrc).toContain('"low"');
    expect(NewIssueButtonSrc).toContain('"bug"');
    expect(NewIssueButtonSrc).toContain('"stale"');
    expect(NewIssueButtonSrc).toContain('"orphan"');
  });
});
