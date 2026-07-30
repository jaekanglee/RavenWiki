package com.ppizil.raven.common.domain.model

/** 연결한 PC가 등록해 둔 vault 하나. */
data class VaultSummary(
    val name: String,
    val path: String?,
    val mode: String?,
    val isDefault: Boolean,
)
