package com.ppizil.raven.common.ui

import androidx.compose.foundation.layout.*
import androidx.compose.material.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.ui.unit.dp
import com.ppizil.raven.common.presentation.viewmodel.PairingIntent
import com.ppizil.raven.common.presentation.viewmodel.PairingSideEffect
import com.ppizil.raven.common.presentation.viewmodel.PairingState
import com.ppizil.raven.common.presentation.viewmodel.PairingViewModel
import kotlinx.coroutines.flow.collectLatest
import org.koin.compose.koinInject

@Composable
fun PairingScreen(
    onNavigateToMain: () -> Unit
) {
    val viewModel: PairingViewModel = koinInject()
    val state by viewModel.state.collectAsState()
    
    var manualEndpoint by remember { mutableStateOf("") }
    val snackbarHostState = remember { SnackbarHostState() }

    LaunchedEffect(viewModel.sideEffect) {
        viewModel.sideEffect.collectLatest { effect ->
            when (effect) {
                is PairingSideEffect.NavigateToMain -> onNavigateToMain()
            }
        }
    }

    Scaffold(
        snackbarHost = { SnackbarHost(snackbarHostState) }
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .windowInsetsPadding(WindowInsets.systemBars)
                .imePadding()
                .padding(24.dp),
            verticalArrangement = Arrangement.Center,
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Text(
                text = "Connect to Raven",
                style = MaterialTheme.typography.h4,
                color = MaterialTheme.colors.onSurface
            )
            
            Spacer(modifier = Modifier.height(32.dp))

            OutlinedTextField(
                value = manualEndpoint,
                onValueChange = { manualEndpoint = it },
                label = { Text("Tailscale IP / Endpoint") },
                modifier = Modifier.fillMaxWidth(),
                placeholder = { Text("e.g. http://100.x.y.z:8765") },
                keyboardOptions = KeyboardOptions(
                    keyboardType = KeyboardType.Uri,
                    imeAction = ImeAction.Done
                ),
                keyboardActions = KeyboardActions(
                    onDone = {
                        if (manualEndpoint.isNotBlank() && state != PairingState.Scanning) {
                            viewModel.sendIntent(PairingIntent.PairManual(manualEndpoint))
                        }
                    }
                ),
                singleLine = true
            )

            Spacer(modifier = Modifier.height(16.dp))

            Button(
                onClick = { viewModel.sendIntent(PairingIntent.PairManual(manualEndpoint)) },
                modifier = Modifier.fillMaxWidth().height(48.dp),
                enabled = manualEndpoint.isNotBlank() && state != PairingState.Scanning
            ) {
                Text("Connect")
            }

            Spacer(modifier = Modifier.height(24.dp))
            
            Text(text = "OR", style = MaterialTheme.typography.subtitle1)
            
            Spacer(modifier = Modifier.height(24.dp))

            OutlinedButton(
                onClick = { viewModel.sendIntent(PairingIntent.StartPairing) },
                modifier = Modifier.fillMaxWidth().height(48.dp),
                enabled = state != PairingState.Scanning
            ) {
                if (state == PairingState.Scanning) {
                    CircularProgressIndicator(modifier = Modifier.size(24.dp))
                } else {
                    Text("Scan QR Code")
                }
            }

            if (state is PairingState.Error) {
                Spacer(modifier = Modifier.height(16.dp))
                Text(
                    text = (state as PairingState.Error).message,
                    color = MaterialTheme.colors.error,
                    style = MaterialTheme.typography.body2
                )
            }
        }
    }
}
