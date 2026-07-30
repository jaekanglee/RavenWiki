package com.ppizil.raven.common.domain.usecase

import com.ppizil.raven.common.domain.model.SearchHit
import com.ppizil.raven.common.domain.repository.DocumentRepository

class SearchDocumentsUseCase(
    private val documentRepository: DocumentRepository,
) {
    suspend operator fun invoke(vault: String, query: String): List<SearchHit> =
        documentRepository.searchDocuments(vault, query)
}
