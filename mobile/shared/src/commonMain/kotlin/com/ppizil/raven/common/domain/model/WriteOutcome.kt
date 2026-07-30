package com.ppizil.raven.common.domain.model

// 저장이 서버까지 갔는지, 큐에 남았는지, 남의 편집과 부딪혔는지 — 화면이 구분해 알려야 한다.
enum class WriteOutcome {
    Synced,
    Queued,
    Conflict,
}
