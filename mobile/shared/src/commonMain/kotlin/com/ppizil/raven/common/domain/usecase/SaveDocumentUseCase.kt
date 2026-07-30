package com.ppizil.raven.common.domain.usecase

import com.ppizil.raven.common.domain.model.Document
import com.ppizil.raven.common.domain.model.WriteOutcome
import com.ppizil.raven.common.domain.repository.DocumentRepository

class SaveDocumentUseCase(
    private val documentRepository: DocumentRepository
) {
    suspend operator fun invoke(document: Document): WriteOutcome =
        documentRepository.saveDocument(document)
}
