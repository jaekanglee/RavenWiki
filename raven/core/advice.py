"""raven.core.advice — 지식 네트워크 분석 기반 진단 및 AI 조언(Advice) 엔진."""
from __future__ import annotations

import sqlite3
from typing import Any
from .vault import Vault
from . import db as db_module


def get_advice(vault: Vault) -> list[dict[str, Any]]:
    """지식 네트워크 분석 결과를 토대로 가독성 높은 조언(Advice) 목록을 생성하여 반환합니다.

    PageRank, Betweenness Centrality, Degree 등을 활용해 브릿지, 비대 컬렉션, 고립 노드 등을 진단합니다.
    """
    if not vault.db_path.exists():
        # db가 없으면 stale/drift 검사를 위해 connect()를 한 번 시도하여 자동 빌드하게 함
        try:
            conn = db_module.connect(vault)
            conn.close()
        except Exception:
            return []

    try:
        conn = db_module.connect(vault)
        conn.row_factory = sqlite3.Row

        # 1. 전체 페이지 정보 가져오기 (자동 생성 카탈로그 제외)
        pages = conn.execute(
            "SELECT slug, title, type, importance, centrality, community FROM pages "
            "WHERE slug != 'content/index' AND slug NOT LIKE 'content/\\_index/%' ESCAPE '\\'"
        ).fetchall()
        n_pages = len(pages)
        if n_pages == 0:
            conn.close()
            return []

        # 2. 링크 관계 가져와서 degree 계산 (카탈로그 링크 제외)
        links = conn.execute(
            "SELECT source_slug, target_slug FROM links "
            "WHERE source_slug != 'content/index' AND source_slug NOT LIKE 'content/\\_index/%' ESCAPE '\\'"
        ).fetchall()
        relations = conn.execute("SELECT source_slug, target_slug FROM relations").fetchall()

        # degree 계산 및 인접 리스트 생성
        degrees = {p["slug"]: 0 for p in pages}
        adj = {p["slug"]: set() for p in pages}
        for s, t in links + relations:
            if s in degrees and t in degrees:
                if t not in adj[s]:
                    adj[s].add(t)
                    degrees[s] += 1
                if s not in adj[t]:
                    adj[t].add(s)
                    degrees[t] += 1

        advice_list = []

        # 1) 핵심 브릿지 문서 추출
        pages_sorted_centrality = sorted(pages, key=lambda x: x["centrality"] or 0, reverse=True)
        bridge_count = 0
        for p in pages_sorted_centrality:
            if bridge_count >= 2:
                break
            cent = p["centrality"] or 0
            if cent > 0.03:  # 매개도가 유의미한 경우
                neighbors = adj[p["slug"]]
                neighbor_folders = set()
                for nb in neighbors:
                    parts = nb.split('/')
                    if len(parts) > 1:
                        folder = parts[1] if parts[0] in ("content", "raw") and len(parts) > 2 else parts[0]
                    else:
                        folder = "root"
                    if folder not in ("_meta", "raw", "_archive", "content"):
                        neighbor_folders.add(folder)
                if len(neighbor_folders) >= 2:
                    folders_str = "와 ".join(list(neighbor_folders)[:2])
                    advice_list.append({
                        "id": f"bridge-{p['slug']}",
                        "type": "bridge",
                        "title": "핵심 브릿지 문서 발견",
                        "message": f"'{p['title']}' 문서는 {folders_str} 도메인을 연결하는 핵심 브릿지 문서입니다.",
                        "severity": "info",
                        "slug": p["slug"]
                    })
                    bridge_count += 1

        # 2) 비대한 폴더/컬렉션 검출 (폴더 기반)
        folder_counts = {}
        for p in pages:
            parts = p["slug"].split('/')
            folder = parts[0] if len(parts) > 1 else "root"
            if folder not in ("_meta", "raw", "_archive"):
                folder_counts[folder] = folder_counts.get(folder, 0) + 1

        for folder, count in folder_counts.items():
            if count >= 8 and (count / n_pages) > 0.35:
                folder_label = folder if folder != "root" else "루트 폴더"
                advice_list.append({
                    "id": f"bloated-{folder}",
                    "type": "bloated",
                    "title": "비대한 컬렉션 감지",
                    "message": f"'{folder_label}' 컬렉션은 다른 노드에 비해 지나치게 비대합니다. 분할을 권장합니다.",
                    "severity": "warning",
                    "slug": f"content/{folder}" if folder != "root" else ""
                })

        # 2-b) 비대 커뮤니티(Louvain) 검출 — community 노드 수 임계값 초과 시 분리 제안
        COMMUNITY_BLOAT_THRESHOLD = 8
        COMMUNITY_RATIO_THRESHOLD = 0.30  # 전체 페이지 중 30% 이상
        community_members: dict[int, list] = {}
        for p in pages:
            cid = p["community"]
            if cid is None:
                continue
            community_members.setdefault(cid, []).append(p)

        for cid, members in community_members.items():
            count = len(members)
            if count < COMMUNITY_BLOAT_THRESHOLD:
                continue
            if n_pages > 0 and (count / n_pages) < COMMUNITY_RATIO_THRESHOLD:
                continue
            # 대표 폴더/도메인 이름 추출 (most-common 2nd-level subfolder in community)
            # content/backend/auth → backend, content/page → (root-level, use 'content')
            folder_tally: dict[str, int] = {}
            for p in members:
                parts = p["slug"].split('/')
                # 2단계 이상 경로: content/backend/auth → 'backend'
                # 1단계 경로: content/page → 'content' (generic)
                if len(parts) >= 3 and parts[0] in ("content", "raw"):
                    domain = parts[1]
                elif len(parts) == 2 and parts[0] not in ("_meta", "raw", "_archive"):
                    domain = parts[0]  # "content"
                else:
                    domain = "root"
                if domain not in ("_meta", "raw", "_archive"):
                    folder_tally[domain] = folder_tally.get(domain, 0) + 1
            if not folder_tally:
                continue
            domain_name = max(folder_tally, key=lambda k: folder_tally[k])
            advice_id = f"community-bloated-{cid}"
            # 중복 방지: 이미 같은 advice_id가 있으면 추가 안 함
            # (폴더 기반 bloated 중복 제거는 하지 않음 — community는 별도 semantic 레이어)
            existing_ids = {a["id"] for a in advice_list}
            if advice_id in existing_ids:
                continue
            advice_list.append({
                "id": advice_id,
                "type": "community_split",
                "title": "비대 도메인 분리 권장",
                "message": (
                    f"'{domain_name}' 도메인의 지식 커뮤니티가 {count}개 노드로 비대합니다. "
                    f"서로 다른 서브 토픽이 하나의 군집으로 뭉쳐 있습니다. "
                    f"분리가 필요합니다."
                ),
                "severity": "warning",
                "slug": f"content/{domain_name}" if domain_name not in ("root", "content") else "",
                "community_id": cid,
                "community_size": count,
            })

        # 3) 고립된 노드 검출
        orphan_count = 0
        for p in pages:
            if orphan_count >= 2:
                break
            if degrees[p["slug"]] == 0 and p["type"] != "journal":  # journal은 고립되기 쉬우므로 제외
                advice_list.append({
                    "id": f"orphan-{p['slug']}",
                    "type": "orphan",
                    "title": "고립된 문서 발견",
                    "message": f"'{p['title']}' 문서는 다른 지식과 연결되어 있지 않은 고립된 상태입니다. 관련 문서와 연결을 권장합니다.",
                    "severity": "warning",
                    "slug": p["slug"]
                })
                orphan_count += 1

        # 4) 중요하지만 연결이 부족한 문서 검출
        pages_sorted_importance = sorted(pages, key=lambda x: x["importance"] or 0, reverse=True)
        top_importance_threshold = max(1, int(n_pages * 0.25))
        top_important_slugs = {x["slug"] for x in pages_sorted_importance[:top_importance_threshold]}

        underlinked_count = 0
        for p in pages:
            if underlinked_count >= 2:
                break
            if p["slug"] in top_important_slugs and degrees[p["slug"]] <= 1 and p["type"] != "journal":
                advice_list.append({
                    "id": f"underlinked-{p['slug']}",
                    "type": "underlinked",
                    "title": "연결이 부족한 중요 지식",
                    "message": f"'{p['title']}' 문서는 지식 중요도가 높지만 연결된 링크가 적습니다. 추가적인 참조 관계 설정을 권장합니다.",
                    "severity": "info",
                    "slug": p["slug"]
                })
                underlinked_count += 1

        conn.close()
        return advice_list
    except Exception as e:
        import sys
        sys.stderr.write(f"⚠️  [get_advice] failed: {e}\n")
        return []
