package com.ppizil.raven.common.ui

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.Card
import androidx.compose.material.Icon
import androidx.compose.material.IconButton
import androidx.compose.material.MaterialTheme
import androidx.compose.material.Text
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.KeyboardArrowUp
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.ppizil.raven.common.domain.model.Document

private fun folderOf(slug: String): String = slug.substringBeforeLast('/', "")

@Composable
fun DocumentListScreen(
    documents: List<Document>,
    onDocumentClick: (Document) -> Unit,
    onDeleteClick: (Document) -> Unit,
    modifier: Modifier = Modifier,
) {
    var currentFolder by remember { mutableStateOf("") }

    val subFolders = remember(documents, currentFolder) {
        documents
            .map { folderOf(it.id) }
            .filter { folder -> currentFolder.isEmpty() || folder.startsWith("$currentFolder/") }
            .mapNotNull { folder ->
                val remainder =
                    if (currentFolder.isEmpty()) folder else folder.removePrefix("$currentFolder/")
                remainder.substringBefore('/').takeIf { it.isNotEmpty() }
            }
            .distinct()
            .sorted()
    }
    val currentDocuments = remember(documents, currentFolder) {
        documents.filter { folderOf(it.id) == currentFolder }
    }

    Column(modifier = modifier.fillMaxSize()) {
        Text(
            text = if (currentFolder.isEmpty()) "/" else "/$currentFolder",
            style = MaterialTheme.typography.caption,
            color = MaterialTheme.colors.onSurface.copy(alpha = 0.6f),
            modifier = Modifier.padding(start = 16.dp, top = 12.dp),
        )
        if (currentFolder.isNotEmpty()) {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .clickable { currentFolder = currentFolder.substringBeforeLast('/', "") }
                    .padding(16.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Icon(
                    Icons.Default.KeyboardArrowUp,
                    contentDescription = "상위 폴더",
                    tint = MaterialTheme.colors.primary,
                )
                Spacer(modifier = Modifier.width(12.dp))
                Text("상위 폴더", color = MaterialTheme.colors.primary)
            }
        }

        LazyColumn(
            modifier = Modifier.fillMaxSize(),
            contentPadding = PaddingValues(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            items(subFolders, key = { "folder:$it" }) { folder ->
                Card(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clickable {
                            currentFolder =
                                if (currentFolder.isEmpty()) folder else "$currentFolder/$folder"
                        },
                    elevation = 1.dp,
                ) {
                    Text(
                        text = "$folder/",
                        style = MaterialTheme.typography.subtitle1,
                        color = MaterialTheme.colors.onSurface,
                        modifier = Modifier.padding(16.dp),
                    )
                }
            }

            items(currentDocuments, key = { "doc:${it.id}" }) { document ->
                Card(modifier = Modifier.fillMaxWidth(), elevation = 2.dp) {
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .clickable { onDocumentClick(document) }
                            .padding(16.dp),
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Column(modifier = Modifier.fillMaxWidth(0.85f)) {
                            Text(
                                text = document.title,
                                style = MaterialTheme.typography.subtitle1,
                                color = MaterialTheme.colors.onSurface,
                                maxLines = 2,
                                overflow = TextOverflow.Ellipsis,
                            )
                            Spacer(modifier = Modifier.height(4.dp))
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                document.type?.takeIf { it.isNotBlank() }?.let { type ->
                                    Text(
                                        text = type,
                                        style = MaterialTheme.typography.caption,
                                        color = MaterialTheme.colors.primary,
                                    )
                                    Spacer(modifier = Modifier.width(8.dp))
                                }
                                Text(
                                    text = document.id,
                                    style = MaterialTheme.typography.caption,
                                    color = MaterialTheme.colors.onSurface.copy(alpha = 0.6f),
                                    maxLines = 1,
                                    overflow = TextOverflow.Ellipsis,
                                )
                            }
                        }
                        IconButton(onClick = { onDeleteClick(document) }) {
                            Icon(
                                Icons.Default.Delete,
                                contentDescription = "삭제",
                                tint = MaterialTheme.colors.error,
                            )
                        }
                    }
                }
            }
        }
    }
}
