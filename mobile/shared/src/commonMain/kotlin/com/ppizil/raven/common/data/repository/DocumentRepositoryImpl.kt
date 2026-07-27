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
            println("Failed to fetch document: ${e.message}")
        }
    }

    override suspend fun syncAllDocuments() {
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
