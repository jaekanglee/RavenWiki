package com.ppizil.raven.common.qr

import kotlinx.coroutines.delay

class FakeQrScanner : QrScanner {
    var nextResult: QrResult = QrResult.Success("https://api.raven.local", "fake-api-key")
    
    override suspend fun scan(): QrResult {
        delay(500) // Simulate scanning delay
        return nextResult
    }
}
