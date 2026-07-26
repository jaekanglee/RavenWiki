package com.ppizil.raven.common.repository

import com.ppizil.raven.common.db.RavenDatabase
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

class SettingsRepository(database: RavenDatabase) {
    private val queries = database.documentQueries

    fun saveApiKey(key: String) {
        queries.setSetting("api_key", key)
    }

    fun getApiKey(): String? {
        return queries.getSetting("api_key").executeAsOneOrNull()
    }

    fun saveEndpoint(endpoint: String) {
        queries.setSetting("endpoint", endpoint)
    }

    fun getEndpoint(): String? {
        return queries.getSetting("endpoint").executeAsOneOrNull()
    }
}
