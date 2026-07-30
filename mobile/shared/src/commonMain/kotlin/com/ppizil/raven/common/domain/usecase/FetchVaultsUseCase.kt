package com.ppizil.raven.common.domain.usecase

import com.ppizil.raven.common.domain.model.VaultSummary
import com.ppizil.raven.common.domain.repository.DocumentRepository

class FetchVaultsUseCase(
    private val documentRepository: DocumentRepository
) {
    suspend operator fun invoke(): List<VaultSummary> = documentRepository.fetchVaults()
}
