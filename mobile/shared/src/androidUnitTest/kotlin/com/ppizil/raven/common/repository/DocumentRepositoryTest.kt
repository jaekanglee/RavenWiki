package com.ppizil.raven.common.repository

import com.ppizil.raven.common.data.repository.DocumentRepositoryImpl
import com.ppizil.raven.common.data.repository.SettingsRepositoryImpl
import com.ppizil.raven.common.data.repository.canonicalPageSlug
import com.ppizil.raven.common.domain.model.Document
import com.ppizil.raven.common.db.RavenDatabase
import app.cash.sqldelight.driver.jdbc.sqlite.JdbcSqliteDriver
import io.ktor.client.*
import io.ktor.client.engine.mock.*
import io.ktor.client.plugins.contentnegotiation.*
import io.ktor.http.*
import io.ktor.serialization.kotlinx.json.*
import java.io.IOException
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.test.runTest
import org.junit.Before
import org.junit.Test
import kotlin.test.assertEquals
import kotlin.test.assertNull
import kotlin.test.assertTrue

class DocumentRepositoryTest {
    private lateinit var repository: DocumentRepositoryImpl
    private lateinit var settingsRepository: SettingsRepositoryImpl
    private lateinit var database: RavenDatabase

    @Before
    fun setup() {
        val driver = JdbcSqliteDriver(JdbcSqliteDriver.IN_MEMORY)
        RavenDatabase.Schema.create(driver)
        database = RavenDatabase(driver)
        settingsRepository = SettingsRepositoryImpl(database)
        settingsRepository.saveEndpoint("http://localhost:8080")
        settingsRepository.saveApiKey("test-key")

        val mockEngine = MockEngine { request ->
            respond(
                content = """[{"slug": "content/doc1", "title": "Test", "type": "concept", "path": "content/doc1.md"}]""",
                status = HttpStatusCode.OK,
                headers = headersOf(HttpHeaders.ContentType, "application/json")
            )
        }
        val httpClient = HttpClient(mockEngine) {
            install(ContentNegotiation) {
                json()
            }
        }
        repository = DocumentRepositoryImpl(httpClient, database, settingsRepository)
    }

    @Test
    fun testSyncAllDocuments() = runTest {
        repository.syncAllDocuments()
        val docs = repository.getAllDocuments().first()
        assertEquals(1, docs.size)
        assertEquals("content/doc1", docs[0].id)
    }

    @Test
    fun offlineSaveKeepsContentAndPendingWrite() = runTest {
        val offlineRepository = repositoryWithEngine(MockEngine { throw IOException("offline") })
        val document = document(content = "content written offline")

        offlineRepository.saveDocument(document)

        assertEquals("content written offline", database.documentQueries.selectById(document.id).executeAsOne().content)
        val pending = offlineRepository.pendingWrites().single()
        assertEquals(document.id, pending.slug)
        assertEquals("PUT", pending.operation)
        assertEquals("content written offline", pending.payload)
        assertEquals(1, pending.attemptCount)
        assertTrue(pending.lastError!!.contains("offline"))
    }

    @Test
    fun reconnectFlushSendsPendingWriteAndClearsIt() = runTest {
        repositoryWithEngine(MockEngine { throw IOException("offline") })
            .saveDocument(document(content = "queued body"))
        var sentBody = ""
        val onlineRepository = repositoryWithEngine(MockEngine { request ->
            assertEquals(HttpMethod.Put, request.method)
            assertEquals("/api/vaults/test-vault/pages/notes/test-page", request.url.encodedPath)
            sentBody = request.body.toByteArray().decodeToString()
            respond("", HttpStatusCode.NoContent)
        })

        onlineRepository.flushPendingWrites()

        assertTrue(sentBody.contains("\"content\":\"queued body\""))
        assertTrue(onlineRepository.pendingWrites().isEmpty())
    }

    @Test
    fun failedRemoteWriteRecordsErrorAndConflictKind() = runTest {
        val conflictRepository = repositoryWithEngine(MockEngine {
            respond("stale version", HttpStatusCode.PreconditionFailed)
        })

        conflictRepository.saveDocument(document())

        val pending = conflictRepository.pendingWrites().single()
        assertEquals(1, pending.attemptCount)
        assertEquals("CONFLICT", pending.failureKind)
        assertTrue(pending.lastError!!.contains("412"))
    }

    @Test
    fun canonicalSlugIsDeterministicAndUsesPathWhenPresent() {
        assertEquals("my-new-page", canonicalPageSlug("  My New Page!  ", null))
        assertEquals("notes/design/page", canonicalPageSlug("Ignored title", "/notes/design/Page.md"))
        assertEquals(
            canonicalPageSlug("Repeatable Title", null),
            canonicalPageSlug("Repeatable Title", null),
        )
    }

    /** AGENTS.md §10: 한글 title -> 한글 파일명. 임의 번역/음차 금지. */
    @Test
    fun canonicalSlugKeepsKoreanTitles() {
        assertEquals("한글-제목", canonicalPageSlug("한글 제목", null))
        assertEquals("대시보드-사용성", canonicalPageSlug("대시보드 사용성!", null))
        assertEquals("content/한글-문서", canonicalPageSlug("무시됨", "/content/한글 문서.md"))
    }

    @Test
    fun migratesLegacyDocumentsWithoutLosingData() {
        val driver = JdbcSqliteDriver(JdbcSqliteDriver.IN_MEMORY)
        driver.execute(
            null,
            """
            CREATE TABLE Document (
                id TEXT NOT NULL PRIMARY KEY,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                isFavorite INTEGER DEFAULT 0,
                lastUpdated INTEGER NOT NULL
            )
            """.trimIndent(),
            0,
        )
        driver.execute(
            null,
            "CREATE TABLE Settings (key TEXT NOT NULL PRIMARY KEY, value TEXT NOT NULL)",
            0,
        )
        driver.execute(
            null,
            "INSERT INTO Document VALUES ('legacy-doc', 'Legacy', 'Body', 0, 1)",
            0,
        )

        RavenDatabase.Schema.migrate(driver, 1, RavenDatabase.Schema.version)

        val document = RavenDatabase(driver).documentQueries.selectById("legacy-doc").executeAsOne()
        assertEquals("Legacy", document.title)
        assertNull(document.path)
    }

    private fun repositoryWithEngine(engine: MockEngine): DocumentRepositoryImpl {
        settingsRepository.saveEndpoint("http://localhost:8080")
        settingsRepository.saveApiKey("test-key")
        settingsRepository.saveVault("test-vault")
        return DocumentRepositoryImpl(
            HttpClient(engine) {
                install(ContentNegotiation) { json() }
            },
            database,
            settingsRepository,
        )
    }

    private fun document(content: String = "body") = Document(
        id = "notes/test-page",
        title = "Test Page",
        content = content,
        path = "notes/test-page.md",
        isFavorite = false,
        lastUpdated = 1L,
    )
}
