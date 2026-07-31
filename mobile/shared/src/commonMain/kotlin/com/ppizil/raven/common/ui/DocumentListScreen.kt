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
import androidx.compose.material.icons.filled.Folder
import androidx.compose.material.icons.filled.Favorite
import androidx.compose.material.icons.filled.FavoriteBorder
import androidx.compose.material.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.material.AlertDialog
import com.ppizil.raven.common.domain.model.Document

private fun folderOf(slug: String): String = slug.substringBeforeLast('/', "")
private fun filenameOf(slug: String): String = slug.substringAfterLast('/')

private fun relativeTime(millis: Long): String {
    if (millis <= 0L) return ""
    val now = io.ktor.util.date.getTimeMillis()
    val diff = (now - millis) / 1000
    return when {
        diff < 60 -> "방금 전"
        diff < 3600 -> "${diff / 60}분 전"
        diff < 86400 -> "${diff / 3600}시간 전"
        diff < 604800 -> "${diff / 86400}일 전"
        else -> "${diff / 604800}주 전"
    }
}

enum class SortMode(val label: String) {
    Recent("최신순"), Title("제목순"), Type("유형순")
}

@Composable
fun DocumentListScreen(
    documents: List<Document>,
    onDocumentClick: (Document) -> Unit,
    onDeleteClick: (Document) -> Unit,
    modifier: Modifier = Modifier,
) {
    var currentFolder by remember { mutableStateOf("") }
    var deleteTarget by remember { mutableStateOf<Document?>(null) }
    var sortMode by remember { mutableStateOf(SortMode.Recent) }
    var favoritesOnly by remember { mutableStateOf(false) }

    val filteredDocuments = remember(documents, favoritesOnly) {
        if (favoritesOnly) documents.filter { it.isFavorite } else documents
    }

    val subFolders = remember(filteredDocuments, currentFolder) {
        filteredDocuments
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
    val currentDocuments = remember(filteredDocuments, currentFolder, sortMode) {
        val filtered = filteredDocuments.filter { folderOf(it.id) == currentFolder }
        when (sortMode) {
            SortMode.Recent -> filtered.sortedByDescending { it.lastUpdated }
            SortMode.Title -> filtered.sortedBy { it.title.lowercase() }
            SortMode.Type -> filtered.sortedBy { it.type ?: "zzz" }
        }
    }

    Column(modifier = modifier.fillMaxSize()) {
        Row(
            modifier = Modifier.fillMaxWidth().padding(start = 16.dp, top = 12.dp, end = 16.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text(
                text = if (currentFolder.isEmpty()) "/" else "/$currentFolder",
                style = MaterialTheme.typography.caption,
                color = MaterialTheme.colors.onSurface.copy(alpha = 0.6f),
                modifier = Modifier.weight(1f),
            )
            IconButton(onClick = { favoritesOnly = !favoritesOnly }) {
                Icon(
                    if (favoritesOnly) Icons.Default.Favorite else Icons.Default.FavoriteBorder,
                    contentDescription = "즐겨찾기 필터",
                    tint = if (favoritesOnly) MaterialTheme.colors.error
                    else MaterialTheme.colors.onSurface.copy(alpha = 0.4f),
                    modifier = Modifier.size(20.dp),
                )
            }
            Row {
                SortMode.entries.forEach { mode ->
                    TextButton(
                        onClick = { sortMode = mode },
                    ) {
                        Text(
                            text = mode.label,
                            style = MaterialTheme.typography.caption,
                            color = if (sortMode == mode) MaterialTheme.colors.primary
                            else MaterialTheme.colors.onSurface.copy(alpha = 0.4f),
                        )
                    }
                }
            }
        }
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
                    Row(
                        modifier = Modifier.padding(16.dp),
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Icon(
                            Icons.Default.Folder,
                            contentDescription = "폴더",
                            tint = MaterialTheme.colors.primary.copy(alpha = 0.7f),
                        )
                        Spacer(modifier = Modifier.width(12.dp))
                        Text(
                            text = folder,
                            style = MaterialTheme.typography.subtitle1,
                            color = MaterialTheme.colors.onSurface,
                        )
                    }
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
                                val time = relativeTime(document.lastUpdated)
                                if (time.isNotEmpty()) {
                                    Text(
                                        text = time,
                                        style = MaterialTheme.typography.caption,
                                        color = MaterialTheme.colors.onSurface.copy(alpha = 0.5f),
                                    )
                                    Spacer(modifier = Modifier.width(8.dp))
                                }
                                Text(
                                    text = filenameOf(document.id),
                                    style = MaterialTheme.typography.caption,
                                    color = MaterialTheme.colors.onSurface.copy(alpha = 0.4f),
                                    maxLines = 1,
                                    overflow = TextOverflow.Ellipsis,
                                )
                            }
                        }
                        IconButton(onClick = { deleteTarget = document }) {
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

    // 삭제 확인 다이얼로그
    deleteTarget?.let { doc ->
        AlertDialog(
            onDismissRequest = { deleteTarget = null },
            title = { Text("문서 삭제") },
            text = { Text("'${doc.title}'을(를) 삭제하시겠습니까?") },
            confirmButton = {
                TextButton(onClick = {
                    onDeleteClick(doc)
                    deleteTarget = null
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
}
