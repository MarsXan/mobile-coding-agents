# iOS: Swift concurrency

## Read the settings before giving advice

The same code is correct or wrong depending on four settings. They are in the session-start profile; `xcodebuild -showBuildSettings` is authoritative.

| Setting | Why it matters |
|---|---|
| `SWIFT_VERSION` (language mode 5 or 6) | In 5, data-race problems are warnings (or silent). In 6 they are errors, and isolation is also checked at run time. |
| `SWIFT_STRICT_CONCURRENCY` (minimal, targeted, complete) | How much is diagnosed in language mode 5. |
| `SWIFT_DEFAULT_ACTOR_ISOLATION` (Swift 6.2+) | With `MainActor`, every unannotated declaration in the module is main-actor isolated. |
| `SWIFT_APPROACHABLE_CONCURRENCY` and upcoming features (Swift 6.2+) | With `NonisolatedNonsendingByDefault`, a `nonisolated async` function runs on its caller's actor instead of moving to the global pool. Work that must leave the actor is then marked `@concurrent`. |

So "make it `nonisolated async` to get off the main thread" is right in one configuration and a hang in another. Check first.

## From diagnostic to smallest correct fix

| Diagnostic (wording varies by version) | Fix, in order of preference |
|---|---|
| "Sending 'x' risks causing data races" / "non-Sendable type passed" | Make the type a value type or immutable so it is `Sendable`; or keep it on one actor and pass an identifier; or transfer it and stop using it at the call site. |
| "Static property 'x' is not concurrency-safe because it is nonisolated global shared mutable state" | Make it `let`; or isolate it (`@MainActor static var`); or move it into an actor. |
| "Main actor-isolated property 'x' can not be referenced from a nonisolated context" | Make the caller `@MainActor` if it is UI code; or `await` it from an async context; or mark the member `nonisolated` if it truly needs no isolation. |
| "Conformance of 'T' to protocol 'P' crosses into main actor-isolated code" | Isolate the conformance (`extension T: @MainActor P`, Swift 6.2+); or mark the requirement implementations `nonisolated`; or, for a protocol from a module not yet migrated, `@preconcurrency` on the conformance. |
| "Capture of 'self' with non-Sendable type in a `@Sendable` closure" | Isolate the type to an actor (a `@MainActor` class is `Sendable`), or capture only the `Sendable` values the closure needs. |
| "Call to main actor-isolated instance method in a synchronous nonisolated context" from a delegate callback | If the API documents main-thread delivery: `MainActor.assumeIsolated { }`. If not: `Task { @MainActor in }`. |

**Escape hatches need a reason next to them.** `@unchecked Sendable` is right only for a type that is protected by a lock you can point to (`Mutex` from iOS 18, `OSAllocatedUnfairLock` from iOS 16). `nonisolated(unsafe)` is right only for state with external synchronisation. `@preconcurrency import` is right for a dependency that has not adopted concurrency. None of them is a fix for your own unsynchronised state.

## Rules

- **Structured first.** `async let` and task groups cancel and propagate errors for you. `Task { }` is for bridging from synchronous code; it inherits the actor and priority. `Task.detached` inherits nothing and is rarely right.
- **Cancellation is cooperative.** Long work calls `try Task.checkCancellation()` or checks `Task.isCancelled`. SwiftUI's `.task` cancels on disappear; in UIKit store the task and cancel it.
- **Actors are re-entrant.** State can change across every `await` inside an actor method. Re-check invariants after an `await`; to avoid duplicate work store the in-flight `Task` and await it.
- **Continuations resume exactly once** on every path. No resume leaks the task forever; two resumes crash. A delegate that fires many times is an `AsyncStream` with an `onTermination` that unregisters it.
- **Never block a concurrency thread.** No `DispatchSemaphore.wait`, `DispatchGroup.wait` or `sync` to wait for async work: the pool is small and it deadlocks. Blocking or CPU-heavy work goes off the actor explicitly (`@concurrent` or a nonisolated async function, depending on the settings above) or onto a dedicated queue bridged with a continuation.
- **Main actor means UI.** Parsing, image decoding, database work and file I/O do not belong on it, even if that is the default isolation.
- **`[weak self]` in a `Task`** only matters for tasks that outlive their owner's usefulness, such as loops over endless streams.

## Interop with what is already there

- **Completion handlers.** Wrap with `withCheckedThrowingContinuation`. Keep the callback version if other callers use it; add the async one beside it.
- **GCD.** `DispatchQueue.main.async` inside main-actor code is usually redundant and reorders work. A serial queue protecting state maps to an actor, but the actor is re-entrant and the queue was not: check every method that awaits.
- **Combine.** `publisher.values` gives an `AsyncSequence`, but a subject that emits while the consumer is busy can drop values; add `.buffer` if every value matters. A loop over a publisher that never completes keeps its task and captures alive until cancelled.
- **Objective-C and older libraries.** Their callbacks can arrive on any queue. In language mode 6, a closure inferred as main-actor isolated and then called on a background queue traps at run time (`dispatch_assert_queue` in the stack). Make the closure `@Sendable` and hop to the main actor inside it.

## Migrating a module to Swift 6 language mode

1. One module at a time, leaf modules first. Modules in different language modes interoperate.
2. In language mode 5, raise `SWIFT_STRICT_CONCURRENCY` to `targeted`, then `complete`, and clear the warnings.
3. Fix in this order: global and static mutable state; model types made `Sendable`; protocol and delegate boundaries; callbacks and closures; then the leftovers.
4. Enable upcoming features one at a time, not as a bundle.
5. Switch the module to language mode 6. Run the tests and exercise the app: mode 6 adds run-time isolation checks that the compiler could not prove.
6. Whether a UI module should default to main-actor isolation is a team decision with a real effect on libraries and background code. Propose it; do not flip it inside another change.

Count the escape hatches before and after (`mobile recon` reports them). A migration that adds them has moved the problem, not solved it.
