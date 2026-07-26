package com.ppizil.raven.common.ui

import com.ppizil.raven.common.qr.QrResult
import com.ppizil.raven.common.qr.QrScanner
import com.ppizil.raven.common.repository.SettingsRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

class PairingViewModel(
    private val qrScanner: QrScanner,
    private val settingsRepository: SettingsRepository
) {
    private val scope = CoroutineScope(Dispatchers.Main)

    private val _uiState = MutableStateFlow<PairingState>(PairingState.Idle)
    val uiState: StateFlow<PairingState> = _uiState.asStateFlow()

    fun startPairing() {
        scope.launch {
            _uiState.value = PairingState.Scanning
            when (val result = qrScanner.scan()) {
                is QrResult.Success -> {
                    settingsRepository.saveEndpoint(result.endpoint)
                    settingsRepository.saveApiKey(result.apiKey)
                    _uiState.value = PairingState.Success
                }
                is QrResult.Error -> {
                    _uiState.value = PairingState.Error(result.message)
                }
                is QrResult.Cancelled -> {
                    _uiState.value = PairingState.Idle
                }
            }
        }
    }
}

sealed class PairingState {
    object Idle : PairingState()
    object Scanning : PairingState()
    object Success : PairingState()
    data class Error(val message: String) : PairingState()
}
