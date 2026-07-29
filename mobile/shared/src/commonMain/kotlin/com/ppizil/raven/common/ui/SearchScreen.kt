package com.ppizil.raven.common.ui

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Search
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.ppizil.raven.common.domain.model.Document
import kotlinx.coroutines.delay

@Composable
fun SearchScreen(
    documents: List<Document>,
    onDocumentClick: (Document) -> Unit,
    modifier: Modifier = Modifier
) {
    var query by remember { mutableStateOf("") }
    var debouncedQuery by remember { mutableStateOf("") }

    LaunchedEffect(query) {
        delay(220) // 220ms debounce (aligned with desktop)
        debouncedQuery = query
    }

    val searchResults = remember(debouncedQuery, documents) {
        if (debouncedQuery.isBlank()) {
            emptyList()
        } else {
            val lowerQuery = debouncedQuery.lowercase()
            documents.filter {
                it.title.lowercase().contains(lowerQuery) || it.content.lowercase().contains(lowerQuery)
            }
        }
    }

    Column(modifier = modifier.fillMaxSize().padding(16.dp)) {
        OutlinedTextField(
            value = query,
            onValueChange = { query = it },
            modifier = Modifier.fillMaxWidth(),
            label = { Text("Search Documents") },
            leadingIcon = { Icon(Icons.Default.Search, contentDescription = "Search Icon") },
            singleLine = true
        )

        Spacer(modifier = Modifier.height(16.dp))

        if (debouncedQuery.isNotBlank()) {
            if (searchResults.isEmpty()) {
                Text("No results found.", style = MaterialTheme.typography.body1)
            } else {
                LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    items(searchResults) { doc ->
                        Card(
                            modifier = Modifier
                                .fillMaxWidth()
                                .clickable { onDocumentClick(doc) },
                            elevation = 2.dp,
                            backgroundColor = MaterialTheme.colors.surface
                        ) {
                            Column(modifier = Modifier.padding(16.dp)) {
                                Text(
                                    text = doc.title, 
                                    style = MaterialTheme.typography.subtitle1,
                                    color = MaterialTheme.colors.primary
                                )
                                Spacer(modifier = Modifier.height(4.dp))
                                Text(
                                    text = doc.content.take(100) + if (doc.content.length > 100) "..." else "",
                                    style = MaterialTheme.typography.body2,
                                    color = MaterialTheme.colors.onSurface.copy(alpha = 0.7f),
                                    maxLines = 2
                                )
                            }
                        }
                    }
                }
            }
        } else {
            Text(
                "Type to search your vault.", 
                style = MaterialTheme.typography.body2, 
                color = MaterialTheme.colors.onSurface.copy(alpha = 0.6f)
            )
        }
    }
}
