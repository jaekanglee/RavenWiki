import androidx.compose.foundation.layout.*
import androidx.compose.material.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.ppizil.raven.common.domain.repository.SettingsRepository
import com.ppizil.raven.common.presentation.viewmodel.MainViewModel
import com.ppizil.raven.common.presentation.viewmodel.MainIntent
import com.ppizil.raven.common.presentation.viewmodel.MainSideEffect
import com.ppizil.raven.common.presentation.viewmodel.ConnectionStatus
import com.ppizil.raven.common.ui.PairingScreen
import com.ppizil.raven.common.ui.DocumentListScreen
import com.ppizil.raven.common.ui.DocumentDetailScreen
import com.ppizil.raven.common.ui.DocumentEditScreen
import com.ppizil.raven.common.ui.SearchScreen
import com.ppizil.raven.common.ui.SettingsScreen
import com.ppizil.raven.common.ui.GraphScreen
import com.ppizil.raven.common.ui.theme.RavenTheme
import androidx.compose.material.ExperimentalMaterialApi
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.Search
import androidx.compose.material.icons.filled.Share
import androidx.compose.material.icons.filled.Settings
import androidx.compose.ui.text.style.TextOverflow
import com.ppizil.raven.common.domain.model.Document
import androidx.compose.material.pullrefresh.PullRefreshIndicator
import androidx.compose.material.pullrefresh.pullRefresh
import androidx.compose.material.pullrefresh.rememberPullRefreshState
import kotlinx.coroutines.flow.collectLatest
import org.koin.compose.koinInject

enum class BottomTab {
    Home, Search, Graph, Settings
}

