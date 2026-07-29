package com.ppizil.raven.common.ui

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.MaterialTheme
import androidx.compose.material.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.ppizil.raven.common.domain.model.Document

@Composable
fun DocumentDetailScreen(
    document: Document,
    modifier: Modifier = Modifier
) {
    Column(
        modifier = modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp)
    ) {
        Text(
            text = document.title,
            style = MaterialTheme.typography.h4,
            color = MaterialTheme.colors.onSurface
        )
        Spacer(modifier = Modifier.height(24.dp))
        Text(
            text = document.content,
            style = MaterialTheme.typography.body1,
            color = MaterialTheme.colors.onSurface
        )
    }
}
