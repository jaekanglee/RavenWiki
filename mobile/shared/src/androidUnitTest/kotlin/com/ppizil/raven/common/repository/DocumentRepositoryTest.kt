package com.ppizil.raven.common.repository

import app.cash.sqldelight.driver.jdbc.sqlite.JdbcSqliteDriver
import com.ppizil.raven.common.db.RavenDatabase
import io.ktor.client.*
import io.ktor.client.engine.mock.*
import io.ktor.client.plugins.contentnegotiation.*
import io.ktor.http.*
import io.ktor.serialization.kotlinx.json.*
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.test.runTest
import kotlinx.serialization.json.Json
import org.junit.Before
import org.junit.Test
import kotlin.test.assertEquals

class DocumentRepositoryTest {

    private lateinit var database: RavenDatabase
    private lateinit var settingsRepository: SettingsRepository
    private lateinit var repository: DocumentRepository
    private lateinit var mockEngine: MockEngine
    private lateinit var httpClient: HttpClient

    @Before
    fun setup() {
        val driver = JdbcSqliteDriver(JdbcSqliteDriver.IN_MEMORY)
        RavenDatabase.Schema.create(driver)
        database = RavenDatabase(driver)
        settingsRepository = SettingsRepository(database)

        mockEngine = MockEngine { request ->
            when (request.url.encodedPath) {
                "/api/docs/1" -> {
                    respond(
                        content = """{"id": "1", "title": "Test Doc", "content": "Hello World"}""",
                        status = HttpStatusCode.OK,
                        headers = headersOf(HttpHeaders.ContentType, "application/json")
                    )
                }
                else -> respondError(HttpStatusCode.NotFound)
            }
        }

        httpClient = HttpClient(mockEngine) {
            install(ContentNegotiation) {
                json(Json { ignoreUnknownKeys = true })
            }
        }

        repository = DocumentRepository(httpClient, database, settingsRepository)
    }

    @Test
    fun testFetchDocumentWithCache() = runTest {
        // Setup credentials
        settingsRepository.saveEndpoint("https://api.raven.local")
        settingsRepository.saveApiKey("fake-key")

        // Initial fetch from remote
        repository.fetchDocument("1")

        // Verify it was saved to DB (Cache)
        val docs = repository.getAllDocuments().first()
        assertEquals(1, docs.size)
        assertEquals("Test Doc", docs[0].title)
        assertEquals("Hello World", docs[0].content)
    }
}
