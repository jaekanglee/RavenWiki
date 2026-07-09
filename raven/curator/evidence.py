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
    """두 문서의 내용과 메타데이터를 분석하여 다양한 관계에 대한 evidence와 reason을 자동으로 추출합니다."""
    from raven.core.frontmatter import parse as fm_parse
    
    source_meta, source_body = fm_parse(source_content)
    target_meta, target_body = fm_parse(target_content)

    evidence_list = []
    reason = ""

    target_base = target_slug.split("/")[-1].replace(".md", "")
    source_base = source_slug.split("/")[-1].replace(".md", "")

    # 1. implements / implemented_by 관계 특화 처리
    if relation_type in ("implements", "implemented_by"):
        # implements: source가 target을 구현 (즉, source가 구현체, target이 부모/인터페이스)
        # implemented_by: target이 source를 구현 (즉, target이 구현체, source가 부모/인터페이스)
        is_implements = relation_type == "implements"
        search_body = source_body if is_implements else target_body
        search_title = target_title if is_implements else source_title
        
        base_names = []
        if is_implements:
            base_names = [target_base, target_title]
        else:
            base_names = [source_base, source_title]
            
        implements_patterns = []
        for name in base_names:
            if not name:
                continue
            implements_patterns.extend([
                re.compile(rf"class\s+\w+\s*\([^)]*{name}[^)]*\)", re.IGNORECASE),
                re.compile(rf"class\s+\w+\s+implements\s+[^{{\n]*{name}", re.IGNORECASE),
                re.compile(rf"class\s+\w+\s+extends\s+[^{{\n]*{name}", re.IGNORECASE),
                re.compile(rf"interface\s+\w+\s+extends\s+[^{{\n]*{name}", re.IGNORECASE),
                re.compile(rf"\bextends\s+{name}\b", re.IGNORECASE),
                re.compile(rf"\bimplements\s+{name}\b", re.IGNORECASE),
            ])
        
        lines = search_body.splitlines()
        for line in lines:
            for pattern in implements_patterns:
                if pattern.search(line):
                    evidence_list.append(line.strip())
                    break
        
        if evidence_list:
            if is_implements:
                reason = f"클래스 상속 및 인터페이스 구현부 구문에서 '{source_title}'이(가) '{target_title}'을(를) 구현/상속함을 발견했습니다."
            else:
                reason = f"클래스 상속 및 인터페이스 구현부 구문에서 '{target_title}'이(가) '{source_title}'을(를) 구현/상속함을 발견했습니다."
            return evidence_list, reason

    # 2. related 관계 특화 처리 (교차 태그 및 고빈도 키워드)
    if relation_type == "related":
        # 1) 교차 태그 (tags) 매칭
        def get_tags_set(meta: dict) -> set[str]:
            tags = meta.get("tags", [])
            if isinstance(tags, str):
                return set([x.strip() for x in tags.split(",") if x.strip()])
            elif isinstance(tags, list):
                return set([str(x).strip() for x in tags if x])
            return set()
            
        source_tags = get_tags_set(source_meta)
        target_tags = get_tags_set(target_meta)
        common_tags = source_tags.intersection(target_tags)
        
        # 2) 고빈도 키워드 매칭
        def extract_keywords(body: str) -> List[Tuple[str, int]]:
            words = re.findall(r"\b[a-zA-Z가-힣]{2,15}\b", body.lower())
            stopwords = {
                "이다", "있다", "하는", "통해", "대한", "위해", "의해", "그리고", "하지만",
                "이것", "저것", "그것", "또한", "매우", "가장", "으로", "에서", "합니다",
                "하고", "하여", "에서", "이고", "하며", "등을", "등의", "것을", "것이", "있는",
                "this", "that", "with", "from", "have", "been", "were"
            }
            word_counts = {}
            for w in words:
                if w not in stopwords:
                    word_counts[w] = word_counts.get(w, 0) + 1
            sorted_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)
            return sorted_words[:15]
            
        source_kws = dict(extract_keywords(source_body))
        target_kws = dict(extract_keywords(target_body))
        common_kws = set(source_kws.keys()).intersection(set(target_kws.keys()))
        
        evidence_parts = []
        reason_parts = []
        
        if common_tags:
            evidence_parts.append(f"공통 태그: {', '.join(sorted(common_tags))}")
            reason_parts.append(f"공통 태그 [{', '.join(sorted(common_tags))}]")
            
        if common_kws:
            sorted_common_kws = sorted(list(common_kws), key=lambda x: source_kws[x] + target_kws[x], reverse=True)
            kws_to_show = sorted_common_kws[:5]
            evidence_parts.append(f"공통 핵심 키워드: {', '.join(kws_to_show)}")
            reason_parts.append(f"고빈도 공통 키워드 [{', '.join(kws_to_show)}]")
            
        if evidence_parts:
            reason = f"두 문서가 동일한 " + " 및 ".join(reason_parts) + "(을)를 공유하여 단순 연관(related) 관계가 있습니다."
            return evidence_parts, reason

    # 3. 소스 코드 내 import 라인 발굴
    import_patterns = [
        re.compile(rf"import\s+.*\s+from\s+['\"][^'\"]*{target_base}[^'\"]*['\"]", re.IGNORECASE),
        re.compile(rf"import\s+['\"][^'\"]*{target_base}[^'\"]*['\"]", re.IGNORECASE),
        re.compile(rf"from\s+['\"][^'\"]*{target_base}[^'\"]*['\"]\s+import", re.IGNORECASE),
        re.compile(rf"require\(\s*['\"][^'\"]*{target_base}[^'\"]*['\"]\s*\)", re.IGNORECASE),
        re.compile(rf"import\s+({target_base}|{target_base.replace('-', '_')})", re.IGNORECASE),
        re.compile(rf"from\s+.*\s+import\s+.*({target_base}|{target_base.replace('-', '_')})", re.IGNORECASE),
    ]

    lines = source_body.splitlines()
    for line in lines:
        for pattern in import_patterns:
            if pattern.search(line):
                evidence_list.append(line.strip())
                break

    if evidence_list:
        reason = f"소스 코드 내 import 구문에서 '{target_title}'({target_slug}) 모듈에 대한 참조를 발견했습니다."
        return evidence_list, reason

    # 4. 두 문서의 본문 중 서로 연관되는 구절(Text Span) 발굴
    target_names = [target_title, target_slug, target_base]
    
    aliases = target_meta.get("aliases", [])
    if isinstance(aliases, str):
        aliases = [x.strip() for x in aliases.split(",") if x.strip()]
    elif isinstance(aliases, list):
        aliases = [str(x).strip() for x in aliases if x]
    else:
        aliases = []
        
    target_names.extend(aliases)
    target_names = list(set([n for n in target_names if n]))

    sentences = []
    raw_sentences = re.split(r'(?<=[.!?])\s+|\n+', source_body)
    for s in raw_sentences:
        s_clean = s.strip()
        if len(s_clean) > 5:
            sentences.append(s_clean)

    for s in sentences:
        for name in target_names:
            if name.lower() in s.lower() or f"[[{target_slug}" in s or f"[[{target_base}" in s:
                evidence_list.append(s)
                break
        if len(evidence_list) >= 3:
            break

    if evidence_list:
        reason = f"본문 텍스트 내에서 '{target_title}'에 대해 언급하는 구절(Text Span)을 발견하여 관계를 맺습니다."
        return evidence_list, reason

    # 5. Fallback: 매칭되는 구절이나 import가 없을 때
    fallback_evidence = f"[[{target_slug}]]"
    fallback_reason = f"자동 관계 인퍼런스를 통해 '{source_title}' 문서가 '{target_title}' 문서의 기능을 {relation_type}하는 것으로 파악되었습니다."
    
    target_desc = ""
    for tl in target_body.splitlines():
        tl_clean = tl.strip()
        if tl_clean and not tl_clean.startswith("-") and not tl_clean.startswith("#"):
            target_desc = tl_clean
            break
            
    ev_spans = [fallback_evidence]
    if target_desc:
        ev_spans.append(f"대상 문서 요약: {target_desc[:100]}...")

    return ev_spans, fallback_reason
