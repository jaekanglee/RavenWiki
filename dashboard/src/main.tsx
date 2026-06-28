import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./styles/globals.css";

// v0.6.10 (P16): PWA registerType="prompt" handler.
// - vite.config.ts에서 registerType을 "prompt"로 변경했으므로,
//   새 SW가 감지되어도 자동 reload하지 않고 onNeedRefresh 콜백을 호출한다.
// - 사용자에게 confirm 다이얼로그를 보여, 승인 시에만 SW 활성화 + reload.
// - "쓸데없는 재로딩" 사용자 불만 해소 (앱 내렸다 다시 켰을 때 자동 reload ❌).
import { registerSW } from "virtual:pwa-register";

const updateSW = registerSW({
  onNeedRefresh() {
    // 사용자가 새로고침을 명시적으로 승인할 때만 활성화.
    if (
      window.confirm(
        "Raven에 새 버전이 있습니다. 지금 업데이트할까요?\n" +
          "(취소하면 다음 새로고침/앱 재실행 때 적용됩니다.)"
      )
    ) {
      updateSW(true);
    }
  },
  onOfflineReady() {
    console.info("[Raven] 오프라인 캐시 준비 완료 — 네트워크 없이도 동작합니다.");
  },
  onRegisterError(error: unknown) {
    console.warn("[Raven] SW 등록 오류:", error);
  },
});

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);