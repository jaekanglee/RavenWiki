package com.ppizil.raven.common.ui

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material.Button
import androidx.compose.material.OutlinedTextField
import androidx.compose.material.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.ppizil.raven.common.data.repository.canonicalPageSlug
import com.ppizil.raven.common.domain.model.Document

@Composable
fun DocumentEditScreen(
    vault: String,
    document: Document? = null,
    onSave: (Document) -> Unit,
    modifier: Modifier = Modifier,
) {
    var title by remember { mutableStateOf(document?.title ?: "") }
    var content by remember { mutableStateOf(document?.content ?: "") }

    Column(modifier = modifier.fillMaxSize().padding(16.dp)) {
        OutlinedTextField(
            value = title,
            onValueChange = { title = it },
            label = { Text("제목") },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true,
        )
        Spacer(modifier = Modifier.height(16.dp))
        OutlinedTextField(
            value = content,
            onValueChange = { content = it },
            label = { Text("본문") },
            modifier = Modifier.fillMaxWidth().weight(1f),
        )
        Spacer(modifier = Modifier.height(16.dp))
        Button(
            onClick = {
                val now = io.ktor.util.date.getTimeMillis()
                val edited = document?.copy(title = title, content = content, lastUpdated = now)
                    ?: canonicalPageSlug(title, null).let { slug ->
                        Document(
                            vault = vault,
                            id = slug,
                            title = title,
                            content = content,
                            type = null,
                            path = "$slug.md",
                            isFavorite = false,
                            lastUpdated = now,
                        )
                    }
                onSave(edited)
            },
            modifier = Modifier.fillMaxWidth().height(48.dp),
            enabled = title.isNotBlank() && content.isNotBlank(),
        ) {
            Text("저장")
        }
    }
}
