"""raven.curator — Stateless Curator + Change Set 큐레이션.

v3 합의안 (Claude + Codex):
- Curator = stateless workflow
- 상태 = curation_history.db (외부)
- 범위 = collections.yaml (vault 내부 _meta/)
- 실행 대상 = git diff 기반 change set
- vault 동적성 = collection sync (warning+continue)

모듈:
- schema   — collections.yaml 로드/검증
- db       — curation_history.db 6 테이블
- hash     — payload_hash canonical form
- curator  — execute() 본체 (Step 4)
- sync     — collection sync CLI (Step 5)
- lifecycle — grace period + soft-archive (Step 6)
- reports  — reviews 인덱스 + log.md append + dry-run 리포트 (Step 7)
"""
