package com.ppizil.raven.common.presentation.di

import org.koin.core.context.startKoin
import org.koin.core.module.Module
import org.koin.dsl.module
import io.ktor.client.*
import io.ktor.client.plugins.contentnegotiation.*
import io.ktor.serialization.kotlinx.json.*
import kotlinx.serialization.json.Json
import com.ppizil.raven.common.domain.repository.SettingsRepository
import com.ppizil.raven.common.domain.repository.DocumentRepository
import com.ppizil.raven.common.data.repository.SettingsRepositoryImpl
import com.ppizil.raven.common.data.repository.DocumentRepositoryImpl
import com.ppizil.raven.common.domain.usecase.PairDeviceUseCase
import com.ppizil.raven.common.domain.usecase.GetDocumentsUseCase
import com.ppizil.raven.common.domain.usecase.SyncDocumentsUseCase
import com.ppizil.raven.common.domain.usecase.SaveDocumentUseCase
import com.ppizil.raven.common.domain.usecase.DeleteDocumentUseCase
import com.ppizil.raven.common.framework.qr.QrScanner
import com.ppizil.raven.common.framework.qr.FakeQrScanner
import com.ppizil.raven.common.presentation.viewmodel.PairingViewModel
import com.ppizil.raven.common.presentation.viewmodel.MainViewModel

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
    
    // Repositories
    single<SettingsRepository> { SettingsRepositoryImpl(get()) }
    single<DocumentRepository> { DocumentRepositoryImpl(get(), get(), get()) }
    
    // Framework
    single<QrScanner> { FakeQrScanner() }
    
    // UseCases
    factory { PairDeviceUseCase(get(), get()) }
    factory { GetDocumentsUseCase(get()) }
    factory { SyncDocumentsUseCase(get()) }
    factory { SaveDocumentUseCase(get()) }
    factory { DeleteDocumentUseCase(get()) }
    
    // ViewModels
    factory { PairingViewModel(get(), get()) }
    factory { MainViewModel(get(), get(), get(), get()) }
}
