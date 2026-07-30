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
)
