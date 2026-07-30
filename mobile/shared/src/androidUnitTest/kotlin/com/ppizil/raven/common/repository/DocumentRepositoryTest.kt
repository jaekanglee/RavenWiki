package com.ppizil.raven.common.repository

import app.cash.sqldelight.driver.jdbc.sqlite.JdbcSqliteDriver
import com.ppizil.raven.common.data.repository.DocumentRepositoryImpl
import com.ppizil.raven.common.data.repository.SettingsRepositoryImpl
import com.ppizil.raven.common.data.remote.ravenJson
import com.ppizil.raven.common.data.repository.canonicalPageSlug
import com.ppizil.raven.common.db.RavenDatabase
import com.ppizil.raven.common.domain.model.Document
import io.ktor.client.HttpClient
import io.ktor.client.engine.mock.MockEngine
import io.ktor.client.engine.mock.MockRequestHandleScope
import io.ktor.client.engine.mock.respond
import io.ktor.client.engine.mock.toByteArray
import io.ktor.client.plugins.contentnegotiation.ContentNegotiation
import io.ktor.client.request.HttpRequestData
import io.ktor.client.request.HttpResponseData
import io.ktor.http.HttpHeaders
import io.ktor.http.HttpMethod
import io.ktor.http.HttpStatusCode
import io.ktor.http.headersOf
import io.ktor.serialization.kotlinx.json.json
import java.io.IOException
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.test.runTest
import org.junit.Before
import org.junit.Test
import kotlin.test.assertEquals
import kotlin.test.assertNull
import kotlin.test.assertTrue

private const val VAULT = "test-vault"

