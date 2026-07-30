import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material.BottomNavigation
import androidx.compose.material.BottomNavigationItem
import androidx.compose.material.Button
import androidx.compose.material.CircularProgressIndicator
import androidx.compose.material.ExperimentalMaterialApi
import androidx.compose.material.FloatingActionButton
import androidx.compose.material.Icon
import androidx.compose.material.IconButton
import androidx.compose.material.MaterialTheme
import androidx.compose.material.OutlinedButton
import androidx.compose.material.Scaffold
import androidx.compose.material.SnackbarHost
import androidx.compose.material.SnackbarHostState
import androidx.compose.material.Text
import androidx.compose.material.TopAppBar
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.Search
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.Share
import androidx.compose.material.pullrefresh.PullRefreshIndicator
import androidx.compose.material.pullrefresh.pullRefresh
import androidx.compose.material.pullrefresh.rememberPullRefreshState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.ppizil.raven.common.domain.repository.SettingsRepository
import com.ppizil.raven.common.presentation.viewmodel.ConnectionStatus
import com.ppizil.raven.common.presentation.viewmodel.MainIntent
import com.ppizil.raven.common.presentation.viewmodel.MainSideEffect
import com.ppizil.raven.common.presentation.viewmodel.MainViewModel
import com.ppizil.raven.common.ui.DocumentDetailScreen
import com.ppizil.raven.common.ui.DocumentEditScreen
import com.ppizil.raven.common.ui.DocumentListScreen
import com.ppizil.raven.common.ui.GraphScreen
import com.ppizil.raven.common.ui.PairingScreen
import com.ppizil.raven.common.ui.SearchScreen
import com.ppizil.raven.common.ui.SettingsScreen
import com.ppizil.raven.common.ui.VaultListScreen
import com.ppizil.raven.common.ui.theme.RavenTheme
import kotlinx.coroutines.flow.collectLatest
import org.koin.compose.koinInject

enum class BottomTab(val label: String) {
    Home("홈"), Search("검색"), Graph("그래프"), Settings("설정")
}

