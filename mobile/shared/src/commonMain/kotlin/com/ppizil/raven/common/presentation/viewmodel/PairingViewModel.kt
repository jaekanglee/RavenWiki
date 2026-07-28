package com.ppizil.raven.common.presentation.viewmodel

import com.ppizil.raven.common.presentation.mvi.MviViewModel
import com.ppizil.raven.common.domain.usecase.PairDeviceUseCase
import com.ppizil.raven.common.framework.qr.QrResult
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

sealed class PairingIntent {
    object StartPairing : PairingIntent()
    data class PairManual(val endpoint: String) : PairingIntent()
}

sealed class PairingState {
    object Idle : PairingState()
    object Scanning : PairingState()
    object Success : PairingState()
    data class Error(val message: String) : PairingState()
}

sealed class PairingSideEffect {
    object NavigateToMain : PairingSideEffect()
}

class PairingViewModel(
    private val pairDeviceUseCase: PairDeviceUseCase,
    private val settingsRepository: com.ppizil.raven.common.domain.repository.SettingsRepository
) : MviViewModel<PairingIntent, PairingState, PairingSideEffect> {

    private val scope = CoroutineScope(Dispatchers.Main)
    
    private val _state = MutableStateFlow<PairingState>(PairingState.Idle)
    override val state: StateFlow<PairingState> = _state.asStateFlow()

    private val _sideEffect = MutableSharedFlow<PairingSideEffect>()
    override val sideEffect: SharedFlow<PairingSideEffect> = _sideEffect.asSharedFlow()

    override fun sendIntent(intent: PairingIntent) {
        when (intent) {
            is PairingIntent.StartPairing -> startPairing()
            is PairingIntent.PairManual -> pairManual(intent.endpoint)
        }
    }

    private fun startPairing() {
        scope.launch {
            _state.value = PairingState.Scanning
            when (val result = pairDeviceUseCase()) {
                is QrResult.Success -> {
                    _state.value = PairingState.Success
                    _sideEffect.emit(PairingSideEffect.NavigateToMain)
                }
                is QrResult.Error -> {
                    _state.value = PairingState.Error(result.message)
                }
                is QrResult.Cancelled -> {
                    _state.value = PairingState.Idle
                }
            }
        }
    }

    private fun formatEndpoint(input: String): String {
        var formatted = input.trim().trimEnd('/')
        if (formatted.isBlank()) return formatted
        
        if (!formatted.startsWith("http://") && !formatted.startsWith("https://")) {
            formatted = "http://$formatted"
        }
        
        val withoutScheme = formatted.substringAfter("://")
        val domainOrIp = withoutScheme.substringBefore("/")
        if (!domainOrIp.contains(":")) {
            formatted = formatted.replaceFirst(domainOrIp, "$domainOrIp:8765")
        }
        
        return formatted
    }

    private fun pairManual(endpoint: String) {
        scope.launch {
            val formattedEndpoint = formatEndpoint(endpoint)
            settingsRepository.saveEndpoint(formattedEndpoint)
            _state.value = PairingState.Success
            _sideEffect.emit(PairingSideEffect.NavigateToMain)
        }
    }
}
