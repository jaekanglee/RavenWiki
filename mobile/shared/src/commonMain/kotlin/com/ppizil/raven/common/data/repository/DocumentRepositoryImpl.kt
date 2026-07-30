package com.ppizil.raven.common.data.repository

import app.cash.sqldelight.coroutines.asFlow
import app.cash.sqldelight.coroutines.mapToList
import com.ppizil.raven.common.data.mapper.toDomainModel
import com.ppizil.raven.common.data.remote.model.PageDetailResponse
import com.ppizil.raven.common.data.remote.model.PageListResponse
import com.ppizil.raven.common.data.remote.model.VaultListResponse
import com.ppizil.raven.common.db.RavenDatabase
import com.ppizil.raven.common.domain.model.Document
import com.ppizil.raven.common.domain.model.VaultSummary
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
    val vault: String,
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

    override suspend fun fetchVaults(): List<VaultSummary> {
        val response = httpClient.get("${endpoint()}/api/vaults") { authorize() }
        ensureSuccess(response)
        return response.body<VaultListResponse>().vaults.map { it.toDomainModel() }
    }

    override fun getDocuments(vault: String): Flow<List<Document>> =
        queries.selectByVault(vault).asFlow().mapToList(Dispatchers.Default).map { documents ->
            documents.map { it.toDomainModel() }
        }

    override suspend fun syncDocuments(vault: String) {
        flushPendingWrites()
        val response = httpClient.get("${endpoint()}/api/vaults/$vault/pages") { authorize() }
        ensureSuccess(response)
        val pages = response.body<PageListResponse>().pages
        val now = io.ktor.util.date.getTimeMillis()
        database.transaction {
            pages.forEach { page ->
                val path = page.slug.takeIf { it.isNotBlank() }?.let { "$it.md" }
                // 목록 API에는 본문이 없다. insert+update로 나눠 이미 받아둔 본문을 보존한다.
                queries.insertDocumentMetaIfAbsent(
                    vault = vault,
                    id = page.slug,
                    title = page.title,
                    type = page.type,
                    path = path,
                    lastUpdated = now,
                )
                queries.updateDocumentMeta(
                    title = page.title,
                    type = page.type,
                    path = path,
                    lastUpdated = now,
                    vault = vault,
                    id = page.slug,
                )
            }
        }
    }

    override suspend fun fetchDocument(vault: String, id: String) {
        val response = httpClient.get("${endpoint()}/api/vaults/$vault/pages/$id") { authorize() }
        ensureSuccess(response)
        val detail = response.body<PageDetailResponse>()
        queries.updateDocumentContent(
            content = detail.content,
            lastUpdated = io.ktor.util.date.getTimeMillis(),
            vault = vault,
            id = id,
        )
    }

    override suspend fun saveDocument(document: Document) {
        database.transaction {
            queries.insertDocument(
                vault = document.vault,
                id = document.id,
                title = document.title,
                content = document.content,
                type = document.type,
                path = document.path,
                isFavorite = document.isFavorite,
                lastUpdated = document.lastUpdated,
            )
            queries.enqueuePendingWrite(
                document.vault,
                document.id,
                PUT_OPERATION,
                document.content,
            )
        }
        flushPendingWrite(document.vault, document.id)
    }

    override suspend fun deleteDocument(vault: String, id: String) {
        database.transaction {
            queries.deleteDocument(vault, id)
            queries.enqueuePendingWrite(vault, id, DELETE_OPERATION, null)
        }
        flushPendingWrite(vault, id)
    }

    override suspend fun flushPendingWrites() {
        pendingWrites().forEach { pending -> flushPendingWrite(pending.vault, pending.slug) }
    }

    fun pendingWrites(): List<PendingWriteEntry> =
        queries.selectPendingWrites().executeAsList().map { pending ->
            PendingWriteEntry(
                vault = pending.vault,
                slug = pending.slug,
                operation = pending.operation,
                payload = pending.payload,
                attemptCount = pending.attemptCount.toInt(),
                lastError = pending.lastError,
                failureKind = pending.failureKind,
            )
        }

    private suspend fun flushPendingWrite(vault: String, slug: String) {
        val pending = pendingWrites().firstOrNull { it.vault == vault && it.slug == slug } ?: return
        try {
            val url = "${endpoint()}/api/vaults/$vault/pages/${pending.slug}"
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
                queries.removePendingWrite(vault, pending.slug)
            } else {
                val kind = if (response.status == HttpStatusCode.Conflict ||
                    response.status == HttpStatusCode.PreconditionFailed
                ) CONFLICT_FAILURE else REMOTE_FAILURE
                recordFailure(
                    vault,
                    pending.slug,
                    kind,
                    "HTTP ${response.status.value} ${response.status.description}",
                )
            }
        } catch (exception: Exception) {
            val message = generateSequence<Throwable>(exception) { it.cause }
                .mapNotNull { it.message }
                .joinToString(": ")
                .ifBlank { exception::class.simpleName.orEmpty() }
            recordFailure(vault, pending.slug, NETWORK_FAILURE, message)
        }
    }

    private fun recordFailure(vault: String, slug: String, kind: String, message: String) {
        queries.recordPendingWriteFailure(message, kind, vault, slug)
    }

    private fun endpoint(): String =
        settingsRepository.getEndpoint()?.takeIf { it.isNotBlank() }?.trimEnd('/')
            ?: "http://10.0.2.2:8765"

    private fun io.ktor.client.request.HttpRequestBuilder.authorize() {
        settingsRepository.getApiKey()?.takeIf { it.isNotBlank() }?.let { apiKey ->
            headers { append("Authorization", "Bearer $apiKey") }
        }
    }

    private fun ensureSuccess(response: HttpResponse) {
        if (!response.status.isSuccess()) {
            error("HTTP ${response.status.value} ${response.status.description}")
        }
    }
}
