package com.ppizil.raven.common.data.remote.model

import kotlinx.serialization.Serializable

@Serializable
data class DocumentDto(val id: String, val title: String, val content: String)
