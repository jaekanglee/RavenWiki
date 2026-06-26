# prompts/first-setup.md

> 신규 vault 부트스트랩용 프롬프트. **첫 실행 시 한 번만** 사용합니다.

---

## 용도

- vault를 처음 만들 때
- active vault를 전환할 때
- wiki.db를 처음 빌드할 때

---

## 프롬프트 (에이전트에 그대로 전달)

```
너는 내 vault의 운영자다. 다음 순서로 첫 vault를 세팅하라.

1. 현재 작업 디렉토리 아래에 새 vault를 만들 위치(vault 이름과 절대 경로)를
   사용자에게 한 줄로 확인하라.

2. Raven CLI가 설치되어 있는지 확인하라 (`raven --version`).
   없으면 "Raven CLI 미설치 — 설치 가이드를 참고하라"고만 보고하고 중단하라.

3. 설치되어 있으면 다음을 순서대로 수행하라:
   a) `raven vault create <name> <path>` — 새 vault 생성
   b) `raven vault list` — 생성 확인
   c) `raven vault use <name>` — active vault 전환
   d) `raven build` — wiki.db 빌드
   e) bootstrap 결과 확인:
      - 자동 복사되어야 하는 4종: SCHEMA.md, RULES.md, log.md, _meta/
      - 절대 복사되지 않아야 하는 것: OPERATIONS.md, agent/*, raven-policy.md

4. 사용자에게 다음을 한 줄로 보고하라:
   - 만든 vault 경로
   - active vault 이름
   - bootstrap으로 들어온 파일 4종
   - 다음 단계로 가능한 작업 (예: 첫 노트 저장, 외부 자료 ingest)

5. vault의 `log.md` 에 다음 형식으로 한 줄 append하라:
   `YYYY-MM-DD HH:mm | first-setup | <vault-name> created, bootstrap verified | <vault-path>`

지금 시작하라.
```

---

## Raven CLI 매핑

| 단계 | 명령 |
|---|---|
| vault 생성 | `raven vault create <name> <path>` |
| vault 목록 | `raven vault list` |
| active 전환 | `raven vault use <name>` |
| 인덱스 빌드 | `raven build` |
| 로그 확인 | `raven log list` |

---

## 체크리스트

- [ ] Raven CLI 설치 확인 (`raven --version`)
- [ ] vault 경로 사용자 확인
- [ ] `raven vault create` 성공
- [ ] `raven vault use` 성공
- [ ] `raven build` 성공
- [ ] bootstrap 4종(SCHEMA.md / RULES.md / log.md / _meta/) 존재
- [ ] 금지 파일(OPERATIONS.md / agent/* / raven-policy.md) 부재
- [ ] `log.md` 에 first-setup 한 줄 append