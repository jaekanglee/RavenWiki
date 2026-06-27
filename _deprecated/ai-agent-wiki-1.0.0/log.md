# log.md — 작업 로그 (append-only)

> 모든 vault 작업은 이 파일에 한 줄씩 append 됩니다.
> **절대 기존 줄을 삭제/수정하지 마세요.**

## 형식

```
YYYY-MM-DD HH:mm | <command> | <summary> | <linked files>
```

- `<command>`: `first-setup` | `save` | `ingest` | `query` | `lint` | `note` (메타) 중 하나
- `<summary>`: 한 줄 요약 (사람이 읽음)
- `<linked files>`: 생성/수정/조회한 파일 경로, 쉼표 구분

---

## Entries

<!-- 새 작업은 아래 줄에 append 하세요. 예시:
2026-06-27 12:00 | first-setup | vault "main" created, bootstrap verified | /path/to/vault
-->