---
title: 모바일 앱 기술 스택 — Compose Multiplatform
created: 2026-07-24
type: decision
status: accepted
confidence: high
tags: [mobile, cmp, compose, android, ios, architecture]
---

# 모바일 앱 기술 스택 — Compose Multiplatform

> **결정**: Raven 모바일 앱(Android 메인, iOS 서브)은 **Compose Multiplatform(CMP)** 으로 구축한다. 데스크톱은 Tauri + React를 유지한다.

## 맥락

Raven은 Python 백엔드(API 서버) + React 프론트엔드 구조. 데스크톱 앱은 Tauri webview로 React Dashboard를 랩핑하여 이미 동작한다.

모바일 앱이 필요하나:

- **Tauri v2 모바일**은 webview 기반 — 네이티브 체감 부족
- **Flutter**는 서드파티 패키지 집합 느낌, Android에서 별도 렌더링 파이프라인
- **React Native**는 데스크톱 미지원, React 코드 재사용 가능하나 네이티브 위젯 매핑 간접
- **SwiftUI**는 Apple 전용, Android 불가
- **CMP**는 Android 네이티브 Compose 그 자체, iOS/Desktop도 지원

사용자(=Raven owner)가 **Android 네이티브 개발자**이며 Compose가 홈그라운드. Android가 1차 타겟, iOS는 서브(나중 보강).

## 결정

### 플랫폼별 스택

| 플랫폼 | 기술 | 백엔드 연결 |
|---|---|---|
| **데스크톱** | Tauri + React (현재 유지) | Python Core 내장 (loopback) |
| **Android (메인)** | CMP Compose | API 서버 HTTP 직접 |
| **iOS (서브)** | CMP Compose (나중 보강) | 동일 |
| **브라우저** | React Dashboard (현재 유지) | 동일 |

### 아키텍처

```
Raven/
├── raven/          ← Python 백엔드 (변경 없음)
├── dashboard/      ← React 웹 (변경 없음)
├── desktop/        ← Tauri (변경 없음)
└── app/            ← CMP (신규)
    ├── shared/     ← Compose UI + API 클라이언트 (Ktor)
    ├── android/    ← Android 앱
    └── ios/        ← iOS 앱 (나중)
```

### 핵심 원칙

1. **CMP 앱은 API 클라이언트** — Python Core 내장 ❌, 이미 돌아가는 API 서버(`http://<host>:8765`)에 HTTP로 연결
2. **데스크톱 Tauri 유지** — Orca처럼 자유로운 UI/UX 구현에 Tauri + React로 충분
3. **Android 1차, iOS 서브** — iOS 약점(Skia 렌더링, beta 성숙도)은 감수, 나중 보강
4. **백엔드 API 변경 없음** — 기존 REST API를 그대로 사용. 모바일 전용 엔드포인트 추가는 필요 시 별도 ADR

### CMP 선택 이유

- Android에서 **네이티브 Compose 그 자체** (별도 렌더링 ❌)
- 사용자가 Android 네이티브 개발자 — 학습 비용 0
- JetBrains 공식 생태계 — 서드파티 집합 느낌 ❌
- 한 코드베이스로 Android + iOS + (필요 시 Desktop)

### 비목표

- Flutter / React Native / SwiftUI 채택 ❌
- 모바일 앱에 Python Core 내장 ❌
- 오프라인 동기화 (초기 범위 ❌, 추후 검토)

## 결과

- `app/` 디렉토리 신규 생성 (Kotlin + Compose)
- Ktor + kotlinx.serialization으로 API 클라이언트 구현
- Android APK/AAB 빌드 파이프라인 구성
- iOS는 CMP iOS 타겟으로 나중 추가

## 관련

- [[raven-desktop-runtime-architecture]] — 데스크톱 Tauri 아키텍처
- [[deployment]] — Tailscale 배포 (모바일 접속 경로)
