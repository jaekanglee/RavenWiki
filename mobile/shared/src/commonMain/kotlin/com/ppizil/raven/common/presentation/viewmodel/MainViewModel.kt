package com.ppizil.raven.common.presentation.viewmodel

import com.ppizil.raven.common.presentation.mvi.MviViewModel
import com.ppizil.raven.common.domain.model.Document
import com.ppizil.raven.common.domain.usecase.GetDocumentsUseCase
import com.ppizil.raven.common.domain.usecase.SyncDocumentsUseCase
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

sealed class MainIntent {
    object SyncDocuments : MainIntent()
}

data class MainState(
    val documents: List<Document> = emptyList(),
    val isLoading: Boolean = false
)

sealed class MainSideEffect {
    data class ShowError(val message: String) : MainSideEffect()
}

class MainViewModel(
    private val getDocumentsUseCase: GetDocumentsUseCase,
    private val syncDocumentsUseCase: SyncDocumentsUseCase
) : MviViewModel<MainIntent, MainState, MainSideEffect> {

    private val scope = CoroutineScope(Dispatchers.Main)
    
    private val _state = MutableStateFlow(MainState())
    override val state: StateFlow<MainState> = _state.asStateFlow()

    private val _sideEffect = MutableSharedFlow<MainSideEffect>()
    override val sideEffect: SharedFlow<MainSideEffect> = _sideEffect.asSharedFlow()

    init {
        scope.launch {
            getDocumentsUseCase().collect { docs ->
                _state.value = _state.value.copy(documents = docs)
            }
        }
    }

    override fun sendIntent(intent: MainIntent) {
        when (intent) {
            is MainIntent.SyncDocuments -> syncDocuments()
        }
    }

    private fun syncDocuments() {
        scope.launch {
            _state.value = _state.value.copy(isLoading = true)
            try {
                syncDocumentsUseCase()
            } catch (e: Exception) {
                _sideEffect.emit(MainSideEffect.ShowError(e.message ?: "Unknown error"))
            } finally {
                _state.value = _state.value.copy(isLoading = false)
            }
        }
    }
}
