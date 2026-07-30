package com.ppizil.raven.common.data.mapper

import com.ppizil.raven.common.data.remote.model.VaultDto
import com.ppizil.raven.common.db.Document as DbDocument
import com.ppizil.raven.common.domain.model.Document
import com.ppizil.raven.common.domain.model.VaultSummary

fun DbDocument.toDomainModel(): Document = Document(
    vault = this.vault,
    id = this.id,
    title = this.title,
    content = this.content,
    type = this.type,
    path = this.path,
    isFavorite = this.isFavorite ?: false,
    lastUpdated = this.lastUpdated,
    precondition = this.precondition,
)

fun VaultDto.toDomainModel(): VaultSummary = VaultSummary(
    name = this.name,
    path = this.path,
    mode = this.mode,
    isDefault = this.isDefault,
)
