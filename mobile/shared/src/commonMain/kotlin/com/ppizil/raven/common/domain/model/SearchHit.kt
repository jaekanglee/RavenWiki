package com.ppizil.raven.common.domain.model

// 목록 API에 본문이 없어 캐시 필터로는 못 찾는 문서까지 서버 검색이 실어 오는 결과 1건.

data class SearchHit(
    val vault: String,
    val slug: String,
    val title: String,
    val type: String? = null,
    val snippet: String? = null,
    val score: Double = 0.0,
)
