# Android: coroutines, Flow, lifecycle and threads

## Scopes: who owns the work

| Work | Scope |
|---|---|
| Tied to a screen's data | `viewModelScope` |
| Tied to a visible UI | `lifecycleScope`; in a Fragment `viewLifecycleOwner.lifecycleScope` |
| Must outlive the screen but not the process | an application scope that is injected (`CoroutineScope(SupervisorJob() + Dispatchers.Default)`) |
| Must finish even if the process dies | WorkManager |

Never `GlobalScope`: nothing cancels it, nothing tests it, and failures vanish.

## Dispatchers and main-safety

- A suspend function is **main-safe**: the function that blocks moves itself with `withContext`. Callers do not wrap it.
- Room and Retrofit suspend functions are already main-safe. Wrapping them again in `withContext(Dispatchers.IO)` is noise.
- Inject dispatchers; do not hard-code `Dispatchers.IO` in classes you want to test.
- No disk, network or heavy computation on the main thread. `runBlocking` there is an ANR waiting for a slow device. Turn on `StrictMode` in debug builds to find violations.

## Cancellation and errors

- Cancellation is cooperative. Long loops call `ensureActive()` or `yield()`.
- **Never swallow `CancellationException`.** `catch (e: Exception)` and `runCatching` both catch it and break cancellation. Rethrow it, or catch specific exception types.
- `withTimeout` throws a `TimeoutCancellationException`, which is a cancellation: unhandled, it silently cancels the caller. Use `withTimeoutOrNull` or catch it explicitly.
- Cleanup that must suspend runs in `withContext(NonCancellable)` inside `finally`.
- An exception in `launch` goes to the parent and cancels its other children. Independent children need `supervisorScope` or a `SupervisorJob`. An exception in `async` appears at `await()`.
- `coroutineScope { }` with `async` is the way to run things in parallel and fail together.

## Flow

- Expose UI state as `StateFlow`: `stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), initial)`. The five seconds keep the upstream alive across a rotation.
- A function that builds a new flow on every call re-runs the upstream for every collector. Build it once and share it.
- `flowOn` changes the upstream only. The collector runs where it was launched.
- `MutableStateFlow.update { }` for atomic changes; `value = value.copy(...)` from two threads loses updates.
- Wrap callbacks with `callbackFlow` and always end it with `awaitClose { unregister() }`.
- One-off events for one consumer: a `Channel` exposed with `receiveAsFlow()`. A `SharedFlow` with no replay drops events emitted while nobody collects.

## Collecting in the UI

- Views: `repeatOnLifecycle(Lifecycle.State.STARTED) { flow.collect { } }`.
- Compose: `collectAsStateWithLifecycle()`.
- `lifecycleScope.launch { flow.collect { } }` alone keeps collecting in the background and updates destroyed views. `launchWhenStarted` is deprecated: it pauses the collector but leaves the upstream running.

## Shared mutable state

- Confine it: one owner, updated through `StateFlow.update`, a `Mutex` (not re-entrant), or a dispatcher limited to one thread (`limitedParallelism(1)`).
- `synchronized` around a suspending call is wrong: the lock is held across the suspension or not at all.

## Surviving the system

- **Configuration change** (rotation, dark mode, font scale, resize): the Activity is re-created, the ViewModel survives.
- **Process death** (app in background, memory needed): everything in memory is gone; only saved instance state and persisted data return. `SavedStateHandle` and `rememberSaveable` hold small UI state; data belongs in a database or DataStore.
- Test it: enable "Don't keep activities", and with the app in the background run `adb shell am kill <package>`, then return to it.
- `android:configChanges` to avoid re-creation hides state bugs; it is not a fix.

## Background work and its limits

- Deferrable work that must run: WorkManager with constraints, backoff and unique work names.
- A foreground service needs a declared `foregroundServiceType` and the matching permission (API 34+), and cannot be started from the background (API 31+).
- A `BroadcastReceiver` has seconds, on the main thread. Hand off to WorkManager, or use `goAsync()` for short work.
- Doze and app standby delay alarms, jobs and network. Exact alarms need a permission. Design for late execution.

## Bridging older code

- A callback API becomes a suspend function with `suspendCancellableCoroutine`, and `invokeOnCancellation` unregisters it.
- An `ExecutorService` becomes a dispatcher with `asCoroutineDispatcher()`.

## Testing

`runTest` with a `StandardTestDispatcher`; replace `Dispatchers.Main` with a test rule; advance virtual time with `advanceUntilIdle()`. No real delays. See `testing.md`.
