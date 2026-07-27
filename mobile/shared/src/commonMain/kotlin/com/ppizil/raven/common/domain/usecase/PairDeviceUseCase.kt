package com.ppizil.raven.common.domain.usecase

import com.ppizil.raven.common.domain.repository.SettingsRepository
import com.ppizil.raven.common.framework.qr.QrScanner
import com.ppizil.raven.common.framework.qr.QrResult

class PairDeviceUseCase(
    private val qrScanner: QrScanner,
    private val settingsRepository: SettingsRepository
) {
    suspend operator fun invoke(): QrResult {
        return when (val result = qrScanner.scan()) {
            is QrResult.Success -> {
                settingsRepository.saveEndpoint(result.endpoint)
                settingsRepository.saveApiKey(result.apiKey)
                result
            }
            else -> result
        }
    }
}
