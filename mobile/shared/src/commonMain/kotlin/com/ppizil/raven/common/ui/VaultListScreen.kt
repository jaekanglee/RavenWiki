package com.ppizil.raven.common.ui

import androidx.compose.foundation.clickable
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
import androidx.compose.material.MaterialTheme
import androidx.compose.material.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.ppizil.raven.common.domain.model.VaultSummary

@Composable
fun VaultListScreen(
    vaults: List<VaultSummary>,
    selectedVault: String?,
    onVaultClick: (VaultSummary) -> Unit,
    modifier: Modifier = Modifier,
) {
    Column(modifier = modifier.fillMaxSize()) {
        Text(
            text = "보관소 ${vaults.size}개",
            style = MaterialTheme.typography.subtitle2,
            color = MaterialTheme.colors.onSurface.copy(alpha = 0.6f),
            modifier = Modifier.padding(start = 16.dp, top = 16.dp, end = 16.dp),
        )
        LazyColumn(
            modifier = Modifier.fillMaxSize(),
            contentPadding = PaddingValues(16.dp),
        ) {
            items(vaults, key = { it.name }) { vault ->
                Card(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(bottom = 12.dp)
                        .clickable { onVaultClick(vault) },
                    elevation = 2.dp,
                    backgroundColor = if (vault.name == selectedVault) {
                        MaterialTheme.colors.primary.copy(alpha = 0.12f)
                    } else {
                        MaterialTheme.colors.surface
                    },
                ) {
                    Column(modifier = Modifier.padding(16.dp)) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Text(
                                text = vault.name,
                                style = MaterialTheme.typography.h6,
                                color = MaterialTheme.colors.onSurface,
                            )
                            vault.mode?.let { mode ->
                                Spacer(modifier = Modifier.width(8.dp))
                                Text(
                                    text = mode,
                                    style = MaterialTheme.typography.caption,
                                    color = MaterialTheme.colors.primary,
                                )
                            }
                            if (vault.isDefault) {
                                Spacer(modifier = Modifier.width(8.dp))
                                Text(
                                    text = "기본",
                                    style = MaterialTheme.typography.caption,
                                    color = MaterialTheme.colors.onSurface.copy(alpha = 0.6f),
                                )
                            }
                        }
                        vault.path?.let { path ->
                            Spacer(modifier = Modifier.height(4.dp))
                            Text(
                                text = path,
                                style = MaterialTheme.typography.caption,
                                color = MaterialTheme.colors.onSurface.copy(alpha = 0.6f),
                                maxLines = 1,
                                overflow = TextOverflow.Ellipsis,
                            )
                        }
                    }
                }
            }
        }
    }
}
