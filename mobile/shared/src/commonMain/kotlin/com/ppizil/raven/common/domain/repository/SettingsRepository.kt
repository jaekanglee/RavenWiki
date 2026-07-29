package com.ppizil.raven.common.domain.repository

interface SettingsRepository {
    fun saveApiKey(key: String)
    fun getApiKey(): String?
    fun saveEndpoint(endpoint: String)
    fun getEndpoint(): String?
    fun setDarkMode(isDark: Boolean)
    fun isDarkMode(): Boolean
}
