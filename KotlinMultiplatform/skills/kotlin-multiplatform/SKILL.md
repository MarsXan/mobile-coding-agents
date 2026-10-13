---
name: kotlin-multiplatform
description: Kotlin Multiplatform engineering reference for Kotlin code shared between an Android app and an iOS app, with or without Compose Multiplatform. Covers source sets and what common code may use, expect and actual, the API that Swift sees (Objective-C export, SKIE, Swift export), Gradle, AGP 9 and Xcode integration, build failures and build time, architecture and dependency injection for shared code, Room, SQLDelight and DataStore, and tests. Use when working in a module with commonMain, androidMain or iosMain source sets, when a shared framework fails to build or link in Xcode, or when Kotlin has to be called from Swift.
---

# Kotlin Multiplatform engineering

Read the project facts first: the session-start profile, or `mobile detect`. The shared modules, the targets they compile for, how the iOS app gets the framework (direct integration, CocoaPods plugin, XCFramework or Swift package, SKIE, Swift export), and the Kotlin, AGP and Compose Multiplatform versions. Advice for one integration or one Kotlin version is wrong for another.

## Working in this codebase

- **Common code compiles for every target of its module.** A `java.*`, `android.*` or Apple `platform.*` API in `commonMain` breaks another platform's build. The edit guard refuses it when the module has a target that lacks the API.
- **The versions move together**: Kotlin, Compose Multiplatform, KSP, SKIE, Metro, AGP, Gradle and Xcode. Read them from the version catalog and check the compatibility tables in `references/build.md` before changing one.
- **Check with `mobile verify`.** It compiles the shared code for one Apple target (fast) and leaves linking to the app build. `build` and `assemble` link every framework and are far slower.
- The Android side of the repository follows the Android pack (`mobile-android:android`), and the Xcode app follows the iOS pack (`mobile-ios:ios`), when they are enabled.

## Load the reference that matches the task

| Task | Reference |
|---|---|
| Gradle setup, the Android library plugin for shared modules, AGP 9, Xcode integration, version compatibility, build failures, build time | [references/build.md](references/build.md) |
| Source sets, `expect` and `actual`, what belongs in common code, multiplatform libraries, threads and memory on iOS | [references/shared-code.md](references/shared-code.md) |
| Designing the API that Swift calls: suspend functions, flows, errors, sealed types, SKIE, Swift export | [references/swift-api.md](references/swift-api.md) |
| Structure of shared code: what to share, view models, dependency injection, navigation, storage with Room, SQLDelight or DataStore | [references/architecture.md](references/architecture.md) |
| Tests in `commonTest`, coroutines and flows, per-target test tasks, Compose Multiplatform UI tests | [references/testing.md](references/testing.md) |

## Specialist skills

JetBrains publishes `Kotlin/kotlin-agent-skills` with skills for the AGP 9 migration of a multiplatform project, the CocoaPods to Swift Package Manager migration, and Kotlin/Native build performance. Use them for those jobs if installed. Google's `agp-9-upgrade` skill says not to use it on Kotlin Multiplatform projects.

## Mistakes to expect from yourself

1. A JVM or Android API in common code: `java.time`, `java.util.UUID`, `android.util.Log`, `System.currentTimeMillis()`.
2. `kotlinx.datetime.Clock` or `Instant`: they moved to `kotlin.time` in kotlinx-datetime 0.7, and the old imports no longer compile.
3. An `expect class` where an interface with one implementation per platform would do. `expect` classes are still Beta.
4. A function that can throw, called from Swift, without `@Throws`: the app terminates instead of throwing.
5. Designing the Swift-facing API for Kotlin callers: default arguments, generic functions, `Flow<T>` and sealed classes do not arrive in Swift as written.
6. Bumping Kotlin to the newest patch while SKIE, KSP or Metro has no release for it yet.
7. Running `./gradlew build` to check a change, or linking a release framework in the edit loop.
8. `Dispatchers.Main` in a native unit test without `Dispatchers.setMain`.
9. `debugImplementation`, build types, flavors or `BuildConfig` in a shared module that uses the Android multiplatform library plugin: it has one variant.
10. Advice from before 2024: `freeze()`, the `native-mt` coroutines, `ios()` targets, `kotlin.native.cacheKind`, the `targetHierarchy` DSL.
