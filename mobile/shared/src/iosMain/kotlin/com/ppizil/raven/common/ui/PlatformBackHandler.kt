package com.ppizil.raven.common.ui

import androidx.compose.runtime.Composable

@Composable
actual fun PlatformBackHandler(enabled: Boolean, onBack: () -> Unit) {
    // iOS uses swipe-back gesture natively; no programmatic back handler needed.
}
