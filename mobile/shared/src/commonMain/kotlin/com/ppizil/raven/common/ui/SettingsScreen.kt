package com.ppizil.raven.common.ui

import androidx.compose.foundation.layout.*
import androidx.compose.material.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.input.VisualTransformation
import androidx.compose.ui.unit.dp
import androidx.compose.ui.graphics.Color
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
    var validationError by remember { mutableStateOf<String?>(null) }

    fun validateAndFormatEndpoint(input: String): String? {
        val trimmed = input.trim().trimEnd('/')
        if (trimmed.isBlank()) return null
        var formatted = trimmed
        if (!formatted.startsWith("http://") && !formatted.startsWith("https://")) {
            formatted = "http://$formatted"
        }
        val withoutScheme = formatted.substringAfter("://")
        if (withoutScheme.isBlank() || withoutScheme.contains(" ")) return null
        return formatted
    }

    Column(modifier = modifier.fillMaxSize().padding(16.dp)) {
        Text("외관", style = MaterialTheme.typography.h6)
        Spacer(modifier = Modifier.height(8.dp))
        Row(
            verticalAlignment = Alignment.CenterVertically,
            modifier = Modifier.fillMaxWidth()
        ) {
            Text("다크 모드", modifier = Modifier.weight(1f))
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
        
        Text("연결 설정", style = MaterialTheme.typography.h6)
        Spacer(modifier = Modifier.height(16.dp))
        
        OutlinedTextField(
            value = endpoint,
            onValueChange = { endpoint = it; isSaved = false },
            label = { Text("서버 주소") },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true
        )
        Spacer(modifier = Modifier.height(16.dp))
        
        OutlinedTextField(
            value = apiKey,
            onValueChange = { apiKey = it; isSaved = false },
            label = { Text("API 키") },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true,
            visualTransformation = if (showApiKey) VisualTransformation.None else PasswordVisualTransformation(),
            trailingIcon = {
                TextButton(onClick = { showApiKey = !showApiKey }) {
                    Text(if (showApiKey) "숨기기" else "보기")
                }
            }
        )
        
        Spacer(modifier = Modifier.height(16.dp))
        Button(
            onClick = {
                val formatted = validateAndFormatEndpoint(endpoint)
                if (endpoint.isNotBlank() && formatted == null) {
                    validationError = "잘못된 주소 형식입니다. 예: http://100.x.y.z:8765"
                } else {
                    validationError = null
                    settingsRepository.saveEndpoint(formatted ?: "")
                    settingsRepository.saveApiKey(apiKey)
                    isSaved = true
                }
            },
            modifier = Modifier.fillMaxWidth()
        ) {
            Text(if (isSaved) "저장 완료 ✓" else "설정 저장")
        }

        validationError?.let { error ->
            Spacer(modifier = Modifier.height(8.dp))
            Text(
                text = error,
                style = MaterialTheme.typography.caption,
                color = MaterialTheme.colors.error,
            )
        }
        
        Spacer(modifier = Modifier.weight(1f))
        
        OutlinedButton(
            onClick = onLogout,
            modifier = Modifier.fillMaxWidth(),
            colors = ButtonDefaults.outlinedButtonColors(contentColor = MaterialTheme.colors.error)
        ) {
            Text("연결 해제")
        }
    }
}
