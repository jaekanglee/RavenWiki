package com.ppizil.raven.common.data.mapper

import com.ppizil.raven.common.db.Document as DbDocument
import com.ppizil.raven.common.domain.model.Document

fun DbDocument.toDomainModel(): Document {
    return Document(
        id = this.id,
        title = this.title,
        content = this.content ?: "",
        path = this.path,
        isFavorite = this.isFavorite ?: false,
        lastUpdated = this.lastUpdated ?: 0L
    )
}
