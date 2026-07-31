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
import androidx.compose.material.icons.filled.Hub
import androidx.compose.material.icons.filled.Favorite
import androidx.compose.material.icons.filled.FavoriteBorder
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
import androidx.compose.material.AlertDialog
import androidx.compose.material.TextButton
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.background
import androidx.compose.ui.draw.clip
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
import com.ppizil.raven.common.ui.PlatformBackHandler
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
        var deleteTarget by remember { mutableStateOf<String?>(null) }
        var previousTab by remember { mutableStateOf<BottomTab?>(null) }
        var showDiscardDialog by remember { mutableStateOf(false) }
        var editHasChanges by remember { mutableStateOf(false) }

        val selectedDocument = state.documents.firstOrNull { it.id == selectedId }
        val activeVault = state.selectedVault

        PlatformBackHandler(enabled = !browsingVaults) {
            when {
                isCreating || isEditing -> {
                    if (editHasChanges) showDiscardDialog = true
                    else {
                        if (isCreating) isCreating = false
                        if (isEditing) isEditing = false
                        editHasChanges = false
                    }
                }
                selectedId != null -> {
                    selectedId = null
                    if (previousTab != null) {
                        currentTab = previousTab!!
                        previousTab = null
                    }
                }
                else -> browsingVaults = true
            }
        }

        LaunchedEffect(viewModel.sideEffect) {
            viewModel.sideEffect.collectLatest { effect ->
                when (effect) {
                    is MainSideEffect.ShowError -> snackbarHostState.showSnackbar(effect.message)
                    is MainSideEffect.ShowNotice -> snackbarHostState.showSnackbar(effect.message)
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
        val pullRefreshEnabled = browsingVaults || (showChrome && currentTab == BottomTab.Home)

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
                                else -> {
                                    val count = state.documents.size
                                    if (count > 0) "${activeVault ?: "Raven"} ($count)"
                                    else activeVault ?: "Raven"
                                }
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
                                    isCreating || isEditing -> {
                                        if (editHasChanges) {
                                            showDiscardDialog = true
                                        } else {
                                            if (isCreating) isCreating = false
                                            if (isEditing) isEditing = false
                                            editHasChanges = false
                                        }
                                    }
                                    selectedId != null -> {
                                        selectedId = null
                                        if (previousTab != null) {
                                            currentTab = previousTab!!
                                            previousTab = null
                                        }
                                    }
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
                        if (!browsingVaults && !isEditing && !isCreating && selectedDocument == null) {
                            val statusColor = when (state.connectionStatus) {
                                ConnectionStatus.Success -> androidx.compose.ui.graphics.Color(0xFF4CAF50)
                                ConnectionStatus.Connecting -> androidx.compose.ui.graphics.Color(0xFFFFC107)
                                ConnectionStatus.Error -> androidx.compose.ui.graphics.Color(0xFFF44336)
                                ConnectionStatus.Idle -> MaterialTheme.colors.onSurface.copy(alpha = 0.3f)
                            }
                            if (state.pendingWriteCount > 0) {
                                Text(
                                    text = "↑${state.pendingWriteCount}",
                                    style = MaterialTheme.typography.caption,
                                    color = androidx.compose.ui.graphics.Color(0xFFFFC107),
                                    modifier = Modifier.padding(end = 4.dp),
                                )
                            }
                            Box(
                                modifier = Modifier
                                    .padding(end = 12.dp)
                                    .size(8.dp)
                                    .clip(CircleShape)
                                    .background(statusColor),
                            )
                        }
                        if (selectedDocument != null && !isEditing && !isCreating) {
                            IconButton(onClick = {
                                viewModel.sendIntent(MainIntent.ToggleFavorite(selectedDocument.id))
                            }) {
                                Icon(
                                    if (selectedDocument.isFavorite) Icons.Default.Favorite
                                    else Icons.Default.FavoriteBorder,
                                    contentDescription = "즐겨찾기",
                                    tint = if (selectedDocument.isFavorite) MaterialTheme.colors.error
                                    else MaterialTheme.colors.onSurface.copy(alpha = 0.6f),
                                )
                            }
                            IconButton(onClick = { deleteTarget = selectedDocument.id }) {
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
                                            BottomTab.Graph -> Icons.Default.Hub
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
                    .pullRefresh(pullRefreshState, enabled = pullRefreshEnabled),
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
                            editHasChanges = false
                            selectedId = document.id
                        },
                        onHasChangesUpdate = { editHasChanges = it },
                        modifier = Modifier.fillMaxSize(),
                    )

                    isEditing && selectedDocument != null -> DocumentEditScreen(
                        vault = selectedDocument.vault,
                        document = selectedDocument,
                        onSave = { document ->
                            viewModel.sendIntent(MainIntent.SaveDocument(document))
                            isEditing = false
                            editHasChanges = false
                        },
                        onHasChangesUpdate = { editHasChanges = it },
                        modifier = Modifier.fillMaxSize(),
                    )

                    selectedDocument != null -> {
                        if (selectedDocument.content.isBlank() && state.isLoadingDocument) {
                            Loading("문서를 불러오는 중…", Modifier.align(Alignment.Center))
                        } else {
                            DocumentDetailScreen(
                                document = selectedDocument,
                                onWikilinkClick = { target ->
                                    val slug = target.lowercase().replace(Regex("[^\\p{L}\\p{N}]+"), "-").trim('-')
                                    selectedId = slug
                                    viewModel.sendIntent(MainIntent.OpenDocument(slug))
                                },
                                modifier = Modifier.fillMaxSize(),
                            )
                        }
                    }

                    selectedId != null && selectedDocument == null && state.isLoadingDocument ->
                        Loading("문서를 불러오는 중…", Modifier.align(Alignment.Center))

                    selectedId != null && selectedDocument == null && !state.isLoadingDocument &&
                        state.connectionStatus == ConnectionStatus.Error ->
                        Column(
                            modifier = Modifier.align(Alignment.Center).padding(32.dp),
                            horizontalAlignment = Alignment.CenterHorizontally,
                            verticalArrangement = Arrangement.spacedBy(12.dp),
                        ) {
                            Text(
                                text = state.errorMessage ?: "문서를 불러오지 못했습니다.",
                                style = MaterialTheme.typography.body2,
                            )
                            Button(onClick = {
                                viewModel.sendIntent(MainIntent.OpenDocument(selectedId!!))
                            }) { Text("다시 시도") }
                            OutlinedButton(onClick = {
                                selectedId = null
                                if (previousTab != null) {
                                    currentTab = previousTab!!
                                    previousTab = null
                                }
                            }) { Text("돌아가기") }
                        }

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
                        BottomTab.Home -> {
                            if (state.documents.isEmpty() &&
                                state.connectionStatus == ConnectionStatus.Success
                            ) {
                                EmptyVault(
                                    onCreateClick = { isCreating = true },
                                    modifier = Modifier.align(Alignment.Center),
                                )
                            } else {
                                DocumentListScreen(
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
                            }
                        }

                        BottomTab.Search -> SearchScreen(
                            query = state.searchQuery,
                            results = state.searchResults,
                            isSearching = state.isSearching,
                            errorMessage = state.searchError,
                            onQueryChange = { viewModel.sendIntent(MainIntent.Search(it)) },
                            onHitClick = { hit ->
                                previousTab = BottomTab.Search
                                selectedId = hit.slug
                                viewModel.sendIntent(MainIntent.OpenDocument(hit.slug))
                            },
                            modifier = Modifier.fillMaxSize(),
                        )

                        BottomTab.Graph -> GraphScreen(
                            documents = state.documents,
                            onNodeClick = { document ->
                                previousTab = BottomTab.Graph
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

        // 삭제 확인 다이얼로그
        deleteTarget?.let { targetId ->
            AlertDialog(
                onDismissRequest = { deleteTarget = null },
                title = { Text("문서 삭제") },
                text = { Text("이 문서를 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.") },
                confirmButton = {
                    TextButton(onClick = {
                        viewModel.sendIntent(MainIntent.DeleteDocument(targetId))
                        deleteTarget = null
                        if (selectedId == targetId) selectedId = null
                    }) {
                        Text("삭제", color = MaterialTheme.colors.error)
                    }
                },
                dismissButton = {
                    TextButton(onClick = { deleteTarget = null }) {
                        Text("취소")
                    }
                },
            )
        }

        if (showDiscardDialog) {
            AlertDialog(
                onDismissRequest = { showDiscardDialog = false },
                title = { Text("편집 취소") },
                text = { Text("저장하지 않은 변경사항이 있습니다. 나가시겠습니까?") },
                confirmButton = {
                    TextButton(onClick = {
                        showDiscardDialog = false
                        editHasChanges = false
                        if (isCreating) isCreating = false
                        if (isEditing) isEditing = false
                    }) {
                        Text("나가기")
                    }
                },
                dismissButton = {
                    TextButton(onClick = { showDiscardDialog = false }) {
                        Text("계속 편집")
                    }
                },
            )
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

@Composable
private fun EmptyVault(
    onCreateClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Column(
        modifier = modifier.padding(32.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text(
            text = "문서가 없습니다",
            style = MaterialTheme.typography.h6,
            color = MaterialTheme.colors.onSurface.copy(alpha = 0.6f),
        )
        Text(
            text = "새 문서를 만들어 보세요.",
            style = MaterialTheme.typography.body2,
            color = MaterialTheme.colors.onSurface.copy(alpha = 0.4f),
        )
        Spacer(modifier = Modifier.height(8.dp))
        Button(onClick = onCreateClick) { Text("새 문서 만들기") }
    }
}

expect fun getPlatformName(): String
