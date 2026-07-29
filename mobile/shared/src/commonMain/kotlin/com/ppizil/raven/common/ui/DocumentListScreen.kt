package com.ppizil.raven.common.ui

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.Card
import androidx.compose.material.Icon
import androidx.compose.material.IconButton
import androidx.compose.material.MaterialTheme
import androidx.compose.material.Text
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.List
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.ppizil.raven.common.domain.model.Document

@Composable
fun DocumentListScreen(
    documents: List<Document>,
    onDocumentClick: (Document) -> Unit,
    onDeleteClick: (Document) -> Unit,
    modifier: Modifier = Modifier
) {
    var currentPath by remember { mutableStateOf("") }
    
    val (folders, currentDocs) = remember(documents, currentPath) {
        val folders = documents
            .mapNotNull { it.path }
            .filter { if (currentPath.isEmpty()) true else it.startsWith("$currentPath/") }
            .map { 
                val remainder = if (currentPath.isEmpty()) it else it.removePrefix("$currentPath/")
                remainder.substringBefore('/') 
            }
            .filter { it.isNotEmpty() }
            .toSet()
            .toList()
            .sorted()
            
        val currentDocs = documents.filter { (it.path ?: "") == currentPath }
        Pair(folders, currentDocs)
    }

    Column(modifier = modifier.fillMaxSize()) {
        if (currentPath.isNotEmpty()) {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .clickable { 
                        currentPath = if (currentPath.contains("/")) currentPath.substringBeforeLast("/") else "" 
                    }
                    .padding(16.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Icon(Icons.Default.ArrowBack, contentDescription = "Up", tint = MaterialTheme.colors.primary)
                Spacer(modifier = Modifier.width(16.dp))
                Text("Back to parent folder", color = MaterialTheme.colors.primary)
            }
        }
        
        LazyColumn(
            modifier = Modifier.fillMaxSize().weight(1f),
            contentPadding = PaddingValues(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            items(folders) { folderName ->
                Card(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clickable { 
                            currentPath = if (currentPath.isEmpty()) folderName else "$currentPath/$folderName" 
                        },
                    elevation = 2.dp,
                    shape = MaterialTheme.shapes.medium,
                    backgroundColor = MaterialTheme.colors.surface
                ) {
                    Row(
                        modifier = Modifier.padding(16.dp).fillMaxWidth(),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Icon(
                            imageVector = Icons.Default.List,
                            contentDescription = "Folder",
                            tint = MaterialTheme.colors.secondary
                        )
                        Spacer(modifier = Modifier.width(16.dp))
                        Text(
                            text = folderName,
                            style = MaterialTheme.typography.h6,
                            color = MaterialTheme.colors.onSurface
                        )
                    }
                }
            }
            
            items(currentDocs) { doc ->
                Card(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clickable { onDocumentClick(doc) },
                    elevation = 2.dp,
                    shape = MaterialTheme.shapes.medium,
                    backgroundColor = MaterialTheme.colors.surface
                ) {
                    Row(
                        modifier = Modifier.padding(16.dp).fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Column(modifier = Modifier.weight(1f)) {
                            Text(
                                text = doc.title,
                                style = MaterialTheme.typography.h6,
                                color = MaterialTheme.colors.onSurface,
                                maxLines = 1,
                                overflow = TextOverflow.Ellipsis
                            )
                            Spacer(modifier = Modifier.height(8.dp))
                            Text(
                                text = doc.content,
                                style = MaterialTheme.typography.body2,
                                color = MaterialTheme.colors.onSurface.copy(alpha = 0.7f),
                                maxLines = 3,
                                overflow = TextOverflow.Ellipsis
                            )
                        }
                        IconButton(onClick = { onDeleteClick(doc) }) {
                            Icon(
                                imageVector = Icons.Default.Delete,
                                contentDescription = "Delete",
                                tint = MaterialTheme.colors.error
                            )
                        }
                    }
                }
            }
        }
    }
}
