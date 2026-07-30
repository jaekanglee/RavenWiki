package com.ppizil.raven.common.repository

import com.ppizil.raven.common.data.repository.DocumentRepositoryImpl
import com.ppizil.raven.common.data.repository.SettingsRepositoryImpl
import com.ppizil.raven.common.db.RavenDatabase
import app.cash.sqldelight.driver.jdbc.sqlite.JdbcSqliteDriver
import io.ktor.client.*
import io.ktor.client.engine.mock.*
import io.ktor.client.plugins.contentnegotiation.*
import io.ktor.http.*
import io.ktor.serialization.kotlinx.json.*
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.test.runTest
import org.junit.Before
import org.junit.Test
import kotlin.test.assertEquals
import kotlin.test.assertNull

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
}
