---
paths:
  - "**/src/commonMain/**"
  - "**/src/commonTest/**"
  - "**/src/iosMain/**"
  - "**/src/appleMain/**"
  - "**/src/nativeMain/**"
  - "**/src/iosTest/**"
---

# Kotlin Multiplatform rules

Facts first: the session-start profile lists the shared modules, the targets they compile for, how the iOS app gets the framework, and what the shared code uses. Advice for one bridge to Swift or one Kotlin version is wrong for another.

- **Common code compiles for every target.** No `java.*`, `android.*` or Apple `platform.*` in `commonMain`: use the Kotlin standard library, a multiplatform library, or an interface implemented per platform. Time is `kotlin.time`, not `java.time` and not the old `kotlinx.datetime.Clock`.
- **Every `expect` needs an `actual` for each target.** Prefer an interface passed in over an `expect class`.
- **The Swift-facing API is designed, not inherited.** `@Throws` on anything Swift calls that can fail, no reliance on default arguments or generic functions, and suspend functions and flows exposed the way this project's bridge supports (plain Objective-C export, SKIE, KMP-NativeCoroutines or Swift export). Do not add or switch a bridge inside another task.
- **Versions move together.** Kotlin, Compose Multiplatform, KSP, SKIE, Metro, AGP, Gradle and Xcode each constrain the others. Read them from the version catalog and check the compatibility table before changing one.
- **Shared modules with the Android multiplatform library plugin have one variant.** No build types, flavors, `BuildConfig` or `debugImplementation` there.
- **Stored data.** A Room or SQLDelight schema change needs a version bump, a migration, and a test against a database written by the previous version. The database file location is a format too.
- **Concurrency.** Inject dispatchers. Shared mutable state needs an atomic, a mutex or one dispatcher. Nothing from the freezing era (`freeze`, `native-mt`).
- **Check cheaply.** Compile one target (`mobile verify`, or `./gradlew :<module>:compileKotlinIosSimulatorArm64`); do not run `build` or `assemble` to check an edit. A change to a signature Swift uses is not done until the iOS app compiles against it.
- **Test on more than the JVM** when the change touches `expect`/`actual`, threading or `iosMain`: `iosSimulatorArm64Test`. `Dispatchers.Main` in a native test needs `Dispatchers.setMain`.

Detail is in the `mobile-kotlin-multiplatform:kotlin-multiplatform` skill. Load the reference for the task: `build.md` (Gradle, AGP 9, Xcode integration, version tables, build failures and build time), `shared-code.md` (source sets, what common code may use, libraries, threads and memory on iOS), `swift-api.md` (the API Swift sees), `architecture.md` (what to share, view models, dependency injection, navigation, storage), `testing.md`.
