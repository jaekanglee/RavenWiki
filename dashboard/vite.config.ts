import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { VitePWA } from "vite-plugin-pwa";

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    VitePWA({
      registerType: "autoUpdate",
      // v0.6.9 (P14 fix): PWA 캐시로 인한 stale UI 봉인.
      // - navigateFallback: null → SPA 라우트가 캐시된 index.html로 fallback되지 않음
      // - /api/* NetworkFirst → API는 항상 네트워크 우선 (옛 JSON 봉인)
      workbox: {
        navigateFallback: null,
        runtimeCaching: [
          {
            urlPattern: /\/api\//,
            handler: "NetworkFirst",
            options: {
              cacheName: "api-cache",
              expiration: { maxEntries: 50, maxAgeSeconds: 60 * 60 * 24 },
            },
          },
        ],
      },
      manifest: {
        name: "Wiki Dashboard",
        short_name: "Wiki",
        theme_color: "#22d3ee",
        icons: [{ src: "/favicon.svg", sizes: "any", type: "image/svg+xml" }],
      },
    }),
  ],
  server: {
    port: 5173,
    host: true,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8765",
        changeOrigin: true,
      },
    },
  },
  test: {
    globals: true,
    environment: "jsdom",
  },
});
