import os

# 1. Create gradle/libs.versions.toml
catalog_content = """[versions]
agp = "8.1.4"
kotlin = "2.0.0"
compose = "1.6.11"
ktor = "2.3.7"
sqldelight = "2.0.1"
koin = "3.5.3"
coroutines = "1.7.3"
serialization = "1.6.2"
androidx-activityCompose = "1.7.2"
androidx-appcompat = "1.6.1"
androidx-core-ktx = "1.10.1"
junit = "4.13.2"
foojay = "0.4.0"

[libraries]
ktor-client-core = { module = "io.ktor:ktor-client-core", version.ref = "ktor" }
ktor-client-content-negotiation = { module = "io.ktor:ktor-client-content-negotiation", version.ref = "ktor" }
ktor-serialization-kotlinx-json = { module = "io.ktor:ktor-serialization-kotlinx-json", version.ref = "ktor" }
ktor-client-android = { module = "io.ktor:ktor-client-android", version.ref = "ktor" }
ktor-client-darwin = { module = "io.ktor:ktor-client-darwin", version.ref = "ktor" }
ktor-client-mock = { module = "io.ktor:ktor-client-mock", version.ref = "ktor" }

koin-core = { module = "io.insert-koin:koin-core", version.ref = "koin" }
koin-android = { module = "io.insert-koin:koin-android", version.ref = "koin" }

sqldelight-coroutines = { module = "app.cash.sqldelight:coroutines-extensions", version.ref = "sqldelight" }
sqldelight-android = { module = "app.cash.sqldelight:android-driver", version.ref = "sqldelight" }
sqldelight-native = { module = "app.cash.sqldelight:native-driver", version.ref = "sqldelight" }
sqldelight-sqlite = { module = "app.cash.sqldelight:sqlite-driver", version.ref = "sqldelight" }

kotlinx-serialization-json = { module = "org.jetbrains.kotlinx:kotlinx-serialization-json", version.ref = "serialization" }
kotlinx-coroutines-core = { module = "org.jetbrains.kotlinx:kotlinx-coroutines-core", version.ref = "coroutines" }
kotlinx-coroutines-test = { module = "org.jetbrains.kotlinx:kotlinx-coroutines-test", version.ref = "coroutines" }

androidx-activity-compose = { module = "androidx.activity:activity-compose", version.ref = "androidx-activityCompose" }
androidx-appcompat = { module = "androidx.appcompat:appcompat", version.ref = "androidx-appcompat" }
androidx-core-ktx = { module = "androidx.core:core-ktx", version.ref = "androidx-core-ktx" }

junit = { module = "junit:junit", version.ref = "junit" }

[plugins]
androidApplication = { id = "com.android.application", version.ref = "agp" }
androidLibrary = { id = "com.android.library", version.ref = "agp" }
kotlinMultiplatform = { id = "org.jetbrains.kotlin.multiplatform", version.ref = "kotlin" }
kotlinAndroid = { id = "org.jetbrains.kotlin.android", version.ref = "kotlin" }
kotlinJvm = { id = "org.jetbrains.kotlin.jvm", version.ref = "kotlin" }
composeMultiplatform = { id = "org.jetbrains.compose", version.ref = "compose" }
composeCompiler = { id = "org.jetbrains.kotlin.plugin.compose", version.ref = "kotlin" }
kotlinSerialization = { id = "org.jetbrains.kotlin.plugin.serialization", version.ref = "kotlin" }
sqldelight = { id = "app.cash.sqldelight", version.ref = "sqldelight" }
foojayResolver = { id = "org.gradle.toolchains.foojay-resolver-convention", version.ref = "foojay" }
"""

os.makedirs('mobile/gradle', exist_ok=True)
with open('mobile/gradle/libs.versions.toml', 'w') as f:
    f.write(catalog_content)

# 2. Update settings.gradle.kts to load catalog if needed? 
# Actually Gradle loads 'gradle/libs.versions.toml' by default, 
# but let's rewrite settings.gradle.kts to remove extra properties.
settings_content = """rootProject.name = "MyApplication"

include(":androidApp")
include(":shared")
includeBuild("buildSrc")

pluginManagement {
    repositories {
        gradlePluginPortal()
        mavenCentral()
        google()
        maven("https://maven.pkg.jetbrains.space/public/p/compose/dev")
    }
}

plugins {
    alias(libs.plugins.foojayResolver)
}

dependencyResolutionManagement {
    repositories {
        mavenCentral()
        google()
        maven("https://maven.pkg.jetbrains.space/public/p/compose/dev")
    }
}
"""
with open('mobile/settings.gradle.kts', 'w') as f:
    f.write(settings_content)

# 3. Create buildSrc
os.makedirs('mobile/buildSrc', exist_ok=True)
with open('mobile/buildSrc/settings.gradle.kts', 'w') as f:
    f.write('dependencyResolutionManagement {\n    versionCatalogs {\n        create("libs") {\n            from(files("../gradle/libs.versions.toml"))\n        }\n    }\n}\n')

