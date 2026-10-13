# Kotlin Multiplatform: the API that Swift sees

Kotlin written for Kotlin callers often arrives in Swift in a poor shape. Design the surface that crosses the boundary on purpose. Facts checked 2026-10-13 against kotlinlang.org and the SKIE and KMP-NativeCoroutines documentation.

## First, which bridge is this project using?

The session profile says how the framework reaches the iOS app. The bridge decides what Swift sees:

| Bridge | Status | Suspend functions | Flows | Sealed classes and enums |
|---|---|---|---|---|
| Objective-C export (the default) | stable | completion handler; Swift's `async` view of it has **no cancellation** | `Flow` loses its element type | no exhaustive `switch`; enums need a `default` |
| + SKIE (Touchlab) | follows exact Kotlin versions | real `async` with cancellation both ways | `AsyncSequence` that keeps the element type | exhaustive Swift enums |
| + KMP-NativeCoroutines | stable (1.x) | async, Combine or RxSwift wrappers with cancellation | typed, cancellable | not covered |
| Swift export | Alpha, direct integration only | `async` | `AsyncSequence` | Swift enums |

Do not change the bridge as part of another task. Each is a migration.

## Rules that hold with plain Objective-C export

- **Errors.** Only exceptions listed in `@Throws` (and their subclasses) become an `NSError` that Swift can catch. Any other exception that reaches Swift **terminates the app**. Annotate every function Swift calls that can fail, including suspend functions (without `@Throws` a suspend function passes on only `CancellationException`).
- **Default arguments are dropped.** Swift must pass every parameter. Add explicit overloads for the calls Swift needs.
- **Generics** survive only on classes, with variance and most bounds lost; generic functions and interfaces arrive as `Any`. Keep generic types off the boundary or wrap them.
- **Sealed classes** arrive as a class hierarchy with no exhaustiveness check. Expose a function that turns the value into something Swift can switch on, or use SKIE.
- **Value classes** arrive as their underlying type.
- **Top-level functions** land on a class named after the file: `Platform.kt` becomes `PlatformKt`. Group what Swift needs in an `object` or a class, reached through `.shared` for an object and `.companion` for a companion.
- **Names.** `@ObjCName` sets the Swift name, `@HiddenFromObjC` keeps a declaration out of the header, `@ShouldRefineInSwift` marks one that a Swift wrapper will replace.
- **Collections are copied** each time they cross. A `List<T>` becomes an `Array`; mutating it in Swift does not change the Kotlin list.
- **Primitives in generics are boxed** (`KotlinInt`, `KotlinBoolean`): a `List<Int>` is not an `[Int]` without conversion.

## Coroutines from Swift

- Since Kotlin 2.0.20 a suspend function may be called from any thread. Advice that it must be the main thread is out of date.
- With plain Objective-C export, cancelling the Swift `Task` does not cancel the coroutine. If cancellation matters (a search, a download), use SKIE or KMP-NativeCoroutines, or expose an explicit `cancel()`.
- A `Flow` cannot be collected from Swift directly. Options, in the order projects usually prefer: SKIE; KMP-NativeCoroutines; a small wrapper class in `iosMain` with `collect(onEach:onCompletion:)` returning a cancel handle.
- Decide which dispatcher the Kotlin side runs on; Swift callers should not have to know.

## Swift 6 and Sendable

Kotlin's generated headers carry no `Sendable` information. Under Swift 6 strict concurrency, passing Kotlin objects across actors produces diagnostics. The bridges are `@preconcurrency import Shared` at the import site (which does not cover every case), or a narrow `extension KotlinType: @retroactive @unchecked Sendable {}` for types that are in fact immutable. Say which one you used and why; do not scatter `@unchecked Sendable` to get a green build. JetBrains has published no timeline for annotating the headers.

## SKIE specifics

- SKIE supports a fixed list of Kotlin versions and usually lags a new patch by days or weeks. Check its supported list before a Kotlin bump; an unsupported pair fails the build.
- It changes the generated Swift API. Turning it on or off is a breaking change for every Swift caller.
- Its default-argument overloads are off by default and limited; do not rely on them.

## Keep the surface small

- Export only what the app needs: `internal` for everything else, and `export(...)` only for dependencies whose types appear in the public API.
- Prefer plain data classes, enums, and interfaces with a few methods at the boundary. Keep `Result`, `Pair`, lambdas with receivers and deeply generic types inside Kotlin.
- When a Kotlin change alters a public signature, the Swift callers break at the next framework build, not at the Kotlin build. Build the iOS app (or at least link the framework and compile the app target) before calling such a change done.

## Mistakes to expect from yourself

1. A throwing function without `@Throws`.
2. Relying on a default argument, an extension function or a generic function from Swift.
3. Returning `Flow` or `StateFlow` across the boundary with no bridge, or assuming Swift cancellation reaches Kotlin.
4. Adding SKIE, KMP-NativeCoroutines or Swift export to solve one call site.
5. Silencing Swift 6 diagnostics about Kotlin types wholesale.
6. Changing a shared signature and verifying only the Android build.
