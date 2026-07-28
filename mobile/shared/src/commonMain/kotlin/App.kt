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
import com.ppizil.raven.common.ui.SlidingPanelLayout
import com.ppizil.raven.common.ui.theme.RavenTheme
import kotlinx.coroutines.flow.collectLatest
import org.koin.compose.koinInject

@Composable
fun App() {
    val settingsRepository: SettingsRepository = koinInject()
    var isPaired by remember { mutableStateOf(settingsRepository.getEndpoint()?.isNotBlank() == true) }

    RavenTheme {
        if (!isPaired) {
            PairingScreen(
                onNavigateToMain = { isPaired = true }
            )
        } else {
            val viewModel: MainViewModel = koinInject()
            val state by viewModel.state.collectAsState()
            val snackbarHostState = remember { SnackbarHostState() }

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

            Scaffold(
                snackbarHost = { SnackbarHost(snackbarHostState) }
            ) { padding ->
                Box(modifier = Modifier.fillMaxSize().padding(padding)) {
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
                            SlidingPanelLayout(
                                documents = state.documents,
                                modifier = Modifier.fillMaxSize()
                            )
                        }
                    }
                }
            }
        }
    }
}

expect fun getPlatformName(): String