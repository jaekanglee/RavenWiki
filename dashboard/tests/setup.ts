// v0.7.102: vitest global setup — jsdom 기본 한계 보완.
//
// 1. window.matchMedia stub — jsdom은 matchMedia 미제공. Sidebar/Layout 등
//    useMediaQuery 훅이 호출되며 v0.7.97 §6 Folder-hover-menu 회귀 테스트가
//    깨졌음. addEventListener/removeEventListener stub으로 해결.
//
// 2. window.scrollTo stub — jsdom 미구현. 일부 component가 호출 시 console.error.
//    no-op으로 처리.

if (typeof window !== "undefined") {
  // matchMedia stub — v0.7.97 §6 (Folder-hover-menu 회귀 가드 회복).
  if (typeof window.matchMedia !== "function") {
    Object.defineProperty(window, "matchMedia", {
      writable: true,
      configurable: true,
      value: (query: string) => ({
        matches: false,
        media: query,
        onchange: null,
        addListener: () => {},           // legacy API (deprecated)
        removeListener: () => {},        // legacy API
        addEventListener: () => {},
        removeEventListener: () => {},
        dispatchEvent: () => false,
      }),
    });
  }

  // scrollTo stub — jsdom 미구현.
  if (typeof window.scrollTo !== "function") {
    window.scrollTo = () => {};
  }
}
