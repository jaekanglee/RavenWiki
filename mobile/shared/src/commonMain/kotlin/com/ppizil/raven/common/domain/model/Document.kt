package com.ppizil.raven.common.domain.model

data class Document(
    val id: String,
    val title: String,
    val content: String,
    val path: String?,
    val isFavorite: Boolean,
    val lastUpdated: Long
)
