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
    data class SaveDocument(val document: com.ppizil.raven.common.domain.model.Document) : MainIntent()
    data class DeleteDocument(val id: String) : MainIntent()
}

enum class ConnectionStatus {
    Idle, Connecting, Success, Error
}

data class MainState(
    val documents: List<Document> = emptyList(),
    val connectionStatus: ConnectionStatus = ConnectionStatus.Idle,
    val errorMessage: String? = null
)

sealed class MainSideEffect {
    data class ShowError(val message: String) : MainSideEffect()
}

class MainViewModel(
    private val getDocumentsUseCase: GetDocumentsUseCase,
    private val syncDocumentsUseCase: SyncDocumentsUseCase,
    private val saveDocumentUseCase: com.ppizil.raven.common.domain.usecase.SaveDocumentUseCase,
    private val deleteDocumentUseCase: com.ppizil.raven.common.domain.usecase.DeleteDocumentUseCase
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
            is MainIntent.SaveDocument -> saveDocument(intent.document)
            is MainIntent.DeleteDocument -> deleteDocument(intent.id)
        }
    }

    private fun deleteDocument(id: String) {
        scope.launch {
            try {
                deleteDocumentUseCase(id)
            } catch (e: Exception) {
                val errorMsg = e.message ?: "Failed to delete document"
                _sideEffect.emit(MainSideEffect.ShowError(errorMsg))
            }
        }
    }

    private fun saveDocument(document: com.ppizil.raven.common.domain.model.Document) {
        scope.launch {
            try {
                saveDocumentUseCase(document)
            } catch (e: Exception) {
                val errorMsg = e.message ?: "Failed to save document"
                _sideEffect.emit(MainSideEffect.ShowError(errorMsg))
            }
        }
    }

    private fun syncDocuments() {
        scope.launch {
            _state.value = _state.value.copy(connectionStatus = ConnectionStatus.Connecting, errorMessage = null)
            try {
                syncDocumentsUseCase()
                _state.value = _state.value.copy(connectionStatus = ConnectionStatus.Success)
            } catch (e: Exception) {
                val errorMsg = e.message ?: "Unknown error"
                _state.value = _state.value.copy(connectionStatus = ConnectionStatus.Error, errorMessage = errorMsg)
                _sideEffect.emit(MainSideEffect.ShowError(errorMsg))
            }
        }
    }
}
