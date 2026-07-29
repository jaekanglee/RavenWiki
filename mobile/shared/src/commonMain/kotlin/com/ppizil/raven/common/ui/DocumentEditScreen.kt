package com.ppizil.raven.common.ui

import androidx.compose.foundation.layout.*
import androidx.compose.material.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.ppizil.raven.common.domain.model.Document

@Composable
fun DocumentEditScreen(
    document: Document? = null,
    onSave: (Document) -> Unit,
    modifier: Modifier = Modifier
) {
    var title by remember { mutableStateOf(document?.title ?: "") }
    var content by remember { mutableStateOf(document?.content ?: "") }

    Column(
        modifier = modifier
            .fillMaxSize()
            .padding(16.dp)
    ) {
        OutlinedTextField(
            value = title,
            onValueChange = { title = it },
            label = { Text("Title") },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true
        )
        Spacer(modifier = Modifier.height(16.dp))
        OutlinedTextField(
            value = content,
            onValueChange = { content = it },
            label = { Text("Content") },
            modifier = Modifier.fillMaxWidth().weight(1f)
        )
        Spacer(modifier = Modifier.height(16.dp))
        Button(
            onClick = {
                val newDoc = document?.copy(
                    title = title,
                    content = content,
                    lastUpdated = io.ktor.util.date.getTimeMillis()
                ) ?: Document(
                    id = "doc_${kotlin.random.Random.nextInt(100000)}",
                    title = title,
                    content = content,
                    path = null,
                    isFavorite = false,
                    lastUpdated = io.ktor.util.date.getTimeMillis()
                )
                onSave(newDoc)
            },
            modifier = Modifier.fillMaxWidth().height(48.dp),
            enabled = title.isNotBlank() && content.isNotBlank()
        ) {
            Text("Save")
        }
    }
}
