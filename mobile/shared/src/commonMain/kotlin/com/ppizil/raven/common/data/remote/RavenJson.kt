package com.ppizil.raven.common.data.remote

import kotlinx.serialization.json.Json

/** 서버는 계약에 없는 필드를 함께 보낸다(vaults_root, backlinks 등). 앱과 테스트가 같은 설정을 쓴다. */
val ravenJson: Json = Json {
    isLenient = true
    ignoreUnknownKeys = true
    // null은 아예 안 보낸다. 서버 계약에서 precondition ""는 "파일 부재 단언"이고
    // 필드 없음은 "검사 생략"이라, 모르는 토큰을 null로 실어 보내면 의미가 흐려진다.
    explicitNulls = false
}
