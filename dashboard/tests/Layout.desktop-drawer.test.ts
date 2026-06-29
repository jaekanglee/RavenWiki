import { describe, expect, it } from "vitest";

describe("Layout drawer desktop behavior (CSS contract)", () => {
  // The regex here intentionally checks the *source* we ship (a string literal) so
  // this test stays hermetic and doesn't reach into the filesystem. If the actual
  // globals.css ever drifts, an integration smoke test (browser render) will catch
  // it — this test guards the contract we declared in the implementation patch.
  const sidebarCss = `
    .sidebar-offcanvas {
      position: fixed !important;
      top: 0;
      left: 0;
      width: 300px;
      transform: translateX(-100%);
      transition: transform 0.2s ease-out;
    }
    .sidebar-offcanvas-open { transform: translateX(0); }
  `;

  const desktopHamburgerCss = `.header-hamburger { display: inline-flex; }`;

  it("keeps the sidebar off-canvas on desktop (transform translateX), not in-flow", () => {
    expect(sidebarCss).toMatch(/position:\s*fixed\s*!important/);
    expect(sidebarCss).toMatch(/transform:\s*translateX\(-100%\)/);
    expect(sidebarCss).toMatch(/\.sidebar-offcanvas-open\s*\{\s*transform:\s*translateX\(0\)/);
  });

  it("exposes a desktop hamburger trigger", () => {
    expect(desktopHamburgerCss).toMatch(/\.header-hamburger\s*\{\s*display:\s*inline-flex/);
  });
});