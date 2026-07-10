import { describe, expect, it } from "vitest";
import LintPageSrc from "../src/routes/LintPage.tsx?raw";

describe("LintPage dynamic check registry contract", () => {
  it("does not hardcode a fixed check-id count for iteration", () => {
    expect(LintPageSrc).not.toMatch(/Array\.from\(\{\s*length:\s*(14|13|23)\s*\}/);
  });

  it("does not hardcode a static CHECK_NAMES map", () => {
    expect(LintPageSrc).not.toContain("CHECK_NAMES");
  });

  it("derives check names/order from summary.checks", () => {
    expect(LintPageSrc).toContain("summary?.checks");
  });

  it("keeps wiki.db rebuild as the only mutating toolbar action", () => {
    expect(LintPageSrc).toContain("wiki.db 리빌드");
    expect(LintPageSrc).toContain("handleRebuild");
  });
});
