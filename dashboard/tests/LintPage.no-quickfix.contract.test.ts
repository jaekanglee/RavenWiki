import { describe, expect, it } from "vitest";
import LintPageSrc from "../src/routes/LintPage.tsx?raw";

describe("LintPage quick-fix removal contract", () => {
  it("does not expose unsafe client-side quick fixes", () => {
    expect(LintPageSrc).not.toContain("퀵픽스");
    expect(LintPageSrc).not.toContain("handleFixBrokenLink");
    expect(LintPageSrc).not.toContain("handleFixFrontmatter");
    expect(LintPageSrc).not.toContain("stub 문서");
  });

  it("keeps wiki.db rebuild as the only mutating toolbar action", () => {
    expect(LintPageSrc).toContain("wiki.db 리빌드");
    expect(LintPageSrc).toContain("handleRebuild");
  });
});
