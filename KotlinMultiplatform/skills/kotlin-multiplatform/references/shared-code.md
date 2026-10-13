# Kotlin Multiplatform: source sets, common code and libraries

Facts checked 2026-10-13 against kotlinlang.org and the libraries' release notes.

## Source sets

- With the default hierarchy template (applied automatically), declaring `androidTarget()` or the Android library block, `iosArm64()` and `iosSimulatorArm64()` gives `commonMain`, `androidMain`, `iosMain` (shared by both iOS targets), `appleMain`, `nativeMain`, and the matching `...Test` sets. Only groups that match declared targets exist.
- A manual `dependsOn` switches the template off with a warning. Do not add one to "fix" a missing source set; declare the target.
- `ios()` is deprecated: it left out the Apple-silicon simulator. `iosX64` (Intel simulators) is a low-priority target and is missing from the official template.
- Put code in the **narrowest shared** source set that every user of it can see: `commonMain` for everyone, `iosMain` for both iOS targets, a platform set for one.

## What common code may use

Common code is compiled for every target of the module. It may use the Kotlin standard library, `kotlinx` libraries and any library published for all of the module's targets.

| Need | In common code | Not in common code |
|---|---|---|
| Time | `kotlin.time.Clock`, `kotlin.time.Instant`; `kotlinx-datetime` for calendars and time zones | `java.time`, `System.currentTimeMillis()`, and the old `kotlinx.datetime.Clock` / `Instant` (moved to `kotlin.time` in kotlinx-datetime 0.7) |
| Identifiers | `kotlin.uuid.Uuid` | `java.util.UUID`, `NSUUID` |
| Files and bytes | `kotlinx-io`, Okio | `java.io.File`, `NSFileManager` |
| HTTP | Ktor client; the engine is chosen per platform (OkHttp on Android, Darwin on iOS) | OkHttp or `NSURLSession` directly |
| JSON | `kotlinx.serialization` | Gson, Moshi, `JSONSerialization` |
| Threads | coroutines, `kotlin.concurrent.atomics`, `@Volatile` | `synchronized`, `java.util.concurrent`, GCD |
| Logging | a small logger interface, or a multiplatform logging library | `android.util.Log`, `NSLog` |

Check whether an API is still marked experimental in the project's Kotlin version before using it; an opt-in is a decision, not a formality.

## Reaching a platform API

In order of preference:

1. **An interface in common code, implemented per platform and passed in** (constructor or the DI graph). Easy to fake in tests, and what the Kotlin docs recommend for most cases.
2. **`expect` function or property** with an `actual` in each platform source set. Good for small stateless things: the platform name, a default dispatcher, a factory.
3. **`expect class`**: still Beta (the compiler warns unless `-Xexpect-actual-classes` is set), and every `actual` must match the declared members exactly. Use it only where the project already does.

Every `expect` needs an `actual` in **each** target's source set, or in a shared one that covers them (`iosMain` covers both iOS targets). A missing one is a compile error for that target only, which a build of the other platform does not show.

## Threads and memory on iOS

- The old rules are gone: no freezing, no `InvalidMutabilityException`, no `native-mt` coroutines. Objects are shared between threads as on the JVM, so shared mutable state needs the same care: atomics, a mutex, or confinement to one dispatcher.
- `Dispatchers.Main` is the main queue on Apple targets, and `Dispatchers.IO` exists on native. Inject dispatchers; do not hard-code them.
- Kotlin objects are garbage collected, Swift objects are reference counted. A cycle made only of Kotlin objects is collected; a cycle that passes through a Swift or Objective-C object is not. Break those by hand (weak reference on the Swift side, or clear the callback).
- A Kotlin object handed to Swift is released only when the Kotlin collector runs: do not rely on `deinit` timing across the boundary.
- Collections crossing to Swift are copied on conversion. Do not pass large lists back and forth in a loop.

## Libraries that are multiplatform, and their traps

- **Room** works in common code (2.7 and later). Room 3 is a new artifact group, `androidx.room3`: KSP only, a driver is mandatory (`setDriver(BundledSQLiteDriver())`), and DAOs are suspend or `Flow`. The database constructor is an `expect object` with `@ConstructedBy`, and KSP is added for each target. Migration rules are the Android ones: a schema change needs a version bump and a migration.
- **SQLDelight**: `.sq` files are the current schema; numbered `.sqm` files migrate installed databases. A schema change without a new `.sqm` breaks existing installs (`mobile risk` reports it). Drivers are per platform.
- **DataStore**: only Preferences DataStore is supported in multiplatform code. The file path is supplied per platform.
- **Lifecycle ViewModel and Navigation** have multiplatform artifacts. Compose Multiplatform projects use the `org.jetbrains.androidx.*` coordinates. Outside the JVM, `viewModel()` needs an explicit initializer: there is no reflection to construct it.
- **Koin** runs everywhere, but Swift cannot call the reified `get<T>()`: expose a small helper in `iosMain`. **Metro** and **kotlin-inject** are compile-time alternatives.
- **Compose Multiplatform resources** live in `composeResources/` and are read through the generated `Res` class, not Android's `R`.

## Mistakes to expect from yourself

1. Writing Android-flavoured Kotlin in `commonMain` and learning about it from the iOS build.
2. An `actual` added for Android only.
3. `expect class` for something an interface does better.
4. A hard-coded dispatcher, or a mutable singleton with no protection.
5. A dependency in `commonMain.dependencies` that publishes no iOS artifact.
