package com.ppizil.raven.common.data.remote.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

/** GET /api/vaults */
@Serializable
data class VaultListResponse(
    val ok: Boolean = true,
    val vaults: List<VaultDto> = emptyList(),
)

@Serializable
data class VaultDto(
    val name: String,
    val path: String? = null,
    val mode: String? = null,
    val owner: String? = null,
    @SerialName("default") val isDefault: Boolean = false,
    @SerialName("workspace_path") val workspacePath: String? = null,
)
