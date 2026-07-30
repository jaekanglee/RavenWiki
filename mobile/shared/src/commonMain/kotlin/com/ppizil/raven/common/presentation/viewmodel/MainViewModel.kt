package com.ppizil.raven.common.presentation.viewmodel

import com.ppizil.raven.common.domain.model.Document
import com.ppizil.raven.common.domain.model.SearchHit
import com.ppizil.raven.common.domain.model.VaultSummary
import com.ppizil.raven.common.domain.model.WriteOutcome
import com.ppizil.raven.common.domain.repository.SettingsRepository
import com.ppizil.raven.common.domain.usecase.DeleteDocumentUseCase
import com.ppizil.raven.common.domain.usecase.FetchDocumentUseCase
import com.ppizil.raven.common.domain.usecase.FetchVaultsUseCase
import com.ppizil.raven.common.domain.usecase.GetDocumentsUseCase
import com.ppizil.raven.common.domain.usecase.SaveDocumentUseCase
import com.ppizil.raven.common.domain.usecase.SearchDocumentsUseCase
import com.ppizil.raven.common.domain.usecase.SyncDocumentsUseCase
import com.ppizil.raven.common.presentation.mvi.MviViewModel
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.flatMapLatest
import kotlinx.coroutines.flow.flowOf
import kotlinx.coroutines.launch

sealed class MainIntent {
    object LoadVaults : MainIntent()
    data class SelectVault(val vault: String) : MainIntent()
    object SyncDocuments : MainIntent()
    data class OpenDocument(val id: String) : MainIntent()
    data class Search(val query: String) : MainIntent()
    data class SaveDocument(val document: Document) : MainIntent()
    data class DeleteDocument(val id: String) : MainIntent()
}

enum class ConnectionStatus {
    Idle, Connecting, Success, Error
}

data class MainState(
    val vaults: List<VaultSummary> = emptyList(),
    val selectedVault: String? = null,
    val documents: List<Document> = emptyList(),
    val searchQuery: String = "",
    val searchResults: List<SearchHit> = emptyList(),
    val isSearching: Boolean = false,
    val searchError: String? = null,
    val connectionStatus: ConnectionStatus = ConnectionStatus.Idle,
    val errorMessage: String? = null,
)

sealed class MainSideEffect {
    data class ShowError(val message: String) : MainSideEffect()
    data class ShowNotice(val message: String) : MainSideEffect()
}

