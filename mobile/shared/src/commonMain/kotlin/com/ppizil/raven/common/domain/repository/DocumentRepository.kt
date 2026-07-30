package com.ppizil.raven.common.domain.repository

import com.ppizil.raven.common.domain.model.Document
import com.ppizil.raven.common.domain.model.SearchHit
import com.ppizil.raven.common.domain.model.VaultSummary
import com.ppizil.raven.common.domain.model.WriteOutcome
import kotlinx.coroutines.flow.Flow

interface DocumentRepository {
    /** 연결한 PC의 vault 목록. */
    suspend fun fetchVaults(): List<VaultSummary>

    /** 한 vault의 문서만 흘려보낸다. */
    fun getDocuments(vault: String): Flow<List<Document>>

    /** 한 vault의 문서 목록(메타데이터)을 동기화한다. 본문은 fetchDocument가 채운다. */
    suspend fun syncDocuments(vault: String)

    /** 문서 본문을 서버에서 받아 채운다. */
    suspend fun fetchDocument(vault: String, id: String)

    /** 캐시에 본문이 없는 문서까지 닿기 위해 서버 검색을 경유한다. */
    suspend fun searchDocuments(vault: String, query: String): List<SearchHit>

    suspend fun flushPendingWrites()
    suspend fun saveDocument(document: Document): WriteOutcome
    suspend fun deleteDocument(vault: String, id: String)
}
