import { describe, expect, it } from "vitest";
import source from "../src/components/NewVaultWizard.tsx?raw";
import appSource from "../src/App.tsx?raw";
import manageSource from "../src/routes/VaultManage.tsx?raw";

describe("plain vault creation dashboard contract", () => {
  it("does not inject bootstrap policy or MCP setup into a new vault", () => {
    expect(source).not.toContain("bootstrap: true");
    expect(source).not.toContain("profile: \"llm-wiki\"");
    expect(source).not.toContain("Agent / MCP Quick Start");
    expect(source).not.toContain("indexBody");
  });

  it("does not expose vault guide or bootstrap management UI", () => {
    expect(appSource).not.toContain("GuidesPage");
    expect(appSource).not.toContain('path="/guides"');
    expect(manageSource).not.toContain("GuidesViewer");
    expect(manageSource).not.toContain("bootstrapStatus");
  });
});