@OptIn(ExperimentalCoroutinesApi::class)
class MainViewModel(
    private val getDocumentsUseCase: GetDocumentsUseCase,
    private val syncDocumentsUseCase: SyncDocumentsUseCase,
    private val saveDocumentUseCase: SaveDocumentUseCase,
    private val searchDocumentsUseCase: SearchDocumentsUseCase,
    private val deleteDocumentUseCase: DeleteDocumentUseCase,
    private val fetchVaultsUseCase: FetchVaultsUseCase,
    private val fetchDocumentUseCase: FetchDocumentUseCase,
    private val settingsRepository: SettingsRepository,
) : MviViewModel<MainIntent, MainState, MainSideEffect> {

    private val scope = CoroutineScope(Dispatchers.Main)

    private val _state = MutableStateFlow(
        MainState(selectedVault = settingsRepository.getVault()?.takeIf { it.isNotBlank() }),
    )
    override val state: StateFlow<MainState> = _state.asStateFlow()

    private val _sideEffect = MutableSharedFlow<MainSideEffect>()
    override val sideEffect: SharedFlow<MainSideEffect> = _sideEffect.asSharedFlow()

    private val activeVault = MutableStateFlow(_state.value.selectedVault)
    private var searchJob: Job? = null

    init {
        scope.launch {
            activeVault
                .flatMapLatest { vault ->
                    if (vault.isNullOrBlank()) flowOf(emptyList()) else getDocumentsUseCase(vault)
                }
                .collect { documents ->
                    _state.value = _state.value.copy(documents = documents)
                }
        }
    }

    override fun sendIntent(intent: MainIntent) {
        when (intent) {
            is MainIntent.LoadVaults -> loadVaults()
            is MainIntent.SelectVault -> selectVault(intent.vault)
            is MainIntent.SyncDocuments -> syncDocuments()
            is MainIntent.OpenDocument -> openDocument(intent.id)
            is MainIntent.Search -> search(intent.query)
            is MainIntent.SaveDocument -> saveDocument(intent.document)
            is MainIntent.DeleteDocument -> deleteDocument(intent.id)
        }
    }

    private fun loadVaults() {
        scope.launch {
            _state.value = _state.value.copy(
                connectionStatus = ConnectionStatus.Connecting,
                errorMessage = null,
            )
            runCatching { fetchVaultsUseCase() }
                .onSuccess { vaults ->
                    _state.value = _state.value.copy(
                        vaults = vaults,
                        connectionStatus = ConnectionStatus.Success,
                    )
                }
                .onFailure { failure -> report(failure, "Failed to load vaults") }
        }
    }

    private fun selectVault(vault: String) {
        settingsRepository.saveVault(vault)
        _state.value = _state.value.copy(
            selectedVault = vault,
            documents = emptyList(),
            searchQuery = "",
            searchResults = emptyList(),
            isSearching = false,
            searchError = null,
        )
        activeVault.value = vault
        syncDocuments()
    }

    private fun syncDocuments() {
        val vault = _state.value.selectedVault
        if (vault.isNullOrBlank()) {
            loadVaults()
            return
        }
        scope.launch {
            _state.value = _state.value.copy(
                connectionStatus = ConnectionStatus.Connecting,
                errorMessage = null,
            )
            runCatching { syncDocumentsUseCase(vault) }
                .onSuccess {
                    _state.value = _state.value.copy(connectionStatus = ConnectionStatus.Success)
                }
                .onFailure { failure -> report(failure, "Failed to sync documents") }
        }
    }

    private fun search(query: String) {
        val vault = _state.value.selectedVault
        searchJob?.cancel()
        if (vault.isNullOrBlank() || query.isBlank()) {
            _state.value = _state.value.copy(
                searchQuery = query,
                searchResults = emptyList(),
                isSearching = false,
                searchError = null,
            )
            return
        }
        _state.value = _state.value.copy(
            searchQuery = query,
            isSearching = true,
            searchError = null,
        )
        searchJob = scope.launch {
            runCatching { searchDocumentsUseCase(vault, query) }
                .onSuccess { hits ->
                    _state.value = _state.value.copy(searchResults = hits, isSearching = false)
                }
                .onFailure { failure ->
                    _state.value = _state.value.copy(
                        searchResults = emptyList(),
                        isSearching = false,
                        searchError = failure.message ?: "검색을 마치지 못했습니다",
                    )
                }
        }
    }

    private fun openDocument(id: String) {
        val vault = _state.value.selectedVault ?: return
        scope.launch {
            runCatching { fetchDocumentUseCase(vault, id) }
                .onFailure { failure -> report(failure, "Failed to open document") }
        }
    }

    private fun saveDocument(document: Document) {
        scope.launch {
            runCatching { saveDocumentUseCase(document) }
                .onSuccess { outcome ->
                    when (outcome) {
                        WriteOutcome.Synced -> Unit
                        WriteOutcome.Queued -> _sideEffect.emit(
                            MainSideEffect.ShowNotice(
                                "지금 PC에 닿지 않아 기기에만 저장했습니다. 재연결 후 당겼 내리면 올라가요.",
                            ),
                        )
                        WriteOutcome.Conflict -> _sideEffect.emit(
                            MainSideEffect.ShowError(
                                "PC에서 이 문서가 먼지 바뀌어 서버에 반영하지 않았습니다. 문서를 다시 받아 합치세요.",
                            ),
                        )
                    }
                }
                .onFailure { failure -> report(failure, "Failed to save document") }
        }
    }

    private fun deleteDocument(id: String) {
        val vault = _state.value.selectedVault ?: return
        scope.launch {
            runCatching { deleteDocumentUseCase(vault, id) }
                .onFailure { failure -> report(failure, "Failed to delete document") }
        }
    }

    private suspend fun report(failure: Throwable, fallback: String) {
        val message = failure.message ?: fallback
        _state.value = _state.value.copy(
            connectionStatus = ConnectionStatus.Error,
            errorMessage = message,
        )
        _sideEffect.emit(MainSideEffect.ShowError(message))
    }
}
