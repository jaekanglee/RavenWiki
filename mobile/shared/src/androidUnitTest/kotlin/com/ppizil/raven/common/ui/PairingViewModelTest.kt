package com.ppizil.raven.common.ui

import app.cash.sqldelight.driver.jdbc.sqlite.JdbcSqliteDriver
import com.ppizil.raven.common.db.RavenDatabase
import com.ppizil.raven.common.qr.FakeQrScanner
import com.ppizil.raven.common.repository.SettingsRepository
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Before
import org.junit.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue

@OptIn(ExperimentalCoroutinesApi::class)
class PairingViewModelTest {

    private lateinit var database: RavenDatabase
    private lateinit var settingsRepository: SettingsRepository
    private lateinit var fakeQrScanner: FakeQrScanner
    private lateinit var viewModel: PairingViewModel

    private val testDispatcher = StandardTestDispatcher()

    @Before
    fun setup() {
        Dispatchers.setMain(testDispatcher)
        val driver = JdbcSqliteDriver(JdbcSqliteDriver.IN_MEMORY)
        RavenDatabase.Schema.create(driver)
        database = RavenDatabase(driver)
        settingsRepository = SettingsRepository(database)
        fakeQrScanner = FakeQrScanner()
        viewModel = PairingViewModel(fakeQrScanner, settingsRepository)
    }

    @After
    fun teardown() {
        Dispatchers.resetMain()
    }

    @Test
    fun testStartPairingSuccess() = runTest(testDispatcher) {
        viewModel.startPairing()
        
        // Wait for coroutines to complete
        testScheduler.advanceUntilIdle()
        
        assertEquals(PairingState.Success, viewModel.uiState.value)
        
        val endpoint = settingsRepository.getEndpoint()
        val apiKey = settingsRepository.getApiKey()
        
        assertEquals("https://api.raven.local", endpoint)
        assertEquals("fake-api-key", apiKey)
    }
}
