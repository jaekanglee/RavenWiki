---
title: "ADR 2026-07-26: Desktop System Tray & Background Execution"
created: 2026-07-26
type: adr
tags: [desktop, tauri, lifecycle]
---

# ADR 2026-07-26: Desktop System Tray & Background Execution

> **결정 (BLUF):** Raven 데스크톱 앱(Tauri)에 시스템 트레이(Menu Bar) 기능을 도입하여 창 숨김(Hide)을 지원하되, Dock 아이콘 유지(Regular 모드) 및 Cmd+Q 정상 종료를 허용하여 macOS 네이티브 UX 표준을 준수하면서 백그라운드 서버를 유지합니다.

## 맥락 (Context)

현재 Raven 데스크톱 앱은 창(Window)의 수명 주기가 앱 전체의 수명 주기와 묶여 있습니다. 데스크톱 환경으로 넘어온 사용자는 Ollama나 Docker Desktop처럼 데스크톱 창을 닫아도 백그라운드에서 API(Python Core)가 유지되어 다른 에이전트가 24시간 접근할 수 있기를 원합니다.
단, 백그라운드 데몬화 시 발생할 수 있는 창 복원(Reopen) 이슈와 글로벌 단축키(Cmd+Q) 등 macOS HIG(Human Interface Guidelines)의 엣지 케이스를 모두 고려해야 합니다.

## 결정 (Decision)

1. **시스템 트레이(Tray Icon) 추가**:
   - `tauri`의 `tray-icon` feature를 활성화합니다.
   - 상단 메뉴바에 Raven 아이콘을 띄우고 `Open Dashboard`, `Quit Raven` 메뉴를 제공합니다.
2. **창 닫기(Close) 가로채기**:
   - 데스크톱 창의 `X` 버튼 클릭 시 창을 완전히 파괴(Destroy)하지 않고 숨김(Hide) 처리합니다.
   - WebView 상태가 유지되어 트레이에서 다시 열 때 로딩 딜레이 없이 즉시 화면이 나타납니다.
3. **Dock 아이콘 유지 (Regular Activation Policy)**:
   - 메뉴바 전용(Accessory) 모드는 Cmd+Tab 창 전환 누락 및 클립보드(Cmd+C/V) 포커스 상실 등 고질적 버그를 유발합니다.
   - Discord나 Slack처럼 Dock 아이콘을 그대로 유지하는 일반(Regular) 모드를 채택하여 OS 윈도우 매니저와의 충돌을 피합니다.
4. **Dock 클릭 시 창 복원 (`RunEvent::Reopen`) 처리**:
   - 창이 숨겨진 상태에서 하단 Dock 아이콘을 클릭하면 앱이 다시 창을 표시하도록 이벤트 루프에 `Reopen` 훅을 명시적으로 추가합니다.
5. **Cmd+Q 정상 종료 지원 (`RunEvent::ExitRequested`)**:
   - 앱이 백그라운드에 있다고 해서 Cmd+Q(완전 종료) 단축키를 무시하면 사용자 경험이 크게 훼손됩니다.
   - 트레이의 `Quit` 클릭 및 Cmd+Q 단축키 발생 시에는 앱과 Python Core 프로세스가 모두 깔끔하게 종료(`core.stop()`)되도록 허용합니다.

## 결과 (Consequences)

- **장점**: UI 창을 숨긴 상태로 Raven MCP와 API를 가볍고 쾌적하게 24시간 가동할 수 있습니다.
- **장점**: Reopen 및 Cmd+Q 처리를 통해 백그라운드 동작과 네이티브 macOS UX(Discord 스타일)를 완벽하게 조화시켰습니다.
- **단점**: Dock에 아이콘이 상주하므로 완전한 메뉴바 전용 앱(Ollama 스타일)과는 미세한 차이가 있으나, 버그 없는 가장 안정적인 타협안입니다.
