package com.ppizil.raven.common.data.remote

import kotlinx.serialization.json.Json

/** 서버는 계약에 없는 필드를 함께 보낸다(vaults_root, backlinks 등). 앱과 테스트가 같은 설정을 쓴다. */
val ravenJson: Json = Json {
    isLenient = true
    ignoreUnknownKeys = true
}
