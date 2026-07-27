package com.ppizil.raven.common.domain.usecase

import com.ppizil.raven.common.domain.model.Document
import com.ppizil.raven.common.domain.repository.DocumentRepository
import kotlinx.coroutines.flow.Flow

class GetDocumentsUseCase(
    private val documentRepository: DocumentRepository
) {
    operator fun invoke(): Flow<List<Document>> {
        return documentRepository.getAllDocuments()
    }
}
