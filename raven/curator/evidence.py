"""raven.curator.evidence — 의미적 교차점 자동 인퍼런스 엔진 및 관계 근거(Evidence) 추출기."""
from __future__ import annotations

import re
from typing import List, Tuple

def extract_evidence_and_reason(
    source_content: str,
    target_content: str,
    source_title: str,
    target_title: str,
    source_slug: str,
    target_slug: str,
    relation_type: str,
) -> Tuple[List[str], str]:
    """두 문서의 내용과 메타데이터를 분석하여 uses 또는 depends_on 관계에 대한 evidence와 reason을 자동으로 추출합니다."""
    evidence_list = []
    reason = ""

    # 1. 소스 코드 내 import 라인 발굴
    # target_slug의 베이스이름을 대상으로 검사
    target_base = target_slug.split("/")[-1].replace(".md", "")
    
    # 정규식 패턴 생성 (대소문자 구분 없이 다양한 언어의 import/require 구문 대응)
    import_patterns = [
        re.compile(rf"import\s+.*\s+from\s+['\"][^'\"]*{target_base}[^'\"]*['\"]", re.IGNORECASE),
        re.compile(rf"import\s+['\"][^'\"]*{target_base}[^'\"]*['\"]", re.IGNORECASE),
        re.compile(rf"from\s+['\"][^'\"]*{target_base}[^'\"]*['\"]\s+import", re.IGNORECASE),
        re.compile(rf"require\(\s*['\"][^'\"]*{target_base}[^'\"]*['\"]\s*\)", re.IGNORECASE),
        re.compile(rf"import\s+({target_base}|{target_base.replace('-', '_')})", re.IGNORECASE),
        re.compile(rf"from\s+.*\s+import\s+.*({target_base}|{target_base.replace('-', '_')})", re.IGNORECASE),
    ]

    lines = source_content.splitlines()
    for line in lines:
        for pattern in import_patterns:
            if pattern.search(line):
                evidence_list.append(line.strip())
                break

    if evidence_list:
        reason = f"소스 코드 내 import 구문에서 '{target_title}'({target_slug}) 모듈에 대한 참조를 발견했습니다."
        return evidence_list, reason

    # 2. 두 문서의 본문 중 서로 연관되는 구절(Text Span) 발굴
    target_names = [target_title, target_slug, target_base]
    
    # target_content의 frontmatter에서 aliases도 파싱해서 이름 목록에 추가
    aliases = []
    fm_match = re.match(r"^---\s*\n(.*?)\n---\s*\n", target_content, re.DOTALL)
    if fm_match:
        fm_text = fm_match.group(1)
        for fm_line in fm_text.splitlines():
            if fm_line.startswith("aliases:"):
                val = fm_line.split(":", 1)[1].strip()
                if val.startswith("[") and val.endswith("]"):
                    aliases = [v.strip().strip("'\"") for v in val[1:-1].split(",")]
                else:
                    aliases = [val.strip().strip("'\"")]
    
    target_names.extend(aliases)
    target_names = list(set([n for n in target_names if n]))

    # 문장 단위로 분할하여 매칭 구절 검색
    sentences = []
    raw_sentences = re.split(r'(?<=[.!?])\s+|\n+', source_content)
    for s in raw_sentences:
        s_clean = s.strip()
        if len(s_clean) > 5:
            sentences.append(s_clean)

    for s in sentences:
        for name in target_names:
            if name.lower() in s.lower() or f"[[{target_slug}" in s or f"[[{target_base}" in s:
                evidence_list.append(s)
                break
        if len(evidence_list) >= 3:  # 최대 3개까지만 수집
            break

    if evidence_list:
        reason = f"본문 텍스트 내에서 '{target_title}'에 대해 언급하는 구절(Text Span)을 발견하여 관계를 맺습니다."
        return evidence_list, reason

    # 3. Fallback: 매칭되는 구절이나 import가 없을 때
    fallback_evidence = f"[[{target_slug}]]"
    fallback_reason = f"자동 관계 인퍼런스를 통해 '{source_title}' 문서가 '{target_title}' 문서의 기능을 {relation_type}하는 것으로 파악되었습니다."
    
    # target_content에서 설명이 될 만한 첫 줄 추출
    target_desc = ""
    for tl in target_content.splitlines():
        tl_clean = tl.strip()
        if tl_clean and not tl_clean.startswith("-") and not tl_clean.startswith("#") and "title:" not in tl_clean and "type:" not in tl_clean:
            target_desc = tl_clean
            break
            
    ev_spans = [fallback_evidence]
    if target_desc:
        ev_spans.append(f"대상 문서 요약: {target_desc[:100]}...")

    return ev_spans, fallback_reason
