package com.ppizil.raven.common.repository

import com.ppizil.raven.common.db.RavenDatabase
import io.ktor.client.*
import io.ktor.client.request.*
import io.ktor.client.statement.*
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow
import app.cash.sqldelight.coroutines.asFlow
import app.cash.sqldelight.coroutines.mapToList
import com.ppizil.raven.common.db.Document
import kotlinx.coroutines.Dispatchers

import kotlinx.serialization.Serializable
import io.ktor.client.call.body
import io.ktor.http.headers
import io.ktor.http.HttpHeaders

@Serializable
data class DocumentDto(val id: String, val title: String, val content: String)

class DocumentRepository(
    private val httpClient: HttpClient,
    private val database: RavenDatabase,
    private val settingsRepository: SettingsRepository
) {
    private val queries = database.documentQueries

    fun getAllDocuments(): Flow<List<Document>> {
        return queries.selectAll().asFlow().mapToList(Dispatchers.Default)
    }

    suspend fun fetchDocument(id: String) {
        val endpoint = settingsRepository.getEndpoint() ?: return
        val apiKey = settingsRepository.getApiKey() ?: return
        
        try {
            val response = httpClient.get("$endpoint/api/docs/$id") {
                headers {
                    append("Authorization", "Bearer $apiKey")
                }
            }
            val doc = response.body<DocumentDto>()
            queries.insertDocument(doc.id, doc.title, doc.content, false, System.currentTimeMillis())
        } catch (e: Exception) {
            // Offline or error: rely on cache
            println("Failed to fetch document: ${e.message}")
        }
    }

    suspend fun syncAllDocuments() {
        val endpoint = settingsRepository.getEndpoint() ?: return
        val apiKey = settingsRepository.getApiKey() ?: return

        try {
            val response = httpClient.get("$endpoint/api/docs") {
                headers {
                    append("Authorization", "Bearer $apiKey")
                }
            }
            val docs = response.body<List<DocumentDto>>()
            docs.forEach { doc ->
                queries.insertDocument(doc.id, doc.title, doc.content, false, System.currentTimeMillis())
            }
        } catch (e: Exception) {
            println("Failed to sync documents: ${e.message}")
        }
    }
}
