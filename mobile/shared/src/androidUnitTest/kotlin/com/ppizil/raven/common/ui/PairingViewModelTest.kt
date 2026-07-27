package com.ppizil.raven.common.ui

import com.ppizil.raven.common.presentation.viewmodel.PairingViewModel
import com.ppizil.raven.common.presentation.viewmodel.PairingState
import com.ppizil.raven.common.presentation.viewmodel.PairingIntent
import com.ppizil.raven.common.domain.usecase.PairDeviceUseCase
import com.ppizil.raven.common.framework.qr.FakeQrScanner
import com.ppizil.raven.common.data.repository.SettingsRepositoryImpl
import com.ppizil.raven.common.db.RavenDatabase
import app.cash.sqldelight.driver.jdbc.sqlite.JdbcSqliteDriver
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.advanceUntilIdle
import org.junit.After
import org.junit.Before
import org.junit.Test
import kotlin.test.assertEquals

class PairingViewModelTest {

    private lateinit var viewModel: PairingViewModel
    private val testDispatcher = StandardTestDispatcher()

    @Before
    fun setup() {
        Dispatchers.setMain(testDispatcher)
        val driver = JdbcSqliteDriver(JdbcSqliteDriver.IN_MEMORY)
        RavenDatabase.Schema.create(driver)
        val database = RavenDatabase(driver)
        val settingsRepository = SettingsRepositoryImpl(database)
        val qrScanner = FakeQrScanner()
        val pairDeviceUseCase = PairDeviceUseCase(qrScanner, settingsRepository)
        viewModel = PairingViewModel(pairDeviceUseCase)
    }

    @After
    fun tearDown() {
        Dispatchers.resetMain()
    }

    @Test
    fun testStartPairingSuccess() = runTest(testDispatcher) {
        assertEquals(PairingState.Idle, viewModel.state.value)
        viewModel.sendIntent(PairingIntent.StartPairing)
        advanceUntilIdle()
        assertEquals(PairingState.Success, viewModel.state.value)
    }
}
