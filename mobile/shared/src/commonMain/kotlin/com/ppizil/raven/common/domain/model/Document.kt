package com.ppizil.raven.common.domain.model

data class Document(
    val vault: String,
    val id: String,
    val title: String,
    val content: String,
    val type: String? = null,
    val path: String? = null,
    val isFavorite: Boolean = false,
    val lastUpdated: Long = 0L,
    // 이 본문을 읽은 시점의 서버 상토큰. PUT에 실어 남의 편집을 덮어쓰는 것을 막는다.
    val precondition: String? = null,
)
