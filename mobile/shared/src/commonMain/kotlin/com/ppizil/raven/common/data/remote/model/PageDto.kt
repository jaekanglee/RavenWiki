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
