package com.ppizil.raven.common.presentation.mvi

import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.SharedFlow

interface MviViewModel<Intent, State, SideEffect> {
    val state: StateFlow<State>
    val sideEffect: SharedFlow<SideEffect>
    fun sendIntent(intent: Intent)
}
