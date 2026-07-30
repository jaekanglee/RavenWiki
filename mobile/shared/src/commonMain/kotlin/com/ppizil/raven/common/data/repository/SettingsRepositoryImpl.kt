package com.ppizil.raven.common.data.repository

import com.ppizil.raven.common.db.RavenDatabase
import com.ppizil.raven.common.domain.repository.SettingsRepository

class SettingsRepositoryImpl(database: RavenDatabase) : SettingsRepository {
    private val queries = database.documentQueries

    override fun saveApiKey(key: String) {
        queries.setSetting("api_key", key)
    }

    override fun getApiKey(): String? {
        return queries.getSetting("api_key").executeAsOneOrNull()
    }

    override fun saveEndpoint(endpoint: String) {
        queries.setSetting("endpoint", endpoint)
    }

    override fun getEndpoint(): String? {
        return queries.getSetting("endpoint").executeAsOneOrNull()
    }

    override fun saveVault(vault: String) {
        queries.setSetting("vault", vault)
    }

    override fun getVault(): String? {
        return queries.getSetting("vault").executeAsOneOrNull()
    }

    override fun setDarkMode(isDark: Boolean) {
        queries.setSetting("dark_mode", isDark.toString())
    }

    override fun isDarkMode(): Boolean {
        // Default to true (Forced Dark Mode First as per ADR) if not set
        return queries.getSetting("dark_mode").executeAsOneOrNull()?.toBoolean() ?: true
    }
}
