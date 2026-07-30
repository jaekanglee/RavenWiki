package com.ppizil.raven.common.data.remote.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.JsonElement

/** GET /api/vaults/{vault}/pages */
@Serializable
data class PageListResponse(
    val ok: Boolean = true,
    val vault: String = "",
    val pages: List<PageSummaryDto> = emptyList(),
)

@Serializable
data class PageSummaryDto(
    val slug: String,
    val title: String,
    val type: String? = null,
    val collection: String? = null,
    val status: String? = null,
    val updated: String? = null,
)

// hybrid-search 와 BM25-lite search 의 공통 응답. hybrid 쪽은 snippet이 없다.
@Serializable
data class SearchResponse(
    val ok: Boolean = true,
    val vault: String = "",
    val query: String = "",
    val results: List<SearchHitDto> = emptyList(),
)

@Serializable
data class SearchHitDto(
    val slug: String,
    val title: String = "",
    val type: String? = null,
    val snippet: String? = null,
    val score: Double = 0.0,
)

/** GET /api/vaults/{vault}/pages/{slug} — 본문은 여기에만 있다. */
@Serializable
data class PageDetailResponse(
    val ok: Boolean = true,
    val vault: String = "",
    val slug: String = "",
    @SerialName("file_path") val filePath: String? = null,
    val content: String = "",
    val frontmatter: JsonElement? = null,
)
