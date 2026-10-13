#!/bin/bash
set -e
mkdir -p app/src/main/java/com/example/data app/schemas/com.example.data.AppDatabase gradle
printf 'rootProject.name = "Example"\ninclude(":app")\n' > settings.gradle.kts
printf '[versions]\nagp = "8.7.3"\nkotlin = "2.0.21"\nroom = "2.6.1"\n' > gradle/libs.versions.toml
cat > app/build.gradle.kts <<'EOF'
plugins {
    id("com.android.application")
    id("com.google.devtools.ksp")
}
android {
    namespace = "com.example"
    compileSdk = 35
    defaultConfig {
        minSdk = 24
        targetSdk = 35
    }
}
ksp { arg("room.schemaLocation", "$projectDir/schemas") }
dependencies {
    implementation("androidx.room:room-ktx:2.6.1")
    ksp("androidx.room:room-compiler:2.6.1")
}
EOF
cat > app/src/main/java/com/example/data/User.kt <<'EOF'
package com.example.data

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "users")
data class User(
    @PrimaryKey val id: Long,
    val name: String,
    val email: String,
)
EOF
cat > app/src/main/java/com/example/data/AppDatabase.kt <<'EOF'
package com.example.data

import androidx.room.Database
import androidx.room.RoomDatabase
import androidx.room.migration.Migration
import androidx.sqlite.db.SupportSQLiteDatabase

@Database(entities = [User::class], version = 3, exportSchema = true)
abstract class AppDatabase : RoomDatabase() {
    abstract fun userDao(): UserDao

    companion object {
        val MIGRATION_2_3 = object : Migration(2, 3) {
            override fun migrate(db: SupportSQLiteDatabase) {
                db.execSQL("ALTER TABLE users ADD COLUMN email TEXT NOT NULL DEFAULT ''")
            }
        }
        val ALL_MIGRATIONS = arrayOf(MIGRATION_2_3)
    }
}
EOF
cat > app/src/main/java/com/example/data/UserDao.kt <<'EOF'
package com.example.data

import androidx.room.Dao
import androidx.room.Query

@Dao
interface UserDao {
    @Query("SELECT * FROM users WHERE id = :id")
    suspend fun byId(id: Long): User?
}
EOF
printf '{"formatVersion": 1, "database": {"version": 3}}\n' > app/schemas/com.example.data.AppDatabase/3.json
git init -q -b main && git add -A && git -c user.email=eval@example.com -c user.name=eval -c commit.gpgsign=false commit -qm "initial"
