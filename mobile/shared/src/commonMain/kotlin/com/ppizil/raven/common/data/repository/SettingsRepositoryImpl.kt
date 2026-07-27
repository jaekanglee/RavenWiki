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
}
