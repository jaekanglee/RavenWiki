package com.ppizil.raven.common.domain.usecase

import com.ppizil.raven.common.domain.repository.DocumentRepository

class DeleteDocumentUseCase(
    private val documentRepository: DocumentRepository
) {
    suspend operator fun invoke(vault: String, id: String) =
        documentRepository.deleteDocument(vault, id)
}
