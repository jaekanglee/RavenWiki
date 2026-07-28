package com.ppizil.raven.common.data.remote.model

import kotlinx.serialization.Serializable

@Serializable
data class DocumentDto(
    val slug: String,
    val title: String,
    val type: String? = null,
    val path: String? = null,
    val created: String? = null,
    val updated: String? = null,
    val tags: String? = null
)
