package com.ppizil.raven.common.data.repository

import app.cash.sqldelight.coroutines.asFlow
import app.cash.sqldelight.coroutines.mapToList
import com.ppizil.raven.common.data.mapper.toDomainModel
import com.ppizil.raven.common.data.remote.model.PageDetailResponse
import com.ppizil.raven.common.data.remote.model.PageListResponse
import com.ppizil.raven.common.data.remote.model.PageWriteResponse
import com.ppizil.raven.common.data.remote.model.SearchHitDto
import com.ppizil.raven.common.data.remote.model.SearchResponse
import com.ppizil.raven.common.data.remote.model.VaultListResponse
import com.ppizil.raven.common.db.RavenDatabase
import com.ppizil.raven.common.domain.model.Document
import com.ppizil.raven.common.domain.model.SearchHit
import com.ppizil.raven.common.domain.model.VaultSummary
import com.ppizil.raven.common.domain.model.WriteOutcome
import com.ppizil.raven.common.domain.repository.DocumentRepository
import com.ppizil.raven.common.domain.repository.SettingsRepository
import io.ktor.client.HttpClient
import io.ktor.client.call.body
import io.ktor.client.request.delete
import io.ktor.client.request.get
import io.ktor.client.request.headers
import io.ktor.client.request.parameter
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
private data class PageWriteBody(val content: String, val precondition: String? = null)

private val MARKUP = Regex("<[^>]+>")

// 서버 snippet은 <mark> 하이라이트 + html 이스케이프가 섞여 오므로 평문으로 되돌린다.
private fun String.asPlainSnippet(): String = MARKUP.replace(this, "")
    .replace("&lt;", "<")
    .replace("&gt;", ">")
    .replace("&quot;", "\"")
    .replace("&#x27;", "'")
    .replace("&amp;", "&")

data class PendingWriteEntry(
    val vault: String,
    val slug: String,
    val operation: String,
    val payload: String?,
    val attemptCount: Int,
    val lastError: String?,
    val failureKind: String?,
    val basePrecondition: String?,
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
            precondition = detail.precondition,
            lastUpdated = io.ktor.util.date.getTimeMillis(),
            vault = vault,
            id = id,
        )
    }

    override suspend fun searchDocuments(vault: String, query: String): List<SearchHit> {
        val trimmed = query.trim()
        if (trimmed.isEmpty()) return emptyList()
        val hits = searchHits("${endpoint()}/api/vaults/$vault/hybrid-search", "query", trimmed)
            .ifEmpty {
                // hybrid는 wiki.db 인덱스에 없는 문서를 못 보므로 BM25-lite 파이프로 뒤및는다.
                searchHits("${endpoint()}/api/vaults/$vault/search", "q", trimmed)
            }
        cacheSearchMeta(vault, hits)
        return hits.map { hit ->
            SearchHit(
                vault = vault,
                slug = hit.slug,
                title = hit.title.ifBlank { hit.slug },
                type = hit.type,
                snippet = hit.snippet?.asPlainSnippet(),
                score = hit.score,
            )
        }
    }

    private suspend fun searchHits(url: String, parameterName: String, query: String) =
        runCatching {
            val response = httpClient.get(url) {
                authorize()
                parameter(parameterName, query)
            }
            ensureSuccess(response)
            response.body<SearchResponse>().results
        }.getOrElse { failure ->
            if (parameterName == "q") throw failure else emptyList()
        }

    private fun cacheSearchMeta(vault: String, hits: List<SearchHitDto>) {
        if (hits.isEmpty()) return
        val now = io.ktor.util.date.getTimeMillis()
        database.transaction {
            hits.forEach { hit ->
                queries.insertDocumentMetaIfAbsent(
                    vault = vault,
                    id = hit.slug,
                    title = hit.title.ifBlank { hit.slug },
                    type = hit.type,
                    path = "${hit.slug}.md",
                    lastUpdated = now,
                )
            }
        }
    }

    override suspend fun saveDocument(document: Document): WriteOutcome {
        database.transaction {
            // OR REPLACE로 덮기 전에 읽는다 — 이 편집이 출발한 지점이 base다.
            val base = document.precondition
                ?: queries.selectPrecondition(document.vault, document.id)
                    .executeAsOneOrNull()
                    ?.precondition
            queries.insertDocument(
                vault = document.vault,
                id = document.id,
                title = document.title,
                content = document.content,
                type = document.type,
                path = document.path,
                isFavorite = document.isFavorite,
                lastUpdated = document.lastUpdated,
                precondition = base,
            )
            queries.enqueuePendingWrite(
                document.vault,
                document.id,
                PUT_OPERATION,
                document.content,
                base,
            )
        }
        return flushPendingWrite(document.vault, document.id)
    }

    override suspend fun deleteDocument(vault: String, id: String) {
        database.transaction {
            val base = queries.selectPrecondition(vault, id).executeAsOneOrNull()?.precondition
            queries.deleteDocument(vault, id)
            queries.enqueuePendingWrite(vault, id, DELETE_OPERATION, null, base)
        }
        flushPendingWrite(vault, id)
    }

    override suspend fun toggleFavorite(vault: String, id: String) {
        queries.toggleFavorite(vault, id)
    }

    override fun pendingWriteCount(): Int = pendingWrites().size

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
                basePrecondition = pending.basePrecondition,
            )
        }

    private suspend fun flushPendingWrite(vault: String, slug: String): WriteOutcome {
        val pending = pendingWrites().firstOrNull { it.vault == vault && it.slug == slug }
            ?: return WriteOutcome.Synced
        try {
            val url = "${endpoint()}/api/vaults/$vault/pages/${pending.slug}"
            val response = when (pending.operation) {
                PUT_OPERATION -> httpClient.put(url) {
                    authorize()
                    contentType(ContentType.Application.Json)
                    setBody(
                        PageWriteBody(
                            content = pending.payload.orEmpty(),
                            precondition = pending.basePrecondition,
                        ),
                    )
                }
                DELETE_OPERATION -> httpClient.delete(url) { authorize() }
                else -> error("Unsupported outbox operation: ${pending.operation}")
            }
            if (response.status.isSuccess()) {
                queries.removePendingWrite(vault, pending.slug)
                if (pending.operation == PUT_OPERATION) {
                    // 새 토큰이 다음 편집의 base다. 안 갱신하면 연속 수정이 방금 자기가 쓴 글과 추돌한다.
                    runCatching { response.body<PageWriteResponse>().precondition }
                        .getOrNull()
                        ?.let { queries.updateDocumentPrecondition(it, vault, pending.slug) }
                }
                return WriteOutcome.Synced
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
                return if (kind == CONFLICT_FAILURE) WriteOutcome.Conflict else WriteOutcome.Queued
            }
        } catch (exception: Exception) {
            val message = generateSequence<Throwable>(exception) { it.cause }
                .mapNotNull { it.message }
                .joinToString(": ")
                .ifBlank { exception::class.simpleName.orEmpty() }
            recordFailure(vault, pending.slug, NETWORK_FAILURE, message)
            return WriteOutcome.Queued
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
