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
                content = """[{"id": "doc1", "title": "Test", "content": "Content"}]""",
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
        assertEquals("doc1", docs[0].id)
    }
}