with open('mobile/buildSrc/build.gradle.kts', 'w') as f:
    f.write("""plugins {
    `kotlin-dsl`
}
repositories {
    mavenCentral()
    google()
    gradlePluginPortal()
}
""")

# 4. Migrate shared/build.gradle.kts
shared_build = """plugins {
    alias(libs.plugins.kotlinMultiplatform)
    alias(libs.plugins.androidLibrary)
    alias(libs.plugins.composeMultiplatform)
    alias(libs.plugins.composeCompiler)
    alias(libs.plugins.kotlinSerialization)
    alias(libs.plugins.sqldelight)
}

kotlin {
    androidTarget()

    listOf(
        iosX64(),
        iosArm64(),
        iosSimulatorArm64()
    ).forEach { iosTarget ->
        iosTarget.binaries.framework {
            baseName = "shared"
            isStatic = true
        }
    }

    sourceSets {
        val commonMain by getting {
            dependencies {
                implementation(compose.runtime)
                implementation(compose.foundation)
                implementation(compose.material)
                @OptIn(org.jetbrains.compose.ExperimentalComposeLibrary::class)
                implementation(compose.components.resources)
                
                implementation(libs.ktor.client.core)
                implementation(libs.ktor.client.content.negotiation)
                implementation(libs.ktor.serialization.kotlinx.json)
                
                implementation(libs.koin.core)
                
                implementation(libs.sqldelight.coroutines)
                implementation(libs.kotlinx.serialization.json)
                implementation(libs.kotlinx.coroutines.core)
            }
        }
        val commonTest by getting {
            dependencies {
                implementation(kotlin("test"))
                implementation(libs.kotlinx.coroutines.test)
            }
        }
        val androidMain by getting {
            dependencies {
                api(libs.androidx.activity.compose)
                api(libs.androidx.appcompat)
                api(libs.androidx.core.ktx)
                
                implementation(libs.ktor.client.android)
                implementation(libs.sqldelight.android)
                implementation(libs.koin.android)
            }
        }
        val androidUnitTest by getting {
            dependencies {
                implementation(kotlin("test-junit"))
                implementation(libs.junit)
                implementation(libs.sqldelight.sqlite)
                implementation(libs.kotlinx.coroutines.test)
                
                implementation(libs.ktor.client.mock)
            }
        }
        val iosX64Main by getting
        val iosArm64Main by getting
        val iosSimulatorArm64Main by getting
        val iosMain by creating {
            dependsOn(commonMain)
            iosX64Main.dependsOn(this)
            iosArm64Main.dependsOn(this)
            iosSimulatorArm64Main.dependsOn(this)
            dependencies {
                implementation(libs.ktor.client.darwin)
                implementation(libs.sqldelight.native)
            }
        }
    }
}

android {
    compileSdk = (findProperty("android.compileSdk") as String).toInt()
    namespace = "com.ppizil.raven.common"

    sourceSets["main"].manifest.srcFile("src/androidMain/AndroidManifest.xml")
    sourceSets["main"].res.srcDirs("src/androidMain/res")
    sourceSets["main"].resources.srcDirs("src/commonMain/resources")

    defaultConfig {
        minSdk = (findProperty("android.minSdk") as String).toInt()
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlin {
        jvmToolchain(17)
    }
}

sqldelight {
    databases {
        create("RavenDatabase") {
            packageName.set("com.ppizil.raven.common.db")
        }
    }
}
"""
with open('mobile/shared/build.gradle.kts', 'w') as f:
    f.write(shared_build)

# 5. Update androidApp/build.gradle.kts
android_build = """plugins {
    alias(libs.plugins.kotlinMultiplatform)
    alias(libs.plugins.androidApplication)
    alias(libs.plugins.composeMultiplatform)
    alias(libs.plugins.composeCompiler)
}

kotlin {
    androidTarget()
    sourceSets {
        val androidMain by getting {
            dependencies {
                implementation(project(":shared"))
            }
        }
    }
}

android {
    compileSdk = (findProperty("android.compileSdk") as String).toInt()
    namespace = "com.ppizil.raven"

    sourceSets["main"].manifest.srcFile("src/androidMain/AndroidManifest.xml")

    defaultConfig {
        applicationId = "com.ppizil.raven"
        minSdk = (findProperty("android.minSdk") as String).toInt()
        targetSdk = (findProperty("android.targetSdk") as String).toInt()
        versionCode = 1
        versionName = "1.0"
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlin {
        jvmToolchain(17)
    }
}
"""
with open('mobile/androidApp/build.gradle.kts', 'w') as f:
    f.write(android_build)

# 6. Update gradle.properties (remove duplicate version props)
with open('mobile/gradle.properties', 'r') as f:
    lines = f.readlines()
with open('mobile/gradle.properties', 'w') as f:
    for line in lines:
        if line.startswith('kotlin.version') or line.startswith('agp.version') or line.startswith('compose.version') or \
           line.startswith('ktor.version') or line.startswith('sqldelight.version') or line.startswith('koin.version') or \
           line.startswith('serialization.version'):
            continue
        f.write(line)

print("Migration done")