@OptIn(ExperimentalMaterialApi::class)
@Composable
fun App() {
    val settingsRepository: SettingsRepository = koinInject()
    var isPaired by remember { mutableStateOf(settingsRepository.getEndpoint()?.isNotBlank() == true) }
    var isDarkTheme by remember { mutableStateOf(settingsRepository.isDarkMode()) }

    RavenTheme(darkTheme = isDarkTheme) {
        if (!isPaired) {
            PairingScreen(
                onNavigateToMain = { isPaired = true }
            )
        } else {
            val viewModel: MainViewModel = koinInject()
            val state by viewModel.state.collectAsState()
            val snackbarHostState = remember { SnackbarHostState() }
            
            var selectedDocument by remember { mutableStateOf<Document?>(null) }
            var isEditing by remember { mutableStateOf(false) }
            var currentTab by remember { mutableStateOf(BottomTab.Home) }

            LaunchedEffect(viewModel.sideEffect) {
                viewModel.sideEffect.collectLatest { effect ->
                    when (effect) {
                        is MainSideEffect.ShowError -> {
                            snackbarHostState.showSnackbar(effect.message)
                        }
                    }
                }
            }

            LaunchedEffect(Unit) {
                viewModel.sendIntent(MainIntent.SyncDocuments)
            }

            val pullRefreshState = rememberPullRefreshState(
                refreshing = state.connectionStatus == ConnectionStatus.Connecting,
                onRefresh = { viewModel.sendIntent(MainIntent.SyncDocuments) }
            )

            Scaffold(
                snackbarHost = { SnackbarHost(snackbarHostState) },
                topBar = {
                    TopAppBar(
                        title = { 
                            Text(
                                text = if (isEditing && selectedDocument == null) "New Document"
                                       else if (isEditing) "Edit Document"
                                       else selectedDocument?.title ?: "Raven",
                                maxLines = 1,
                                overflow = TextOverflow.Ellipsis
                            ) 
                        },
                        backgroundColor = MaterialTheme.colors.surface,
                        elevation = 0.dp,
                        navigationIcon = if (selectedDocument != null || isEditing) {
                            {
                                IconButton(onClick = { 
                                    if (isEditing) {
                                        isEditing = false
                                    } else {
                                        selectedDocument = null 
                                    }
                                }) {
                                    Icon(
                                        imageVector = Icons.Default.ArrowBack,
                                        contentDescription = "Back"
                                    )
                                }
                            }
                        } else null,
                        actions = {
                            if (selectedDocument != null && !isEditing) {
                                IconButton(onClick = { 
                                    viewModel.sendIntent(MainIntent.DeleteDocument(selectedDocument!!.id))
                                    selectedDocument = null 
                                }) {
                                    Icon(
                                        imageVector = Icons.Default.Delete,
                                        contentDescription = "Delete",
                                        tint = MaterialTheme.colors.error
                                    )
                                }
                                IconButton(onClick = { isEditing = true }) {
                                    Icon(
                                        imageVector = Icons.Default.Edit,
                                        contentDescription = "Edit"
                                    )
                                }
                            }
                        }
                    )
                },
                floatingActionButton = {
                    if (currentTab == BottomTab.Home && selectedDocument == null && !isEditing && state.connectionStatus == ConnectionStatus.Success) {
                        FloatingActionButton(onClick = {
                            selectedDocument = null
                            isEditing = true
                        }) {
                            Icon(Icons.Default.Add, contentDescription = "New Document")
                        }
                    }
                },
                bottomBar = {
                    if (state.connectionStatus == ConnectionStatus.Success && selectedDocument == null && !isEditing) {
                        BottomNavigation(
                            backgroundColor = MaterialTheme.colors.surface,
                            elevation = 8.dp
                        ) {
                            BottomNavigationItem(
                                icon = { Icon(Icons.Default.Home, contentDescription = "Home") },
                                label = { Text("Home", maxLines = 1) },
                                selected = currentTab == BottomTab.Home,
                                onClick = { currentTab = BottomTab.Home },
                                selectedContentColor = MaterialTheme.colors.primary,
                                unselectedContentColor = MaterialTheme.colors.onSurface.copy(alpha = 0.6f)
                            )
                            BottomNavigationItem(
                                icon = { Icon(Icons.Default.Search, contentDescription = "Search") },
                                label = { Text("Search", maxLines = 1) },
                                selected = currentTab == BottomTab.Search,
                                onClick = { currentTab = BottomTab.Search },
                                selectedContentColor = MaterialTheme.colors.primary,
                                unselectedContentColor = MaterialTheme.colors.onSurface.copy(alpha = 0.6f)
                            )
                            BottomNavigationItem(
                                icon = { Icon(Icons.Default.Share, contentDescription = "Graph") },
                                label = { Text("Graph", maxLines = 1) },
                                selected = currentTab == BottomTab.Graph,
                                onClick = { currentTab = BottomTab.Graph },
                                selectedContentColor = MaterialTheme.colors.primary,
                                unselectedContentColor = MaterialTheme.colors.onSurface.copy(alpha = 0.6f)
                            )
                            BottomNavigationItem(
                                icon = { Icon(Icons.Default.Settings, contentDescription = "Settings") },
                                label = { Text("Settings", maxLines = 1) },
                                selected = currentTab == BottomTab.Settings,
                                onClick = { currentTab = BottomTab.Settings },
                                selectedContentColor = MaterialTheme.colors.primary,
                                unselectedContentColor = MaterialTheme.colors.onSurface.copy(alpha = 0.6f)
                            )
                        }
                    }
                }
            ) { padding ->
                Box(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(padding)
                        .pullRefresh(pullRefreshState)
                ) {
                    when {
                        state.connectionStatus == ConnectionStatus.Connecting && state.documents.isEmpty() -> {
                            Column(
                                modifier = Modifier.align(Alignment.Center),
                                horizontalAlignment = Alignment.CenterHorizontally
                            ) {
                                CircularProgressIndicator()
                                Spacer(modifier = Modifier.height(16.dp))
                                Text("Connecting to server...")
                            }
                        }
                        state.connectionStatus == ConnectionStatus.Error && state.documents.isEmpty() -> {
                            Column(
                                modifier = Modifier.align(Alignment.Center).padding(32.dp),
                                horizontalAlignment = Alignment.CenterHorizontally
                            ) {
                                Text(
                                    text = "Connection Failed",
                                    style = MaterialTheme.typography.h6,
                                    color = MaterialTheme.colors.error
                                )
                                Spacer(modifier = Modifier.height(8.dp))
                                Text(
                                    text = state.errorMessage ?: "Unknown Error",
                                    style = MaterialTheme.typography.body1
                                )
                                Spacer(modifier = Modifier.height(24.dp))
                                Button(onClick = {
                                    settingsRepository.saveEndpoint("")
                                    isPaired = false
                                }) {
                                    Text("Change Connection IP")
                                }
                            }
                        }
                        state.connectionStatus == ConnectionStatus.Success && state.documents.isEmpty() -> {
                            Column(
                                modifier = Modifier.align(Alignment.Center).padding(32.dp),
                                horizontalAlignment = Alignment.CenterHorizontally
                            ) {
                                Text(
                                    text = "Connected Successfully!",
                                    style = MaterialTheme.typography.h6,
                                    color = MaterialTheme.colors.primary
                                )
                                Spacer(modifier = Modifier.height(8.dp))
                                Text(
                                    text = "But there are no documents in this vault.",
                                    style = MaterialTheme.typography.body1
                                )
                                Spacer(modifier = Modifier.height(24.dp))
                                Button(onClick = { viewModel.sendIntent(MainIntent.SyncDocuments) }) {
                                    Text("Refresh")
                                }
                                Spacer(modifier = Modifier.height(8.dp))
                                OutlinedButton(onClick = {
                                    settingsRepository.saveEndpoint("")
                                    isPaired = false
                                }) {
                                    Text("Change Vault IP")
                                }
                            }
                        }
                        else -> {
                            if (isEditing) {
                                DocumentEditScreen(
                                    document = selectedDocument,
                                    onSave = { doc ->
                                        viewModel.sendIntent(MainIntent.SaveDocument(doc))
                                        isEditing = false
                                        selectedDocument = doc
                                    },
                                    modifier = Modifier.fillMaxSize()
                                )
                            } else if (selectedDocument != null) {
                                DocumentDetailScreen(
                                    document = selectedDocument!!,
                                    modifier = Modifier.fillMaxSize()
                                )
                            } else {
                                when (currentTab) {
                                    BottomTab.Home -> {
                                        DocumentListScreen(
                                            documents = state.documents,
                                            onDocumentClick = { selectedDocument = it },
                                            onDeleteClick = { 
                                                viewModel.sendIntent(MainIntent.DeleteDocument(it.id)) 
                                            },
                                            modifier = Modifier.fillMaxSize()
                                        )
                                    }
                                    BottomTab.Search -> {
                                        SearchScreen(
                                            documents = state.documents,
                                            onDocumentClick = { selectedDocument = it },
                                            modifier = Modifier.fillMaxSize()
                                        )
                                    }
                                    BottomTab.Graph -> {
                                        GraphScreen(
                                            documents = state.documents,
                                            onNodeClick = { selectedDocument = it },
                                            modifier = Modifier.fillMaxSize()
                                        )
                                    }
                                    BottomTab.Settings -> {
                                        SettingsScreen(
                                            settingsRepository = settingsRepository,
                                            onLogout = {
                                                settingsRepository.saveEndpoint("")
                                                isPaired = false
                                            },
                                            currentIsDark = isDarkTheme,
                                            onThemeChange = { isDarkTheme = it },
                                            modifier = Modifier.fillMaxSize()
                                        )
                                    }
                                }
                            }
                        }
                    }
                    if (selectedDocument == null && !isEditing) {
                        PullRefreshIndicator(
                            refreshing = state.connectionStatus == ConnectionStatus.Connecting,
                            state = pullRefreshState,
                            modifier = Modifier.align(Alignment.TopCenter)
                        )
                    }
                }
            }
        }
    }
}

expect fun getPlatformName(): String