class DocumentRepositoryTest {
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
        settingsRepository.saveVault(VAULT)
    }

    private fun MockRequestHandleScope.jsonOk(body: String) =
        respond(body, HttpStatusCode.OK, headersOf(HttpHeaders.ContentType, "application/json"))

    private fun repositoryWithEngine(engine: MockEngine) = DocumentRepositoryImpl(
        HttpClient(engine) { install(ContentNegotiation) { json(ravenJson) } },
        database,
        settingsRepository,
    )

    private fun repositoryRouting(
        route: suspend MockRequestHandleScope.(HttpRequestData) -> HttpResponseData,
    ) = repositoryWithEngine(MockEngine { request -> route(request) })

    private fun pagesBody(vault: String) =
        """{"ok":true,"vault":"$vault","pages":[{"slug":"content/index","title":"$vault home",""" +
            """"type":"concept","collection":"content","status":"current","updated":"2026-07-30"}]}"""

    private fun document(content: String = "body") = Document(
        vault = VAULT,
        id = "notes/test-page",
        title = "Test Page",
        content = content,
        type = "concept",
        path = "notes/test-page.md",
        isFavorite = false,
        lastUpdated = 1L,
    )

    @Test
    fun fetchVaultsReturnsHostVaultNames() = runTest {
        val repository = repositoryRouting {
            jsonOk(
                """{"ok":true,"vaults":[""" +
                    """{"name":"babymoa","path":"/v/babymoa","mode":"agent","owner":"u","default":true},""" +
                    """{"name":"hermes-infra","path":"/v/h","mode":"agent","owner":"u","default":false}],""" +
                    """"vaults_root":"/v"}""",
            )
        }

        val vaults = repository.fetchVaults()

        assertEquals(listOf("babymoa", "hermes-infra"), vaults.map { it.name })
        assertEquals(listOf(true, false), vaults.map { it.isDefault })
        assertEquals("/v/babymoa", vaults.first().path)
    }

    @Test
    fun documentsAreScopedPerVault() = runTest {
        val repository = repositoryRouting { request ->
            val segments = request.url.encodedPath.trim('/').split('/')
            jsonOk(pagesBody(segments[segments.indexOf("vaults") + 1]))
        }

        repository.syncDocuments("babymoa")
        repository.syncDocuments("hermes-infra")

        val babymoa = repository.getDocuments("babymoa").first()
        val hermes = repository.getDocuments("hermes-infra").first()
        assertEquals(listOf("babymoa home"), babymoa.map { it.title })
        assertEquals(listOf("hermes-infra home"), hermes.map { it.title })
        assertEquals("content/index", babymoa.single().id)
        assertEquals("content/index", hermes.single().id)
    }

    @Test
    fun openingDocumentStoresServerContentNotType() = runTest {
        val repository = repositoryRouting { request ->
            if (request.url.encodedPath.endsWith("/pages")) {
                jsonOk(pagesBody("babymoa"))
            } else {
                jsonOk(
                    """{"ok":true,"vault":"babymoa","slug":"content/index",""" +
                        """"file_path":"/v/babymoa/content/index.md","frontmatter":{"type":"concept"},""" +
                        """"content":"# babymoa\n\n실제 본문 문장","backlinks":[]}""",
                )
            }
        }

        repository.syncDocuments("babymoa")
        repository.fetchDocument("babymoa", "content/index")

        val document = repository.getDocuments("babymoa").first().single()
        assertTrue(document.content.contains("실제 본문 문장"), "본문: ${document.content}")
        assertEquals("concept", document.type)
    }

    @Test
    fun syncKeepsAlreadyFetchedContent() = runTest {
        val repository = repositoryRouting { request ->
            if (request.url.encodedPath.endsWith("/pages")) {
                jsonOk(pagesBody("babymoa"))
            } else {
                jsonOk(
                    """{"ok":true,"vault":"babymoa","slug":"content/index",""" +
                        """"content":"보존되어야 하는 본문"}""",
                )
            }
        }

        repository.syncDocuments("babymoa")
        repository.fetchDocument("babymoa", "content/index")
        repository.syncDocuments("babymoa")

        assertEquals(
            "보존되어야 하는 본문",
            repository.getDocuments("babymoa").first().single().content,
        )
    }

    @Test
    fun searchFindsDocumentWhoseBodyIsNotCached() = runTest {
        val repository = repositoryRouting { request ->
            when {
                request.url.encodedPath.endsWith("/pages") -> jsonOk(pagesBody(VAULT))
                request.url.encodedPath.endsWith("/hybrid-search") -> jsonOk(
                    """{"ok":true,"vault":"$VAULT","query":"생소한단어","results":[""" +
                        """{"slug":"content/never-opened","title":"열어보지 않은 문서","type":"concept","score":1.5}]}""",
                )
                else -> jsonOk("""{"ok":true,"vault":"$VAULT","results":[]}""")
            }
        }
        repository.syncDocuments(VAULT)
        val cached = repository.getDocuments(VAULT).first()
        assertTrue(cached.all { it.content.isBlank() }, "캐시 본문이 이뭐 차 있으면 RED 전제가 깨진다")

        val hits = repository.searchDocuments(VAULT, "생소한단어")

        assertEquals(listOf("content/never-opened"), hits.map { it.slug })
        assertEquals("열어보지 않은 문서", hits.single().title)
        assertEquals(VAULT, hits.single().vault)
    }

    @Test
    fun searchIsScopedToRequestedVaultAndSkipsBlankQuery() = runTest {
        val requested = mutableListOf<String>()
        val repository = repositoryRouting { request ->
            requested += request.url.encodedPath + "?" + request.url.encodedQuery
            jsonOk("""{"ok":true,"vault":"babymoa","results":[]}""")
        }

        assertTrue(repository.searchDocuments("babymoa", "   ").isEmpty())
        assertTrue(requested.isEmpty(), "번 쿼리로 서버를 도되면 안 된다: $requested")

        repository.searchDocuments("babymoa", "ollama")

        assertTrue(
            requested.first().startsWith("/api/vaults/babymoa/hybrid-search?"),
            "검색 요칭: $requested",
        )
        assertTrue(requested.first().contains("query=ollama"), "검색 요칭: $requested")
    }

    @Test
    fun searchFallsBackToSnippetEndpointWhenHybridHasNoHits() = runTest {
        val repository = repositoryRouting { request ->
            if (request.url.encodedPath.endsWith("/hybrid-search")) {
                jsonOk("""{"ok":true,"vault":"$VAULT","results":[]}""")
            } else {
                jsonOk(
                    """{"ok":true,"vault":"$VAULT","query":"outbox","results":[""" +
                        """{"slug":"content/journal/2026-07-30","title":"오늘 기록","type":"journal",""" +
                        """"snippet":"…<mark>outbox</mark> 재전속 동기화…","score":3.0}]}""",
                )
            }
        }

        val hits = repository.searchDocuments(VAULT, "outbox")

        assertEquals(listOf("content/journal/2026-07-30"), hits.map { it.slug })
        assertEquals("…outbox 재전속 동기화…", hits.single().snippet)
    }

    @Test
    fun searchHitOutsideCacheBecomesOpenable() = runTest {
        val repository = repositoryRouting { request ->
            when {
                request.url.encodedPath.endsWith("/hybrid-search") -> jsonOk(
                    """{"ok":true,"vault":"$VAULT","results":[""" +
                        """{"slug":"content/fresh-on-pc","title":"PC에서 방금 만든 문서","type":"note","score":1.0}]}""",
                )
                else -> jsonOk(
                    """{"ok":true,"vault":"$VAULT","slug":"content/fresh-on-pc","content":"동기화 전 본문"}""",
                )
            }
        }

        repository.searchDocuments(VAULT, "방금")
        repository.fetchDocument(VAULT, "content/fresh-on-pc")

        val document = repository.getDocuments(VAULT).first().single()
        assertEquals("PC에서 방금 만든 문서", document.title)
        assertEquals("동기화 전 본문", document.content)
    }

    @Test
    fun offlineSaveKeepsContentAndPendingWrite() = runTest {
        val repository = repositoryWithEngine(MockEngine { throw IOException("offline") })
        val document = document(content = "content written offline")

        repository.saveDocument(document)

        val stored = database.documentQueries.selectById(VAULT, document.id).executeAsOne()
        assertEquals("content written offline", stored.content)
        val pending = repository.pendingWrites().single()
        assertEquals(VAULT, pending.vault)
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
        val onlineRepository = repositoryRouting { request ->
            assertEquals(HttpMethod.Put, request.method)
            assertEquals("/api/vaults/$VAULT/pages/notes/test-page", request.url.encodedPath)
            sentBody = request.body.toByteArray().decodeToString()
            respond("", HttpStatusCode.NoContent)
        }

        onlineRepository.flushPendingWrites()

        assertTrue(sentBody.contains("\"content\":\"queued body\""))
        assertTrue(onlineRepository.pendingWrites().isEmpty())
    }

    @Test
    fun pendingWritesOfDifferentVaultsDoNotCollide() = runTest {
        val repository = repositoryWithEngine(MockEngine { throw IOException("offline") })

        repository.saveDocument(document(content = "from test-vault"))
        repository.saveDocument(
            document(content = "from other-vault").copy(vault = "other-vault"),
        )

        val pending = repository.pendingWrites()
        assertEquals(2, pending.size)
        assertEquals(
            listOf("from other-vault", "from test-vault"),
            pending.mapNotNull { it.payload }.sorted(),
        )
    }

    @Test
    fun failedRemoteWriteRecordsErrorAndConflictKind() = runTest {
        val conflictRepository = repositoryWithEngine(
            MockEngine { respond("stale version", HttpStatusCode.PreconditionFailed) },
        )

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
    fun migratesVersionOneInstallWithoutLosingData() {
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
        driver.execute(null, "INSERT INTO Document VALUES ('legacy-doc', 'Legacy', 'Body', 0, 1)", 0)
        driver.execute(null, "INSERT INTO Settings VALUES ('vault', 'legacy-vault')", 0)

        RavenDatabase.Schema.migrate(driver, 1, RavenDatabase.Schema.version)

        val migrated = RavenDatabase(driver).documentQueries
            .selectById("legacy-vault", "legacy-doc")
            .executeAsOne()
        assertEquals("Legacy", migrated.title)
        assertEquals("Body", migrated.content)
        assertEquals("legacy-vault", migrated.vault)
        assertNull(migrated.path)
    }

    @Test
    fun migratesVersionThreeInstallKeepingPendingWrites() {
        val driver = JdbcSqliteDriver(JdbcSqliteDriver.IN_MEMORY)
        driver.execute(
            null,
            """
            CREATE TABLE Document (
                id TEXT NOT NULL PRIMARY KEY,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                path TEXT,
                isFavorite INTEGER DEFAULT 0,
                lastUpdated INTEGER NOT NULL
            )
            """.trimIndent(),
            0,
        )
        driver.execute(
            null,
            """
            CREATE TABLE PendingWrite (
                slug TEXT NOT NULL PRIMARY KEY,
                operation TEXT NOT NULL,
                payload TEXT,
                attemptCount INTEGER NOT NULL DEFAULT 0,
                lastError TEXT,
                failureKind TEXT
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
            "INSERT INTO Document VALUES ('notes/queued', 'Queued', 'Offline body', 'notes/queued.md', 0, 7)",
            0,
        )
        driver.execute(
            null,
            "INSERT INTO PendingWrite VALUES ('notes/queued', 'PUT', 'Offline body', 2, 'boom', 'NETWORK')",
            0,
        )

        RavenDatabase.Schema.migrate(driver, 3, RavenDatabase.Schema.version)

        val queries = RavenDatabase(driver).documentQueries
        val migrated = queries.selectById("default", "notes/queued").executeAsOne()
        assertEquals("Offline body", migrated.content)
        val pending = queries.selectPendingWrites().executeAsList().single()
        assertEquals("default", pending.vault)
        assertEquals("notes/queued", pending.slug)
        assertEquals("Offline body", pending.payload)
        assertEquals(2L, pending.attemptCount)
    }
}