@OptIn(ExperimentalMaterialApi::class)
@Composable
fun App() {
    val settingsRepository: SettingsRepository = koinInject()
    var isPaired by remember { mutableStateOf(settingsRepository.getEndpoint()?.isNotBlank() == true) }
    var isDarkTheme by remember { mutableStateOf(settingsRepository.isDarkMode()) }

    RavenTheme(darkTheme = isDarkTheme) {
        if (!isPaired) {
            PairingScreen(onNavigateToMain = { isPaired = true })
            return@RavenTheme
        }

        val viewModel: MainViewModel = koinInject()
        val state by viewModel.state.collectAsState()
        val snackbarHostState = remember { SnackbarHostState() }

        var selectedId by remember { mutableStateOf<String?>(null) }
        var isEditing by remember { mutableStateOf(false) }
        var isCreating by remember { mutableStateOf(false) }
        var currentTab by remember { mutableStateOf(BottomTab.Home) }
        var browsingVaults by remember { mutableStateOf(settingsRepository.getVault().isNullOrBlank()) }

        val selectedDocument = state.documents.firstOrNull { it.id == selectedId }
        val activeVault = state.selectedVault

        LaunchedEffect(viewModel.sideEffect) {
            viewModel.sideEffect.collectLatest { effect ->
                when (effect) {
                    is MainSideEffect.ShowError -> snackbarHostState.showSnackbar(effect.message)
                }
            }
        }

        LaunchedEffect(Unit) {
            viewModel.sendIntent(MainIntent.LoadVaults)
            if (!settingsRepository.getVault().isNullOrBlank()) {
                viewModel.sendIntent(MainIntent.SyncDocuments)
            }
        }

        val pullRefreshState = rememberPullRefreshState(
            refreshing = state.connectionStatus == ConnectionStatus.Connecting,
            onRefresh = {
                if (browsingVaults) {
                    viewModel.sendIntent(MainIntent.LoadVaults)
                } else {
                    viewModel.sendIntent(MainIntent.SyncDocuments)
                }
            },
        )

        val inDocument = selectedId != null || isEditing || isCreating
        val showChrome = !browsingVaults && !inDocument

        Scaffold(
            snackbarHost = { SnackbarHost(snackbarHostState) },
            topBar = {
                TopAppBar(
                    title = {
                        Text(
                            text = when {
                                browsingVaults -> "보관소 선택"
                                isCreating -> "새 문서"
                                isEditing -> "문서 편집"
                                selectedDocument != null -> selectedDocument.title
                                else -> activeVault ?: "Raven"
                            },
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis,
                        )
                    },
                    backgroundColor = MaterialTheme.colors.surface,
                    elevation = 0.dp,
                    navigationIcon = if (!browsingVaults) {
                        {
                            IconButton(onClick = {
                                when {
                                    isCreating -> isCreating = false
                                    isEditing -> isEditing = false
                                    selectedId != null -> selectedId = null
                                    else -> browsingVaults = true
                                }
                            }) {
                                Icon(Icons.Default.ArrowBack, contentDescription = "뒤로")
                            }
                        }
                    } else {
                        null
                    },
                    actions = {
                        if (selectedDocument != null && !isEditing && !isCreating) {
                            IconButton(onClick = {
                                viewModel.sendIntent(MainIntent.DeleteDocument(selectedDocument.id))
                                selectedId = null
                            }) {
                                Icon(
                                    Icons.Default.Delete,
                                    contentDescription = "삭제",
                                    tint = MaterialTheme.colors.error,
                                )
                            }
                            IconButton(onClick = { isEditing = true }) {
                                Icon(Icons.Default.Edit, contentDescription = "편집")
                            }
                        }
                    },
                )
            },
            floatingActionButton = {
                if (showChrome && currentTab == BottomTab.Home && activeVault != null) {
                    FloatingActionButton(onClick = { isCreating = true }) {
                        Icon(Icons.Default.Add, contentDescription = "새 문서")
                    }
                }
            },
            bottomBar = {
                if (showChrome) {
                    BottomNavigation(
                        backgroundColor = MaterialTheme.colors.surface,
                        elevation = 8.dp,
                    ) {
                        BottomTab.entries.forEach { tab ->
                            BottomNavigationItem(
                                icon = {
                                    Icon(
                                        imageVector = when (tab) {
                                            BottomTab.Home -> Icons.Default.Home
                                            BottomTab.Search -> Icons.Default.Search
                                            BottomTab.Graph -> Icons.Default.Share
                                            BottomTab.Settings -> Icons.Default.Settings
                                        },
                                        contentDescription = tab.label,
                                    )
                                },
                                label = { Text(tab.label, maxLines = 1) },
                                selected = currentTab == tab,
                                onClick = { currentTab = tab },
                                selectedContentColor = MaterialTheme.colors.primary,
                                unselectedContentColor = MaterialTheme.colors.onSurface.copy(alpha = 0.6f),
                            )
                        }
                    }
                }
            },
        ) { padding ->
            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(padding)
                    .pullRefresh(pullRefreshState),
            ) {
                when {
                    browsingVaults -> {
                        if (state.vaults.isEmpty() &&
                            state.connectionStatus == ConnectionStatus.Connecting
                        ) {
                            Loading("보관소 목록을 가져오는 중…", Modifier.align(Alignment.Center))
                        } else if (state.vaults.isEmpty()) {
                            ConnectionProblem(
                                message = state.errorMessage ?: "이 PC에서 보관소를 찾지 못했습니다.",
                                onRetry = { viewModel.sendIntent(MainIntent.LoadVaults) },
                                onChangeEndpoint = {
                                    settingsRepository.saveEndpoint("")
                                    isPaired = false
                                },
                                modifier = Modifier.align(Alignment.Center),
                            )
                        } else {
                            VaultListScreen(
                                vaults = state.vaults,
                                selectedVault = activeVault,
                                onVaultClick = { vault ->
                                    selectedId = null
                                    isEditing = false
                                    isCreating = false
                                    currentTab = BottomTab.Home
                                    browsingVaults = false
                                    viewModel.sendIntent(MainIntent.SelectVault(vault.name))
                                },
                                modifier = Modifier.fillMaxSize(),
                            )
                        }
                    }

                    isCreating && activeVault != null -> DocumentEditScreen(
                        vault = activeVault,
                        document = null,
                        onSave = { document ->
                            viewModel.sendIntent(MainIntent.SaveDocument(document))
                            isCreating = false
                            selectedId = document.id
                        },
                        modifier = Modifier.fillMaxSize(),
                    )

                    isEditing && selectedDocument != null -> DocumentEditScreen(
                        vault = selectedDocument.vault,
                        document = selectedDocument,
                        onSave = { document ->
                            viewModel.sendIntent(MainIntent.SaveDocument(document))
                            isEditing = false
                        },
                        modifier = Modifier.fillMaxSize(),
                    )

                    selectedDocument != null -> DocumentDetailScreen(
                        document = selectedDocument,
                        modifier = Modifier.fillMaxSize(),
                    )

                    state.documents.isEmpty() &&
                        state.connectionStatus == ConnectionStatus.Connecting ->
                        Loading("문서를 가져오는 중…", Modifier.align(Alignment.Center))

                    state.documents.isEmpty() &&
                        state.connectionStatus == ConnectionStatus.Error ->
                        ConnectionProblem(
                            message = state.errorMessage ?: "문서를 가져오지 못했습니다.",
                            onRetry = { viewModel.sendIntent(MainIntent.SyncDocuments) },
                            onChangeEndpoint = { browsingVaults = true },
                            changeLabel = "다른 보관소 선택",
                            modifier = Modifier.align(Alignment.Center),
                        )

                    else -> when (currentTab) {
                        BottomTab.Home -> DocumentListScreen(
                            documents = state.documents,
                            onDocumentClick = { document ->
                                selectedId = document.id
                                viewModel.sendIntent(MainIntent.OpenDocument(document.id))
                            },
                            onDeleteClick = { document ->
                                viewModel.sendIntent(MainIntent.DeleteDocument(document.id))
                            },
                            modifier = Modifier.fillMaxSize(),
                        )

                        BottomTab.Search -> SearchScreen(
                            query = state.searchQuery,
                            results = state.searchResults,
                            isSearching = state.isSearching,
                            errorMessage = state.searchError,
                            onQueryChange = { viewModel.sendIntent(MainIntent.Search(it)) },
                            onHitClick = { hit ->
                                selectedId = hit.slug
                                viewModel.sendIntent(MainIntent.OpenDocument(hit.slug))
                            },
                            modifier = Modifier.fillMaxSize(),
                        )

                        BottomTab.Graph -> GraphScreen(
                            documents = state.documents,
                            onNodeClick = { document ->
                                selectedId = document.id
                                viewModel.sendIntent(MainIntent.OpenDocument(document.id))
                            },
                            modifier = Modifier.fillMaxSize(),
                        )

                        BottomTab.Settings -> SettingsScreen(
                            settingsRepository = settingsRepository,
                            onLogout = {
                                settingsRepository.saveEndpoint("")
                                isPaired = false
                            },
                            currentIsDark = isDarkTheme,
                            onThemeChange = { isDarkTheme = it },
                            modifier = Modifier.fillMaxSize(),
                        )
                    }
                }

                if (showChrome) {
                    PullRefreshIndicator(
                        refreshing = state.connectionStatus == ConnectionStatus.Connecting,
                        state = pullRefreshState,
                        modifier = Modifier.align(Alignment.TopCenter),
                    )
                }
            }
        }
    }
}

@Composable
private fun Loading(message: String, modifier: Modifier = Modifier) {
    Column(modifier = modifier, horizontalAlignment = Alignment.CenterHorizontally) {
        CircularProgressIndicator()
        Spacer(modifier = Modifier.height(16.dp))
        Text(message)
    }
}

@Composable
private fun ConnectionProblem(
    message: String,
    onRetry: () -> Unit,
    onChangeEndpoint: () -> Unit,
    modifier: Modifier = Modifier,
    changeLabel: String = "연결 주소 변경",
) {
    Column(
        modifier = modifier.padding(32.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text(
            text = "연결 실패",
            style = MaterialTheme.typography.h6,
            color = MaterialTheme.colors.error,
        )
        Text(text = message, style = MaterialTheme.typography.body2)
        Button(onClick = onRetry) { Text("다시 시도") }
        OutlinedButton(onClick = onChangeEndpoint) { Text(changeLabel) }
    }
}

expect fun getPlatformName(): String
