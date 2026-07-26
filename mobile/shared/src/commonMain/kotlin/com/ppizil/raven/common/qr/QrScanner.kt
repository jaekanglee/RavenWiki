package com.ppizil.raven.common.qr

interface QrScanner {
    suspend fun scan(): QrResult
}

sealed class QrResult {
    data class Success(val endpoint: String, val apiKey: String) : QrResult()
    data class Error(val message: String) : QrResult()
    object Cancelled : QrResult()
}
