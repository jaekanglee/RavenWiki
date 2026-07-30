package com.ppizil.raven.common.presentation.di

import com.ppizil.raven.common.data.repository.DocumentRepositoryImpl
import com.ppizil.raven.common.data.repository.SettingsRepositoryImpl
import com.ppizil.raven.common.domain.repository.DocumentRepository
import com.ppizil.raven.common.domain.repository.SettingsRepository
import com.ppizil.raven.common.domain.usecase.DeleteDocumentUseCase
import com.ppizil.raven.common.domain.usecase.FetchDocumentUseCase
import com.ppizil.raven.common.domain.usecase.FetchVaultsUseCase
import com.ppizil.raven.common.domain.usecase.GetDocumentsUseCase
import com.ppizil.raven.common.domain.usecase.PairDeviceUseCase
import com.ppizil.raven.common.domain.usecase.SaveDocumentUseCase
import com.ppizil.raven.common.domain.usecase.SyncDocumentsUseCase
import com.ppizil.raven.common.framework.qr.FakeQrScanner
import com.ppizil.raven.common.framework.qr.QrScanner
import com.ppizil.raven.common.presentation.viewmodel.MainViewModel
import com.ppizil.raven.common.presentation.viewmodel.PairingViewModel
import io.ktor.client.HttpClient
import io.ktor.client.plugins.contentnegotiation.ContentNegotiation
import io.ktor.serialization.kotlinx.json.json
import com.ppizil.raven.common.data.remote.ravenJson
import org.koin.core.context.startKoin
import org.koin.core.module.Module
import org.koin.dsl.module

fun initKoin(appModule: Module) = startKoin {
    modules(
        appModule,
        commonModule,
    )
}

val commonModule = module {
    single {
        HttpClient {
            install(ContentNegotiation) {
                json(ravenJson)
            }
        }
    }

    single<SettingsRepository> { SettingsRepositoryImpl(get()) }
    single<DocumentRepository> { DocumentRepositoryImpl(get(), get(), get()) }

    single<QrScanner> { FakeQrScanner() }

    factory { PairDeviceUseCase(get(), get()) }
    factory { GetDocumentsUseCase(get()) }
    factory { SyncDocumentsUseCase(get()) }
    factory { SaveDocumentUseCase(get()) }
    factory { DeleteDocumentUseCase(get()) }
    factory { FetchVaultsUseCase(get()) }
    factory { FetchDocumentUseCase(get()) }

    factory { PairingViewModel(get(), get()) }
    factory { MainViewModel(get(), get(), get(), get(), get(), get(), get()) }
}
