package com.ppizil.raven.common.domain.usecase

import com.ppizil.raven.common.domain.repository.DocumentRepository

class SyncDocumentsUseCase(
    private val documentRepository: DocumentRepository
) {
    suspend operator fun invoke() {
        documentRepository.syncAllDocuments()
    }
}
