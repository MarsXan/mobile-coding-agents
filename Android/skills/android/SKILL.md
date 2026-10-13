---
name: android
description: Android engineering reference for Kotlin, Jetpack Compose, Views and Java codebases, including legacy ones. Covers Gradle, AGP and R8 failures, lifecycle, process death and saved state, coroutines and Flow, migrations from RxJava, LiveData, Views, kapt and Dagger with Compose interop, Room and DataStore migrations, unit, UI and screenshot tests, startup, jank, ANR and memory work, security, accessibility and Google Play requirements. Use when writing, reviewing, debugging, migrating or building Android code, or when a Gradle build or an Android test fails.
---

# Android engineering

Read the project facts first: the session-start profile, or `mobile detect`. minSdk, compile and target SDK, AGP, Kotlin and Gradle versions, and whether the project uses kapt, KSP, Compose, flavors, RxJava, Java. Advice that is right for AGP 9 or Kotlin 2.x is wrong for an older project, and the reverse.

## Working in this codebase

- Match the stack of the file you are in. Modernise only when that is the task (`mobile-core:safe-change`, `mobile-core:migrate`).
- Check with `mobile verify`. For raw Gradle commands and what their failures mean, read `references/build.md`.
- Always use the wrapper (`./gradlew`), never a global `gradle`.
- Read versions from the version catalog and `./gradlew --version`; do not recall them. Compatibility between AGP, Gradle, the JDK, Kotlin and compileSdk is a matrix: look it up in the release notes for this project's AGP.

## Load the reference that matches the task

| Task | Reference |
|---|---|
| Gradle, AGP, Kotlin and R8 failures, dependency conflicts, upgrades, version catalogs | [references/build.md](references/build.md) |
| Views, Fragments and Java code; migrating RxJava, LiveData, kapt, Dagger, Views to their successors; Compose interop; edge-to-edge and back handling | [references/legacy.md](references/legacy.md) |
| Coroutines, Flow, lifecycle-aware collection, threading, background work, process death | [references/concurrency.md](references/concurrency.md) |
| Room, DataStore, SharedPreferences, files, backup, schema migration | [references/persistence.md](references/persistence.md) |
| Unit, Compose and Espresso tests, screenshot tests, flaky tests | [references/testing.md](references/testing.md) |
| Startup, jank, ANR, memory, app size | [references/performance.md](references/performance.md) |
| Security, permissions, accessibility, localisation, Google Play requirements | [references/release.md](references/release.md) |

## Specialist skills

If installed, use these for their speciality and this skill for everything around it: Google's `android-skills` (`agp-9-upgrade`, `edge-to-edge`, `navigation-3`, `r8-analyzer`, `android-profiler`, `migrate-xml-views-to-jetpack-compose`), `gradle-skills` for build logic.

## Mistakes to expect from yourself

Several of these are what public agent benchmarks on Android tasks report as the residual failures.

1. State that does not survive rotation or process death.
2. A screen that only works in the light theme, at the default font scale, on a phone in portrait.
3. A dependency-injection change that compiles and fails at run time. Launch the app or run an instrumented smoke test.
4. An API above minSdk with no version check.
5. `GlobalScope`, `runBlocking` on the main thread, or a flow collected without the lifecycle.
6. A "build fix" that changes versions, adds `-dontwarn` or `@Suppress`, raises a lint baseline, or changes compileSdk or targetSdk.
7. Advice for the wrong AGP or Kotlin generation: Kotlin plugin setup, kapt versus KSP, the Compose compiler.
8. A Room entity changed with no version bump and migration.
9. A missing `android:exported`, an unvalidated `Intent`, a mutable `PendingIntent`.
10. A failing screenshot or assertion "fixed" by raising a threshold or deleting the assertion.
