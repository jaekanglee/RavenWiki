"""tests.curator.test_evidence — extract_evidence_and_reason 테스트."""
from __future__ import annotations

from raven.curator.evidence import extract_evidence_and_reason

def test_extract_implements_relationship():
    # Source가 Target을 상속/구현하는 경우
    source_content = """---
title: AuthRepositoryImpl
type: concept
---
class AuthRepositoryImpl(AuthRepository):
    def save(self):
        pass
"""
    target_content = """---
title: AuthRepository
type: concept
---
interface AuthRepository:
    def save(self):
        pass
"""
    
    evidence, reason = extract_evidence_and_reason(
        source_content=source_content,
        target_content=target_content,
        source_title="AuthRepositoryImpl",
        target_title="AuthRepository",
        source_slug="content/auth_repo_impl",
        target_slug="content/auth_repo",
        relation_type="implements"
    )
    
    assert len(evidence) == 1
    assert "class AuthRepositoryImpl(AuthRepository):" in evidence[0]
    assert "AuthRepositoryImpl" in reason
    assert "AuthRepository" in reason

def test_extract_related_relationship():
    # 공통 태그 및 고빈도 키워드 매칭
    source_content = """---
title: Backend Auth
type: concept
tags: [backend, security, oauth]
---
이 문서는 backend 시스템의 oauth 기반 로그인 처리를 설명합니다.
인증 토큰을 안전하게 관리해야 합니다.
"""
    target_content = """---
title: Frontend Login
type: concept
tags: [frontend, security, oauth]
---
웹 프론트엔드에서 oauth 로그인을 구현하기 위해 인증 토큰을 backend로 전송합니다.
"""
    
    evidence, reason = extract_evidence_and_reason(
        source_content=source_content,
        target_content=target_content,
        source_title="Backend Auth",
        target_title="Frontend Login",
        source_slug="content/backend_auth",
        target_slug="content/frontend_login",
        relation_type="related"
    )
    
    assert any("공통 태그" in ev for ev in evidence)
    assert any("공통 핵심 키워드" in ev for ev in evidence)
    assert "공통 태그" in reason or "공통 키워드" in reason
