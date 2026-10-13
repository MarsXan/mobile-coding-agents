# Kotlin Multiplatform: Gradle, AGP, Xcode and build problems

Facts checked 2026-10-13 against kotlinlang.org, developer.android.com and the tools' release notes. Versions change monthly: confirm against the linked tables before acting on a number here.

## Versions that must match

Kotlin's compatibility guide (kotlinlang.org/docs/multiplatform/multiplatform-compatibility-guide.html) lists, per Kotlin release, the supported Gradle range, AGP range and the Xcode version it was tested with. As of October 2026:

| Kotlin | Gradle | AGP | Xcode |
|---|---|---|---|
| 2.4.20 to 2.4.21 | 7.6.3 to 9.7.0 | 8.5.2 to 9.3.1 | 26.4 |
| 2.4.0 to 2.4.10 | 7.6.3 to 9.5.0 | 8.5.2 to 9.1.0 | 26.4 |
| 2.3.20 to 2.3.21 | 7.6.3 to 9.3.0 | 8.2.2 to 9.0.0 | 26.0 |
| 2.2.21 | 7.6.3 to 8.14 | 7.3.1 to 8.11.1 | 26.0 |

- A newer Gradle than listed usually works with deprecation warnings. A newer **Xcode** often does not: support for the next Xcode major arrives in a later Kotlin release.
- Compose Multiplatform has its own table (kotlinlang.org/docs/multiplatform/compose-compatibility-and-versioning.html): the current release needs Kotlin 2.1 or later, and 2.2.20 or later for iOS and web.
- Tools that plug into the compiler follow exact Kotlin versions: **SKIE**, **KSP**, **Metro**, **KMP-NativeCoroutines**. A new Kotlin patch can be days or weeks ahead of them. Check each one's supported list before a Kotlin bump, and bump them in the same change.
- Kotlin 2.4 raised the default minimum iOS version of the framework from 14 to 15, and removed the K1 compiler and the `targetHierarchy` DSL.

## The Android side of a shared module

- A shared module declares its Android target with the `com.android.kotlin.multiplatform.library` plugin and a `kotlin { android { namespace = ...; compileSdk = ...; minSdk = ... } }` block (AGP 8.12 and later; the block was called `androidLibrary` before, and that name is deprecated). Older projects use `com.android.library` with `androidTarget()`.
- That plugin has **one variant**: no build types, flavors or `BuildConfig`, and no `debugImplementation`. Android resources are off unless `androidResources { enable = true }`. Android dependencies go in `androidMain.dependencies`.
- Its test source sets are `androidHostTest` (JVM unit tests) and `androidDeviceTest` (instrumented), each off until enabled with `withHostTest {}` or `withDeviceTest {}`.
- **AGP 9**: the multiplatform plugin can no longer share a module with `com.android.application` or `com.android.library`. The Android app becomes its own module (`androidApp`) that depends on the shared one. Kotlin is built into AGP 9, so `org.jetbrains.kotlin.android` is removed. This is a migration with an official guide and a JetBrains skill (`kotlin-tooling-agp9-migration`); do it as its own change.

## How the iOS app gets the shared code

| Way | How it works | Notes |
|---|---|---|
| Direct integration | a Run Script phase in Xcode, before Compile Sources, runs `./gradlew :<module>:embedAndSignAppleFrameworkForXcode` | the default for a single repository. Needs `binaries.framework` on the iOS targets, and "User Script Sandboxing" off |
| CocoaPods Gradle plugin | Gradle generates a podspec; `pod install` wires it | cannot be combined with direct integration. The CocoaPods registry stops accepting new podspecs in December 2026: plan the move to Swift packages (`kotlin-tooling-cocoapods-spm-migration`) |
| XCFramework in a Swift package | `./gradlew :<module>:assemble<Name>XCFramework`, zip, checksum, `binaryTarget` in `Package.swift` | for a separate iOS repository. KMMBridge automates publishing |

Swift export (Kotlin producing a real Swift module instead of an Objective-C header) is Alpha, works only with direct integration, and is expected to change. Do not move a project to it unasked.

## Build failures and their usual cause

| Symptom | Cause |
|---|---|
| The framework or the `embedAndSign...` task is not found in Xcode | no `binaries.framework` declared for that target, script sandboxing still on, or a custom Xcode configuration without `KOTLIN_FRAMEWORK_BUILD_TYPE` |
| cinterop or link errors after an Xcode update | this Kotlin version does not support that Xcode yet. Check the table before changing code |
| "Building for iOS Simulator, but linking in object file built for iOS" or a missing architecture | the simulator target is missing: Apple-silicon simulators need `iosSimulatorArm64()` |
| iOS tasks unavailable on a Linux or Windows runner | compiling Apple klibs works on any host; linking, cinterop, CocoaPods and running tests need a Mac |
| Unresolved reference in `commonMain` to a JVM or Android type | a one-platform API in common code (`shared-code.md`) |
| A KSP processor does nothing on iOS | KSP is configured per target: `add("kspIosSimulatorArm64", ...)` and the others |
| Kotlin metadata or "unsupported Kotlin version" errors from a plugin | a compiler plugin or annotation processor older than the Kotlin version |

## Build time

- Check a change with one compile task: `./gradlew :<module>:compileKotlinIosSimulatorArm64`. To produce a framework, one link task: `linkDebugFrameworkIosSimulatorArm64`. `build` and `assemble` link every target in debug and release.
- Do not link release frameworks or assemble XCFrameworks in the edit loop.
- Keep `~/.konan` and the Gradle caches between CI runs. `org.gradle.caching=true`, and enough heap in `org.gradle.jvmargs`.
- `kotlin.native.cacheKind` is deprecated since Kotlin 2.3.20: remove it and other old "disable cache" workarounds from `gradle.properties` unless a current issue still requires them.
- The configuration cache works with the Kotlin plugin. It also runs tasks in parallel, so several link tasks can run at once and exhaust memory.
- Avoid `transitiveExport`; export only the modules Swift needs to see.

## Tasks to know

`compileKotlinIosSimulatorArm64`, `compileKotlinIosArm64`, `compileKotlinMetadata` (common code only), `allTests`, `iosSimulatorArm64Test`, `jvmTest`, `linkDebugFrameworkIosSimulatorArm64`, `embedAndSignAppleFrameworkForXcode`, `assembleXCFramework`.
