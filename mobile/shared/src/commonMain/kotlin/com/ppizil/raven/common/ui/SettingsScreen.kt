package com.ppizil.raven.common.ui

import androidx.compose.foundation.layout.*
import androidx.compose.material.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.input.VisualTransformation
import androidx.compose.ui.unit.dp
import com.ppizil.raven.common.domain.repository.SettingsRepository

@Composable
fun SettingsScreen(
    settingsRepository: SettingsRepository,
    onLogout: () -> Unit,
    currentIsDark: Boolean,
    onThemeChange: (Boolean) -> Unit,
    modifier: Modifier = Modifier
) {
    var endpoint by remember { mutableStateOf(settingsRepository.getEndpoint() ?: "") }
    var apiKey by remember { mutableStateOf(settingsRepository.getApiKey() ?: "") }
    var showApiKey by remember { mutableStateOf(false) }
    var isSaved by remember { mutableStateOf(false) }

    Column(modifier = modifier.fillMaxSize().padding(16.dp)) {
        Text("App Theme", style = MaterialTheme.typography.h6)
        Spacer(modifier = Modifier.height(8.dp))
        Row(
            verticalAlignment = Alignment.CenterVertically,
            modifier = Modifier.fillMaxWidth()
        ) {
            Text("Dark Mode", modifier = Modifier.weight(1f))
            Switch(
                checked = currentIsDark,
                onCheckedChange = { 
                    settingsRepository.setDarkMode(it)
                    onThemeChange(it) 
                },
                colors = SwitchDefaults.colors(checkedThumbColor = MaterialTheme.colors.primary)
            )
        }
        
        Divider(modifier = Modifier.padding(vertical = 24.dp))
        
        Text("Connection Settings", style = MaterialTheme.typography.h6)
        Spacer(modifier = Modifier.height(16.dp))
        
        OutlinedTextField(
            value = endpoint,
            onValueChange = { endpoint = it; isSaved = false },
            label = { Text("Vault IP / Endpoint") },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true
        )
        Spacer(modifier = Modifier.height(16.dp))
        
        OutlinedTextField(
            value = apiKey,
            onValueChange = { apiKey = it; isSaved = false },
            label = { Text("API Key") },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true,
            visualTransformation = if (showApiKey) VisualTransformation.None else PasswordVisualTransformation(),
            trailingIcon = {
                TextButton(onClick = { showApiKey = !showApiKey }) {
                    Text(if (showApiKey) "Hide" else "Show")
                }
            }
        )
        
        Spacer(modifier = Modifier.height(16.dp))
        Button(
            onClick = {
                settingsRepository.saveEndpoint(endpoint)
                settingsRepository.saveApiKey(apiKey)
                isSaved = true
            },
            modifier = Modifier.fillMaxWidth()
        ) {
            Text(if (isSaved) "Saved ✓" else "Save Settings")
        }
        
        Spacer(modifier = Modifier.weight(1f))
        
        OutlinedButton(
            onClick = onLogout,
            modifier = Modifier.fillMaxWidth(),
            colors = ButtonDefaults.outlinedButtonColors(contentColor = MaterialTheme.colors.error)
        ) {
            Text("Disconnect Vault")
        }
    }
}
