package com.ppizil.raven.common.data.repository

import com.ppizil.raven.common.db.RavenDatabase
import com.ppizil.raven.common.domain.model.Document
import com.ppizil.raven.common.domain.repository.DocumentRepository
import com.ppizil.raven.common.domain.repository.SettingsRepository
import com.ppizil.raven.common.data.remote.model.DocumentDto
import com.ppizil.raven.common.data.mapper.toDomainModel
import io.ktor.client.*
import io.ktor.client.request.*
import io.ktor.client.call.body
import io.ktor.http.headers
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import app.cash.sqldelight.coroutines.asFlow
import app.cash.sqldelight.coroutines.mapToList
import kotlinx.coroutines.Dispatchers

class DocumentRepositoryImpl(
    private val httpClient: HttpClient,
    private val database: RavenDatabase,
    private val settingsRepository: SettingsRepository
) : DocumentRepository {
    private val queries = database.documentQueries

    override fun getAllDocuments(): Flow<List<Document>> {
        return queries.selectAll().asFlow().mapToList(Dispatchers.Default).map { list ->
            list.map { it.toDomainModel() }
        }
    }

    override suspend fun fetchDocument(id: String) {
        val endpoint = settingsRepository.getEndpoint()?.takeIf { it.isNotBlank() }?.trimEnd('/') ?: "http://10.0.2.2:8765"
        val apiKey = settingsRepository.getApiKey()
        
        try {
            val requestBuilder: HttpRequestBuilder.() -> Unit = {
                if (!apiKey.isNullOrBlank()) {
                    headers {
                        append("Authorization", "Bearer $apiKey")
                    }
                }
            }
            val response = httpClient.get("$endpoint/api/index.json", requestBuilder)
            val docs = response.body<List<DocumentDto>>()
            val doc = docs.find { it.slug == id } ?: return
            queries.insertDocument(doc.slug, doc.title, doc.type ?: "", doc.path, false, io.ktor.util.date.getTimeMillis())
        } catch (e: Exception) {
            println("Failed to fetch document: ${e.message}")
        }
    }

    override suspend fun syncAllDocuments() {
        val endpoint = settingsRepository.getEndpoint()?.takeIf { it.isNotBlank() }?.trimEnd('/') ?: "http://10.0.2.2:8765"
        val apiKey = settingsRepository.getApiKey()

        val requestBuilder: HttpRequestBuilder.() -> Unit = {
            if (!apiKey.isNullOrBlank()) {
                headers {
                    append("Authorization", "Bearer $apiKey")
                }
            }
        }
        val response = httpClient.get("$endpoint/api/index.json", requestBuilder)
        val docs = response.body<List<DocumentDto>>()
        docs.forEach { doc ->
            queries.insertDocument(doc.slug, doc.title, doc.type ?: "", doc.path, false, io.ktor.util.date.getTimeMillis())
        }
    }

    override suspend fun saveDocument(document: Document) {
        // 1. Save locally
        queries.insertDocument(
            id = document.id,
            title = document.title,
            content = document.content,
            path = document.path,
            isFavorite = document.isFavorite,
            lastUpdated = document.lastUpdated
        )

        // 2. Sync to remote (optional / stub)
        // val endpoint = settingsRepository.getEndpoint()?.takeIf { it.isNotBlank() }?.trimEnd('/') ?: "http://10.0.2.2:8765"
        // val apiKey = settingsRepository.getApiKey()
        // try {
        //     httpClient.post("$endpoint/api/documents") { /* ... */ }
        // } catch (e: Exception) {
        //     println("Failed to sync document remotely: ${e.message}")
        // }
    }

    override suspend fun deleteDocument(id: String) {
        queries.deleteDocument(id)
        
        // 2. Sync deletion to remote (optional / stub)
        // val endpoint = settingsRepository.getEndpoint()?.takeIf { it.isNotBlank() }?.trimEnd('/') ?: "http://10.0.2.2:8765"
        // val apiKey = settingsRepository.getApiKey()
        // try {
        //     httpClient.delete("$endpoint/api/documents/$id") { /* ... */ }
        // } catch (e: Exception) {
        //     println("Failed to delete document remotely: ${e.message}")
        // }
    }
}
