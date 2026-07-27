import os
import shutil

base_pkg = 'mobile/shared/src/commonMain/kotlin/com/ppizil/raven/common'

def write_file(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        f.write(content)

# 1. domain/model/Document.kt
write_file(f'{base_pkg}/domain/model/Document.kt', """package com.ppizil.raven.common.domain.model

data class Document(
    val id: String,
    val title: String,
    val content: String,
    val isFavorite: Boolean,
    val lastUpdated: Long
)
""")

# 2. domain/repository/SettingsRepository.kt
write_file(f'{base_pkg}/domain/repository/SettingsRepository.kt', """package com.ppizil.raven.common.domain.repository

interface SettingsRepository {
    fun saveApiKey(key: String)
    fun getApiKey(): String?
    fun saveEndpoint(endpoint: String)
    fun getEndpoint(): String?
}
""")

# 3. domain/repository/DocumentRepository.kt
write_file(f'{base_pkg}/domain/repository/DocumentRepository.kt', """package com.ppizil.raven.common.domain.repository

import com.ppizil.raven.common.domain.model.Document
import kotlinx.coroutines.flow.Flow

interface DocumentRepository {
    fun getAllDocuments(): Flow<List<Document>>
    suspend fun fetchDocument(id: String)
    suspend fun syncAllDocuments()
}
""")

# 4. domain/usecase/
write_file(f'{base_pkg}/domain/usecase/PairDeviceUseCase.kt', """package com.ppizil.raven.common.domain.usecase

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
""")

write_file(f'{base_pkg}/domain/usecase/GetDocumentsUseCase.kt', """package com.ppizil.raven.common.domain.usecase

import com.ppizil.raven.common.domain.model.Document
import com.ppizil.raven.common.domain.repository.DocumentRepository
import kotlinx.coroutines.flow.Flow

class GetDocumentsUseCase(
    private val documentRepository: DocumentRepository
) {
    operator fun invoke(): Flow<List<Document>> {
        return documentRepository.getAllDocuments()
    }
}
""")

write_file(f'{base_pkg}/domain/usecase/SyncDocumentsUseCase.kt', """package com.ppizil.raven.common.domain.usecase

import com.ppizil.raven.common.domain.repository.DocumentRepository

class SyncDocumentsUseCase(
    private val documentRepository: DocumentRepository
) {
    suspend operator fun invoke() {
        documentRepository.syncAllDocuments()
    }
}
""")

# 5. data/remote/model/DocumentDto.kt
write_file(f'{base_pkg}/data/remote/model/DocumentDto.kt', """package com.ppizil.raven.common.data.remote.model

import kotlinx.serialization.Serializable

@Serializable
data class DocumentDto(val id: String, val title: String, val content: String)
""")

# 6. data/mapper/DocumentMapper.kt
write_file(f'{base_pkg}/data/mapper/DocumentMapper.kt', """package com.ppizil.raven.common.data.mapper

import com.ppizil.raven.common.db.Document as DbDocument
import com.ppizil.raven.common.domain.model.Document

fun DbDocument.toDomainModel(): Document {
    return Document(
        id = this.id,
        title = this.title,
        content = this.content ?: "",
        isFavorite = this.isFavorite ?: false,
        lastUpdated = this.lastUpdated ?: 0L
    )
}
""")

# 7. data/repository/SettingsRepositoryImpl.kt
write_file(f'{base_pkg}/data/repository/SettingsRepositoryImpl.kt', """package com.ppizil.raven.common.data.repository

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
""")

# 8. data/repository/DocumentRepositoryImpl.kt
write_file(f'{base_pkg}/data/repository/DocumentRepositoryImpl.kt', """package com.ppizil.raven.common.data.repository

import com.ppizil.raven.common.db.RavenDatabase
import com.ppizil.raven.common.domain.model.Document
import com.ppizil.raven.common.domain.repository.DocumentRepository
import com.ppizil.raven.common.domain.repository.SettingsRepository
import com.ppizil.raven.common.data.remote.model.DocumentDto
import com.ppizil.raven.common.data.mapper.toDomainModel
import io.ktor.client.*
import io.ktor.client.request.*
import io.ktor.client.call.body
import io.ktor.http.headers
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import app.cash.sqldelight.coroutines.asFlow
import app.cash.sqldelight.coroutines.mapToList
import kotlinx.coroutines.Dispatchers

class DocumentRepositoryImpl(
    private val httpClient: HttpClient,
    private val database: RavenDatabase,
    private val settingsRepository: SettingsRepository
) : DocumentRepository {
    private val queries = database.documentQueries

    override fun getAllDocuments(): Flow<List<Document>> {
        return queries.selectAll().asFlow().mapToList(Dispatchers.Default).map { list ->
            list.map { it.toDomainModel() }
        }
    }

    override suspend fun fetchDocument(id: String) {
        val endpoint = settingsRepository.getEndpoint() ?: return
        val apiKey = settingsRepository.getApiKey() ?: return
        
        try {
            val response = httpClient.get("$endpoint/api/docs/$id") {
                headers {
                    append("Authorization", "Bearer $apiKey")
                }
            }
            val doc = response.body<DocumentDto>()
            queries.insertDocument(doc.id, doc.title, doc.content, false, System.currentTimeMillis())
        } catch (e: Exception) {
            println("Failed to fetch document: ${e.message}")
        }
    }

    override suspend fun syncAllDocuments() {
        val endpoint = settingsRepository.getEndpoint() ?: return
        val apiKey = settingsRepository.getApiKey() ?: return

        try {
            val response = httpClient.get("$endpoint/api/docs") {
                headers {
                    append("Authorization", "Bearer $apiKey")
                }
            }
            val docs = response.body<List<DocumentDto>>()
            docs.forEach { doc ->
                queries.insertDocument(doc.id, doc.title, doc.content, false, System.currentTimeMillis())
            }
        } catch (e: Exception) {
            println("Failed to sync documents: ${e.message}")
        }
    }
}
""")

# 9. presentation/mvi/MviViewModel.kt
write_file(f'{base_pkg}/presentation/mvi/MviViewModel.kt', """package com.ppizil.raven.common.presentation.mvi

import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.SharedFlow

interface MviViewModel<Intent, State, SideEffect> {
    val state: StateFlow<State>
    val sideEffect: SharedFlow<SideEffect>
    fun sendIntent(intent: Intent)
}
""")

# 10. presentation/viewmodel/PairingViewModel.kt
write_file(f'{base_pkg}/presentation/viewmodel/PairingViewModel.kt', """package com.ppizil.raven.common.presentation.viewmodel

import com.ppizil.raven.common.presentation.mvi.MviViewModel
import com.ppizil.raven.common.domain.usecase.PairDeviceUseCase
import com.ppizil.raven.common.framework.qr.QrResult
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

sealed class PairingIntent {
    object StartPairing : PairingIntent()
}

sealed class PairingState {
    object Idle : PairingState()
    object Scanning : PairingState()
    object Success : PairingState()
    data class Error(val message: String) : PairingState()
}

sealed class PairingSideEffect {
    object NavigateToMain : PairingSideEffect()
}

class PairingViewModel(
    private val pairDeviceUseCase: PairDeviceUseCase
) : MviViewModel<PairingIntent, PairingState, PairingSideEffect> {

    private val scope = CoroutineScope(Dispatchers.Main)
    
    private val _state = MutableStateFlow<PairingState>(PairingState.Idle)
    override val state: StateFlow<PairingState> = _state.asStateFlow()

    private val _sideEffect = MutableSharedFlow<PairingSideEffect>()
    override val sideEffect: SharedFlow<PairingSideEffect> = _sideEffect.asSharedFlow()

    override fun sendIntent(intent: PairingIntent) {
        when (intent) {
            is PairingIntent.StartPairing -> startPairing()
        }
    }

    private fun startPairing() {
        scope.launch {
            _state.value = PairingState.Scanning
            when (val result = pairDeviceUseCase()) {
                is QrResult.Success -> {
                    _state.value = PairingState.Success
                    _sideEffect.emit(PairingSideEffect.NavigateToMain)
                }
                is QrResult.Error -> {
                    _state.value = PairingState.Error(result.message)
                }
                is QrResult.Cancelled -> {
                    _state.value = PairingState.Idle
                }
            }
        }
    }
}
""")

# 11. presentation/viewmodel/MainViewModel.kt
write_file(f'{base_pkg}/presentation/viewmodel/MainViewModel.kt', """package com.ppizil.raven.common.presentation.viewmodel

import com.ppizil.raven.common.presentation.mvi.MviViewModel
import com.ppizil.raven.common.domain.model.Document
import com.ppizil.raven.common.domain.usecase.GetDocumentsUseCase
import com.ppizil.raven.common.domain.usecase.SyncDocumentsUseCase
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

sealed class MainIntent {
    object SyncDocuments : MainIntent()
}

data class MainState(
    val documents: List<Document> = emptyList(),
    val isLoading: Boolean = false
)

sealed class MainSideEffect {
    data class ShowError(val message: String) : MainSideEffect()
}

class MainViewModel(
    private val getDocumentsUseCase: GetDocumentsUseCase,
    private val syncDocumentsUseCase: SyncDocumentsUseCase
) : MviViewModel<MainIntent, MainState, MainSideEffect> {

    private val scope = CoroutineScope(Dispatchers.Main)
    
    private val _state = MutableStateFlow(MainState())
    override val state: StateFlow<MainState> = _state.asStateFlow()

    private val _sideEffect = MutableSharedFlow<MainSideEffect>()
    override val sideEffect: SharedFlow<MainSideEffect> = _sideEffect.asSharedFlow()

    init {
        scope.launch {
            getDocumentsUseCase().collect { docs ->
                _state.value = _state.value.copy(documents = docs)
            }
        }
    }

    override fun sendIntent(intent: MainIntent) {
        when (intent) {
            is MainIntent.SyncDocuments -> syncDocuments()
        }
    }

    private fun syncDocuments() {
        scope.launch {
            _state.value = _state.value.copy(isLoading = true)
            try {
                syncDocumentsUseCase()
            } catch (e: Exception) {
                _sideEffect.emit(MainSideEffect.ShowError(e.message ?: "Unknown error"))
            } finally {
                _state.value = _state.value.copy(isLoading = false)
            }
        }
    }
}
""")

# 12. presentation/di/Koin.kt
write_file(f'{base_pkg}/presentation/di/Koin.kt', """package com.ppizil.raven.common.presentation.di

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
    
    // ViewModels
    factory { PairingViewModel(get()) }
    factory { MainViewModel(get(), get()) }
}
""")

# Move QrScanner
os.makedirs(f'{base_pkg}/framework/qr', exist_ok=True)
if os.path.exists(f'{base_pkg}/qr/QrScanner.kt'):
    shutil.move(f'{base_pkg}/qr/QrScanner.kt', f'{base_pkg}/framework/qr/QrScanner.kt')
if os.path.exists(f'{base_pkg}/qr/FakeQrScanner.kt'):
    shutil.move(f'{base_pkg}/qr/FakeQrScanner.kt', f'{base_pkg}/framework/qr/FakeQrScanner.kt')

# Update FakeQrScanner package
if os.path.exists(f'{base_pkg}/framework/qr/FakeQrScanner.kt'):
    with open(f'{base_pkg}/framework/qr/FakeQrScanner.kt', 'r') as f:
        content = f.read()
    content = content.replace('package com.ppizil.raven.common.qr', 'package com.ppizil.raven.common.framework.qr')
    with open(f'{base_pkg}/framework/qr/FakeQrScanner.kt', 'w') as f:
        f.write(content)

if os.path.exists(f'{base_pkg}/framework/qr/QrScanner.kt'):
    with open(f'{base_pkg}/framework/qr/QrScanner.kt', 'r') as f:
        content = f.read()
    content = content.replace('package com.ppizil.raven.common.qr', 'package com.ppizil.raven.common.framework.qr')
    with open(f'{base_pkg}/framework/qr/QrScanner.kt', 'w') as f:
        f.write(content)

# Remove old directories
shutil.rmtree(f'{base_pkg}/repository', ignore_errors=True)
shutil.rmtree(f'{base_pkg}/qr', ignore_errors=True)
if os.path.exists(f'{base_pkg}/di/Koin.kt'):
    os.remove(f'{base_pkg}/di/Koin.kt')
shutil.rmtree(f'{base_pkg}/di', ignore_errors=True)
if os.path.exists(f'{base_pkg}/ui/MainViewModel.kt'):
    os.remove(f'{base_pkg}/ui/MainViewModel.kt')
if os.path.exists(f'{base_pkg}/ui/PairingViewModel.kt'):
    os.remove(f'{base_pkg}/ui/PairingViewModel.kt')

# Update imports in UI
ui_files = [
    'mobile/shared/src/commonMain/kotlin/App.kt',
    f'{base_pkg}/ui/SlidingPanelLayout.kt'
]
for f_path in ui_files:
    if os.path.exists(f_path):
        with open(f_path, 'r') as f:
            c = f.read()
        c = c.replace('com.ppizil.raven.common.db.Document', 'com.ppizil.raven.common.domain.model.Document')
        c = c.replace('com.ppizil.raven.common.di.initKoin', 'com.ppizil.raven.common.presentation.di.initKoin')
        with open(f_path, 'w') as f:
            f.write(c)

# Fix Main.android.kt
android_main = 'mobile/shared/src/androidMain/kotlin/main.android.kt'
if os.path.exists(android_main):
    with open(android_main, 'r') as f:
        c = f.read()
    c = c.replace('com.ppizil.raven.common.di.initKoin', 'com.ppizil.raven.common.presentation.di.initKoin')
    with open(android_main, 'w') as f:
        f.write(c)

# Fix tests
test_files = [
    'mobile/shared/src/androidUnitTest/kotlin/com/ppizil/raven/common/ui/PairingViewModelTest.kt',
    'mobile/shared/src/androidUnitTest/kotlin/com/ppizil/raven/common/repository/DocumentRepositoryTest.kt'
]

pairing_test = """package com.ppizil.raven.common.ui

import com.ppizil.raven.common.presentation.viewmodel.PairingViewModel
import com.ppizil.raven.common.presentation.viewmodel.PairingState
import com.ppizil.raven.common.presentation.viewmodel.PairingIntent
import com.ppizil.raven.common.domain.usecase.PairDeviceUseCase
import com.ppizil.raven.common.framework.qr.FakeQrScanner
import com.ppizil.raven.common.data.repository.SettingsRepositoryImpl
import com.ppizil.raven.common.db.RavenDatabase
import app.cash.sqldelight.driver.jdbc.sqlite.JdbcSqliteDriver
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.advanceUntilIdle
import org.junit.After
import org.junit.Before
import org.junit.Test
import kotlin.test.assertEquals

class PairingViewModelTest {

    private lateinit var viewModel: PairingViewModel
    private val testDispatcher = StandardTestDispatcher()

    @Before
    fun setup() {
        Dispatchers.setMain(testDispatcher)
        val driver = JdbcSqliteDriver(JdbcSqliteDriver.IN_MEMORY)
        RavenDatabase.Schema.create(driver)
        val database = RavenDatabase(driver)
        val settingsRepository = SettingsRepositoryImpl(database)
        val qrScanner = FakeQrScanner()
        val pairDeviceUseCase = PairDeviceUseCase(qrScanner, settingsRepository)
        viewModel = PairingViewModel(pairDeviceUseCase)
    }

    @After
    fun tearDown() {
        Dispatchers.resetMain()
    }

    @Test
    fun testStartPairingSuccess() = runTest(testDispatcher) {
        assertEquals(PairingState.Idle, viewModel.state.value)
        viewModel.sendIntent(PairingIntent.StartPairing)
        advanceUntilIdle()
        assertEquals(PairingState.Success, viewModel.state.value)
    }
}
"""
if os.path.exists(test_files[0]):
    with open(test_files[0], 'w') as f:
        f.write(pairing_test)

doc_test = """package com.ppizil.raven.common.repository

import com.ppizil.raven.common.data.repository.DocumentRepositoryImpl
import com.ppizil.raven.common.data.repository.SettingsRepositoryImpl
import com.ppizil.raven.common.db.RavenDatabase
import app.cash.sqldelight.driver.jdbc.sqlite.JdbcSqliteDriver
import io.ktor.client.*
import io.ktor.client.engine.mock.*
import io.ktor.client.plugins.contentnegotiation.*
import io.ktor.http.*
import io.ktor.serialization.kotlinx.json.*
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.test.runTest
import org.junit.Before
import org.junit.Test
import kotlin.test.assertEquals

class DocumentRepositoryTest {
    private lateinit var repository: DocumentRepositoryImpl
    private lateinit var settingsRepository: SettingsRepositoryImpl
    private lateinit var database: RavenDatabase

    @Before
    fun setup() {
        val driver = JdbcSqliteDriver(JdbcSqliteDriver.IN_MEMORY)
        RavenDatabase.Schema.create(driver)
        database = RavenDatabase(driver)
        settingsRepository = SettingsRepositoryImpl(database)
        settingsRepository.saveEndpoint("http://localhost:8080")
        settingsRepository.saveApiKey("test-key")

        val mockEngine = MockEngine { request ->
            respond(
                content = \"\"\"[{"id": "doc1", "title": "Test", "content": "Content"}]\"\"\",
                status = HttpStatusCode.OK,
                headers = headersOf(HttpHeaders.ContentType, "application/json")
            )
        }
        val httpClient = HttpClient(mockEngine) {
            install(ContentNegotiation) {
                json()
            }
        }
        repository = DocumentRepositoryImpl(httpClient, database, settingsRepository)
    }

    @Test
    fun testSyncAllDocuments() = runTest {
        repository.syncAllDocuments()
        val docs = repository.getAllDocuments().first()
        assertEquals(1, docs.size)
        assertEquals("doc1", docs[0].id)
    }
}
"""
if os.path.exists(test_files[1]):
    with open(test_files[1], 'w') as f:
        f.write(doc_test)

print("Clean Architecture Migration Script Done!")
