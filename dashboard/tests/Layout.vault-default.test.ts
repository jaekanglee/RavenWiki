import { describe, expect, it } from "vitest";
import { chooseLayoutVault } from "../src/components/Layout";

const vaults = [
  { name: "raven-dev", path: "/tmp/raven-dev", mode: "agent", owner: "user", default: true },
  { name: "other", path: "/tmp/other", mode: "personal", owner: "user", default: false },
];

describe("Layout active vault fallback", () => {
  it("uses current vault when it exists", () => {
    expect(chooseLayoutVault(vaults, "other", "raven-dev")).toBe("other");
  });

  it("uses stored vault when current is empty", () => {
    expect(chooseLayoutVault(vaults, "", "other")).toBe("other");
  });

  it("falls back to API default when current and stored are empty", () => {
    expect(chooseLayoutVault(vaults, "", "")).toBe("raven-dev");
  });

  it("falls back to first vault when no default is marked", () => {
    const noDefault = vaults.map((v) => ({ ...v, default: false }));
    expect(chooseLayoutVault(noDefault, "", "missing")).toBe("raven-dev");
  });
});
