---
description: Code added to a common source set uses only APIs that exist on every target of the module.
tags: [kotlin-multiplatform, guard]
plugins: ["../../../core", "../../../KotlinMultiplatform", "../../../Android"]
max_turns: 12
allowed_tools: [Read, Glob, Grep, Skill]
---
Add `fun formatPrice(cents: Long): String` to the Money object in shared/src/commonMain/kotlin/com/example/shared/Money.kt. 1250 should give "12.50" and 5 should give "0.05". Both apps will call it.
