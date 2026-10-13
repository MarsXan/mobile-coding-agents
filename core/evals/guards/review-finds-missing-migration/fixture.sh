#!/bin/bash
set -e
mkdir -p app/src/main/java/com/example/data
printf 'rootProject.name = "Example"\ninclude(":app")\n' > settings.gradle.kts
printf 'plugins { id("com.android.application") }\nandroid {\n    compileSdk = 35\n    defaultConfig { minSdk = 24 }\n}\n' > app/build.gradle.kts
cat > app/src/main/java/com/example/data/User.kt <<'EOF'
package com.example.data

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "users")
data class User(
    @PrimaryKey val id: Long,
    val name: String,
)
EOF
cat > app/src/main/java/com/example/data/AppDatabase.kt <<'EOF'
package com.example.data

import androidx.room.Database
import androidx.room.RoomDatabase

@Database(entities = [User::class], version = 3, exportSchema = true)
abstract class AppDatabase : RoomDatabase()
EOF
git init -q -b main && git add -A && git -c user.email=eval@example.com -c user.name=eval -c commit.gpgsign=false commit -qm "initial"
git checkout -q -b feature/last-seen
cat > app/src/main/java/com/example/data/User.kt <<'EOF'
package com.example.data

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "users")
data class User(
    @PrimaryKey val id: Long,
    val name: String,
    val lastSeenAt: Long,
)
EOF
git add -A && git -c user.email=eval@example.com -c user.name=eval -c commit.gpgsign=false commit -qm "Show last seen time on the profile"
