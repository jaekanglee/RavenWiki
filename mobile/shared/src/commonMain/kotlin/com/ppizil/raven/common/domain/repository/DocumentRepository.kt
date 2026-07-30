package com.ppizil.raven.common.domain.repository

import com.ppizil.raven.common.domain.model.Document
import kotlinx.coroutines.flow.Flow

interface DocumentRepository {
    fun getAllDocuments(): Flow<List<Document>>
    suspend fun fetchDocument(id: String)
    suspend fun syncAllDocuments()
    suspend fun flushPendingWrites()
    suspend fun saveDocument(document: Document)
    suspend fun deleteDocument(id: String)
}
