package com.ppizil.raven.common.di

import org.koin.core.context.startKoin
import org.koin.core.module.Module
import org.koin.dsl.module
import io.ktor.client.*
import io.ktor.client.plugins.contentnegotiation.*
import io.ktor.serialization.kotlinx.json.*
import kotlinx.serialization.json.Json

fun initKoin(appModule: Module) = startKoin {
    modules(
        appModule,
        commonModule
    )
}

val commonModule = module {
    single {
        HttpClient {
            install(ContentNegotiation) {
                json(Json {
                    prettyPrint = true
                    isLenient = true
                    ignoreUnknownKeys = true
                })
            }
        }
    }
    single { com.ppizil.raven.common.repository.SettingsRepository(get()) }
    single { com.ppizil.raven.common.repository.DocumentRepository(get(), get(), get()) }
    single<com.ppizil.raven.common.qr.QrScanner> { com.ppizil.raven.common.qr.FakeQrScanner() }
    factory { com.ppizil.raven.common.ui.PairingViewModel(get(), get()) }
    factory { com.ppizil.raven.common.ui.MainViewModel(get()) }
}
