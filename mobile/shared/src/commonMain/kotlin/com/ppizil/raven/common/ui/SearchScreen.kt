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
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.ppizil.raven.common.domain.model.SearchHit
import kotlinx.coroutines.delay

@Composable
fun SearchScreen(
    query: String,
    results: List<SearchHit>,
    isSearching: Boolean,
    errorMessage: String?,
    onQueryChange: (String) -> Unit,
    onHitClick: (SearchHit) -> Unit,
    modifier: Modifier = Modifier
) {
    var draft by remember { mutableStateOf(query) }

    LaunchedEffect(draft) {
        delay(220) // 220ms debounce (aligned with desktop)
        onQueryChange(draft)
    }

    Column(modifier = modifier.fillMaxSize().padding(16.dp)) {
        OutlinedTextField(
            value = draft,
            onValueChange = { draft = it },
            modifier = Modifier.fillMaxWidth(),
            label = { Text("보관소 전체 검색") },
            leadingIcon = { Icon(Icons.Default.Search, contentDescription = "Search Icon") },
            singleLine = true
        )

        Spacer(modifier = Modifier.height(16.dp))

        when {
            draft.isBlank() -> Text(
                "제목뿐 아니라 본문까지 PC의 보관소에서 찾습니다.",
                style = MaterialTheme.typography.body2,
                color = MaterialTheme.colors.onSurface.copy(alpha = 0.6f)
            )

            isSearching && results.isEmpty() -> Row(
                verticalAlignment = androidx.compose.ui.Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                CircularProgressIndicator(modifier = Modifier.size(18.dp), strokeWidth = 2.dp)
                Text("검색 중…", style = MaterialTheme.typography.body2)
            }

            else -> Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                errorMessage?.let { message ->
                    Text(
                        text = message,
                        style = MaterialTheme.typography.caption,
                        color = MaterialTheme.colors.error,
                    )
                }
                if (results.isEmpty()) {
                    Text("결과가 없습니다.", style = MaterialTheme.typography.body1)
                } else {
                    LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        items(results, key = { it.slug }) { hit ->
                            Card(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .clickable { onHitClick(hit) },
                                elevation = 2.dp,
                                backgroundColor = MaterialTheme.colors.surface
                            ) {
                                Column(modifier = Modifier.padding(16.dp)) {
                                    Text(
                                        text = hit.title,
                                        style = MaterialTheme.typography.subtitle1,
                                        color = MaterialTheme.colors.primary,
                                        maxLines = 2,
                                        overflow = TextOverflow.Ellipsis,
                                    )
                                    Spacer(modifier = Modifier.height(4.dp))
                                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                        hit.type?.takeIf { it.isNotBlank() }?.let { type ->
                                            Text(
                                                text = type,
                                                style = MaterialTheme.typography.caption,
                                                color = MaterialTheme.colors.primary,
                                            )
                                        }
                                        Text(
                                            text = hit.slug,
                                            style = MaterialTheme.typography.caption,
                                            color = MaterialTheme.colors.onSurface.copy(alpha = 0.6f),
                                            maxLines = 1,
                                            overflow = TextOverflow.Ellipsis,
                                        )
                                    }
                                    hit.snippet?.takeIf { it.isNotBlank() }?.let { snippet ->
                                        Spacer(modifier = Modifier.height(6.dp))
                                        Text(
                                            text = snippet,
                                            style = MaterialTheme.typography.body2,
                                            color = MaterialTheme.colors.onSurface.copy(alpha = 0.7f),
                                            maxLines = 3,
                                            overflow = TextOverflow.Ellipsis,
                                        )
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
