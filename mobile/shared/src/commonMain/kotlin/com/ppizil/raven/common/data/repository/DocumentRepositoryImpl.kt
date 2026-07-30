package com.ppizil.raven.common.data.repository

import app.cash.sqldelight.coroutines.asFlow
import app.cash.sqldelight.coroutines.mapToList
import com.ppizil.raven.common.data.mapper.toDomainModel
import com.ppizil.raven.common.data.remote.model.DocumentDto
import com.ppizil.raven.common.db.RavenDatabase
import com.ppizil.raven.common.domain.model.Document
import com.ppizil.raven.common.domain.repository.DocumentRepository
import com.ppizil.raven.common.domain.repository.SettingsRepository
import io.ktor.client.HttpClient
import io.ktor.client.call.body
import io.ktor.client.request.delete
import io.ktor.client.request.get
import io.ktor.client.request.headers
import io.ktor.client.request.put
import io.ktor.client.request.setBody
import io.ktor.client.statement.HttpResponse
import io.ktor.http.ContentType
import io.ktor.http.HttpStatusCode
import io.ktor.http.contentType
import io.ktor.http.isSuccess
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import kotlinx.serialization.Serializable

private const val PUT_OPERATION = "PUT"
private const val DELETE_OPERATION = "DELETE"
private const val CONFLICT_FAILURE = "CONFLICT"
private const val NETWORK_FAILURE = "NETWORK"
private const val REMOTE_FAILURE = "REMOTE"

@Serializable
private data class PageWriteBody(val content: String)

data class PendingWriteEntry(
    val slug: String,
    val operation: String,
    val payload: String?,
    val attemptCount: Int,
    val lastError: String?,
    val failureKind: String?,
)

fun canonicalPageSlug(title: String, path: String?): String {
    val source = path
        ?.trim()
        ?.trim('/')
        ?.removeSuffix(".md")
        ?.takeIf { it.isNotBlank() }
        ?: title.trim()
    return source
        .split('/')
        .filter { it.isNotBlank() }
        .joinToString("/") { segment ->
            segment.lowercase()
                .replace(Regex("[^\\p{L}\\p{N}]+"), "-")
                .trim('-')
        }
        .split('/')
        .filter { it.isNotBlank() }
        .joinToString("/")
        .ifBlank { "untitled" }
}

class DocumentRepositoryImpl(
    private val httpClient: HttpClient,
    private val database: RavenDatabase,
    private val settingsRepository: SettingsRepository,
) : DocumentRepository {
    private val queries = database.documentQueries

    override fun getAllDocuments(): Flow<List<Document>> =
        queries.selectAll().asFlow().mapToList(Dispatchers.Default).map { documents ->
            documents.map { it.toDomainModel() }
        }

    override suspend fun fetchDocument(id: String) {
        try {
            val response = httpClient.get("${endpoint()}/api/index.json") { authorize() }
            ensureSuccess(response)
            val document = response.body<List<DocumentDto>>().find { it.slug == id } ?: return
            queries.insertDocument(
                document.slug,
                document.title,
                document.type ?: "",
                document.path,
                false,
                io.ktor.util.date.getTimeMillis(),
            )
        } catch (exception: Exception) {
            println("Failed to fetch document: ${exception.message}")
        }
    }

    override suspend fun syncAllDocuments() {
        flushPendingWrites()
        val response = httpClient.get("${endpoint()}/api/index.json") { authorize() }
        ensureSuccess(response)
        response.body<List<DocumentDto>>().forEach { document ->
            queries.insertDocument(
                document.slug,
                document.title,
                document.type ?: "",
                document.path,
                false,
                io.ktor.util.date.getTimeMillis(),
            )
        }
    }

    override suspend fun saveDocument(document: Document) {
        database.transaction {
            queries.insertDocument(
                id = document.id,
                title = document.title,
                content = document.content,
                path = document.path,
                isFavorite = document.isFavorite,
                lastUpdated = document.lastUpdated,
            )
            queries.enqueuePendingWrite(document.id, PUT_OPERATION, document.content)
        }
        flushPendingWrite(document.id)
    }

    override suspend fun deleteDocument(id: String) {
        database.transaction {
            queries.deleteDocument(id)
            queries.enqueuePendingWrite(id, DELETE_OPERATION, null)
        }
        flushPendingWrite(id)
    }

    override suspend fun flushPendingWrites() {
        pendingWrites().forEach { pending -> flushPendingWrite(pending.slug) }
    }

    fun pendingWrites(): List<PendingWriteEntry> =
        queries.selectPendingWrites().executeAsList().map { pending ->
            PendingWriteEntry(
                slug = pending.slug,
                operation = pending.operation,
                payload = pending.payload,
                attemptCount = pending.attemptCount.toInt(),
                lastError = pending.lastError,
                failureKind = pending.failureKind,
            )
        }

    private suspend fun flushPendingWrite(slug: String) {
        val pending = pendingWrites().firstOrNull { it.slug == slug } ?: return
        try {
            val url = "${endpoint()}/api/vaults/${vault()}/pages/${pending.slug}"
            val response = when (pending.operation) {
                PUT_OPERATION -> httpClient.put(url) {
                    authorize()
                    contentType(ContentType.Application.Json)
                    setBody(PageWriteBody(pending.payload.orEmpty()))
                }
                DELETE_OPERATION -> httpClient.delete(url) { authorize() }
                else -> error("Unsupported outbox operation: ${pending.operation}")
            }
            if (response.status.isSuccess()) {
                queries.removePendingWrite(pending.slug)
            } else {
                val kind = if (response.status == HttpStatusCode.Conflict ||
                    response.status == HttpStatusCode.PreconditionFailed
                ) CONFLICT_FAILURE else REMOTE_FAILURE
                recordFailure(pending.slug, kind, "HTTP ${response.status.value} ${response.status.description}")
            }
        } catch (exception: Exception) {
            val message = generateSequence<Throwable>(exception) { it.cause }
                .mapNotNull { it.message }
                .joinToString(": ")
                .ifBlank { exception::class.simpleName.orEmpty() }
            recordFailure(pending.slug, NETWORK_FAILURE, message)
        }
    }

    private fun recordFailure(slug: String, kind: String, message: String) {
        queries.recordPendingWriteFailure(message, kind, slug)
    }

    private fun endpoint(): String =
        settingsRepository.getEndpoint()?.takeIf { it.isNotBlank() }?.trimEnd('/')
            ?: "http://10.0.2.2:8765"

    private fun vault(): String = settingsRepository.getVault()?.takeIf { it.isNotBlank() } ?: "default"

    private fun io.ktor.client.request.HttpRequestBuilder.authorize() {
        settingsRepository.getApiKey()?.takeIf { it.isNotBlank() }?.let { apiKey ->
            headers { append("Authorization", "Bearer $apiKey") }
        }
    }

    private fun ensureSuccess(response: HttpResponse) {
        check(response.status.isSuccess()) {
            "HTTP ${response.status.value} ${response.status.description}"
        }
    }
}
