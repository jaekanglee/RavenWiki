package com.ppizil.raven.common.ui

import com.ppizil.raven.common.db.Document
import com.ppizil.raven.common.repository.DocumentRepository
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

class MainViewModel(
    private val documentRepository: DocumentRepository
) {
    private val scope = CoroutineScope(Dispatchers.Main)

    val documents: StateFlow<List<Document>> = documentRepository.getAllDocuments()
        .stateIn(
            scope = scope,
            started = SharingStarted.WhileSubscribed(5000),
            initialValue = emptyList()
        )

    fun sync() {
        scope.launch {
            documentRepository.syncAllDocuments()
        }
    }
}
