#!/bin/bash
set -e
# A Kotlin Multiplatform project: `shared` compiles for Android and iOS.
S=shared/src
mkdir -p $S/commonMain/kotlin/com/example/shared $S/androidMain/kotlin/com/example/shared $S/iosMain/kotlin/com/example/shared gradle androidApp
cat > settings.gradle.kts <<'EOF'
rootProject.name = "Example"
include(":androidApp", ":shared")
EOF
cat > gradle/libs.versions.toml <<'EOF'
[versions]
agp = "8.13.0"
kotlin = "2.2.20"

[plugins]
kotlinMultiplatform = { id = "org.jetbrains.kotlin.multiplatform", version.ref = "kotlin" }
androidLibrary = { id = "com.android.library", version.ref = "agp" }
androidApplication = { id = "com.android.application", version.ref = "agp" }
EOF
cat > shared/build.gradle.kts <<'EOF'
plugins {
    alias(libs.plugins.kotlinMultiplatform)
    alias(libs.plugins.androidLibrary)
}

kotlin {
    androidTarget()
    iosArm64()
    iosSimulatorArm64()

    sourceSets {
        commonMain.dependencies {
        }
    }
}

android {
    namespace = "com.example.shared"
    compileSdk = 36
    defaultConfig {
        minSdk = 24
    }
}
EOF
cat > androidApp/build.gradle.kts <<'EOF'
plugins {
    alias(libs.plugins.androidApplication)
}
android {
    namespace = "com.example.app"
    compileSdk = 36
    defaultConfig {
        minSdk = 24
        targetSdk = 36
    }
}
dependencies {
    implementation(project(":shared"))
}
EOF
cat > $S/commonMain/kotlin/com/example/shared/Platform.kt <<'EOF'
package com.example.shared

expect fun platformName(): String
EOF
cat > $S/androidMain/kotlin/com/example/shared/Platform.android.kt <<'EOF'
package com.example.shared

actual fun platformName(): String = "Android ${android.os.Build.VERSION.SDK_INT}"
EOF
cat > $S/iosMain/kotlin/com/example/shared/Platform.ios.kt <<'EOF'
package com.example.shared

import platform.UIKit.UIDevice

actual fun platformName(): String = UIDevice.currentDevice.systemName() + " " + UIDevice.currentDevice.systemVersion
EOF
cat > $S/commonMain/kotlin/com/example/shared/Ids.kt <<'EOF'
package com.example.shared

/** Identifiers created on the device. Used by both apps. */
object Ids {
    fun orderReference(number: Int): String = "ORD-" + number.toString().padStart(6, '0')
}
EOF
cat > $S/commonMain/kotlin/com/example/shared/Money.kt <<'EOF'
package com.example.shared

/** Money is kept in cents everywhere. Used by both apps. */
object Money {
    fun toCents(units: Long, cents: Long): Long = units * 100 + cents
}
EOF
git init -q -b main && git add -A && git -c user.email=eval@example.com -c user.name=eval -c commit.gpgsign=false commit -qm "initial"
