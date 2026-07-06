// useDebounced — 입력 즉시 반영 + 외부 effect는 지연 발화 (§13 재사용 hook, v0.7.69+).
//
// SearchBar / SearchPage 두 곳에서 동일하게 필요하던 패턴을 한 군데로 추출:
//   - 입력은 즉시 state에 반영 (controlled input UX)
//   - effect / fetch는 N ms 동안 입력이 멈춘 뒤에야 실행
//   - AbortController는 effect 측 책임 (hook은 delay만)
//
// 220ms는 SearchPage 기준 기존 값. SearchBar는 0ms(즉시 fetch)였지만 v0.7.69+
// 동일 220ms로 통일 — IME 조합 중 / 빠른 typing 시 /api/vaults/{}/search 폭주 방지.
import { useEffect, useState } from "react";

export function useDebounced<T>(value: T, delayMs: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = window.setTimeout(() => setDebounced(value), delayMs);
    return () => window.clearTimeout(timer);
  }, [value, delayMs]);
  return debounced;
}