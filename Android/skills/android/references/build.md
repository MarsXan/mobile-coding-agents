# Android: Gradle, AGP, R8

## Commands

```sh
./gradlew --version                                   # Gradle, Kotlin and JVM actually in use
./gradlew --console=plain :app:compileDebugSources    # compile check, Java and Kotlin
./gradlew --console=plain :app:compileDebugKotlin     # faster in a Kotlin-only module
./gradlew --console=plain :feature:login:testDebugUnitTest --tests 'com.example.LoginViewModelTest'
./gradlew --console=plain :app:lintDebug
./gradlew :app:dependencyInsight --dependency okhttp --configuration debugRuntimeClasspath
./gradlew :app:dependencies --configuration debugRuntimeClasspath
```

- With product flavors every variant task carries the flavor: `compileStagingDebugKotlin`. `./gradlew tasks --all` lists them.
- Instrumented tests (`connectedDebugAndroidTest`) need a device or emulator. Gradle Managed Devices give a reproducible one.
- Add `--stacktrace` or `--info` when the cause is in build logic; `--scan` only if the team uses build scans (it uploads data).
- `mobile verify` wraps the common checks and prints only the failures.

## What a failure means

| Message | Cause and next step |
|---|---|
| `Could not resolve` / `Could not find com.x:lib:1.2.3` | Wrong coordinates or version, a repository missing from `dependencyResolutionManagement`, or no network or credentials. Do not add `jcenter()`; it is gone. |
| `Duplicate class X found in modules A and B` | Two artefacts ship the same classes. `dependencyInsight` shows who brings each; align versions with a BOM or exclude the transitive duplicate. Jetifier is not the fix unless old support libraries are really present. |
| `Manifest merger failed` | Read `build/outputs/logs/manifest-merger-*-report.txt`. Resolve with `tools:replace` or `tools:node` on the one attribute in conflict. `android:exported needs to be explicitly specified`: set it deliberately (see `release.md`). |
| `Execution failed for task ':app:kaptDebugKotlin'`, KSP errors | An annotation processor (Room, Hilt, Moshi) rejected the code. Its own message is above the Gradle error; fix that. |
| `Unsupported class file major version`, `requires Java 17 to run` | The JDK running Gradle does not match what AGP needs. Fix the Gradle JDK or the toolchain; do not downgrade AGP. |
| `Inconsistent JVM-target compatibility` | Java and Kotlin compile to different targets. Set `kotlin { jvmToolchain(N) }` or align `compileOptions` with the Kotlin `jvmTarget`. |
| `This version of the Compose Compiler requires Kotlin version X` | Before Kotlin 2.0 the compiler extension version must match Kotlin. From Kotlin 2.0 apply the `org.jetbrains.kotlin.plugin.compose` plugin at the Kotlin version and delete `kotlinCompilerExtensionVersion`. |
| `Module was compiled with an incompatible version of Kotlin` | A dependency was built with a newer Kotlin than this project's compiler. Upgrade Kotlin or use an older version of that dependency. |
| R8 `Missing class X` | Add the missing dependency, or a precise `-dontwarn` for that class only if it is truly optional. |
| Crash in release only: `ClassNotFoundException`, `NoSuchMethodError`, fields null after JSON parsing | R8 removed or renamed something reached by reflection. Add the narrowest `-keep` or `@Keep`; check `build/outputs/mapping/<variant>/usage.txt`. Never `-dontobfuscate` or `-keep class ** { *; }`. |
| `AAPT: error: resource ... not found` | Missing in that variant's source set, or referenced through another module's `R` (non-transitive R classes: use the declaring module's `R`). |
| `Configuration cache problems found` | Build logic reads project state at execution time. Fix the task or plugin; do not turn the cache off for the whole build. |
| Lint fails the build | Fix the issue. Adding it to `lint-baseline.xml` is a team decision, not a build fix. |

## Upgrades

- **One upgrade per change**, each with a clean build and tests, in this order: Gradle wrapper (to what the target AGP requires), AGP, Kotlin (with KSP and the Compose compiler plugin), compileSdk, libraries, and last targetSdk.
- **targetSdk is a behaviour change**, not a build setting. Read "behavior changes for apps targeting" that level and test the affected flows. It gets its own change.
- **Read the release notes of the version you are moving to** for removed DSL and new defaults. Do not skip major versions.
- **AGP 9** builds Kotlin itself: the `org.jetbrains.kotlin.android` plugin is removed from modules and the `org.jetbrains.kotlin.kapt` plugin does not work with it (the bridge is `com.android.legacy-kapt`; the fix is KSP). Check the project's AGP before applying either form.
- **KSP** must be the release that matches the project's Kotlin. KSP 1 is gone.
- Versions live in `gradle/libs.versions.toml`. Artefacts managed by a BOM (Compose, Firebase, OkHttp) take no explicit version.

## Native libraries and 16 KB pages

Apps with native code that target API 35 or later must support 16 KB memory pages. A prebuilt `.so` from an old SDK fails this. Check an APK with `zipalign -c -P 16 -v 4 app.apk`, and update the NDK, AGP or the third-party SDK that ships the library.

## Build speed (only when that is the task)

Measure first (`--profile`, a build scan, or gradle-profiler). The usual wins: the configuration cache, the build cache, KSP instead of kapt, convention plugins in an included build instead of `buildSrc`, non-transitive R classes, smaller modules with `implementation` rather than `api` dependencies. Do not change JVM arguments without a measurement.

## Inside Claude Code's sandbox

Gradle writes to `~/.gradle` (wrapper distributions, caches, the daemon) and `~/.android`, and downloads from Google's and Maven Central's repositories. The toolkit's `docs/03-setup-and-validation.md` lists the settings; they are **untested** for Android because the machine the toolkit was built on has no JDK.
