# Flutter: async, lifecycle and isolates

## One isolate, one thread

Dart code in an isolate runs on a single thread with an event loop. `async` and `await` interleave work; they do not run it in parallel.

- **I/O is already non-blocking.** A network call or file read does not need an isolate.
- **Heavy synchronous work blocks every frame**: decoding megabytes of JSON, image processing, cryptography, sorting or searching large lists. Move it with `Isolate.run(() => work(data))` (or `compute`).
- What crosses to an isolate is copied. Pass plain data. A closure that captures `this` drags the whole State or controller along and usually fails.
- A background isolate that uses plugins must call `BackgroundIsolateBinaryMessenger.ensureInitialized(token)` first.

## After every `await`: is the widget still there?

```dart
Future<void> _save() async {
  await repository.save(draft);
  if (!mounted) return;            // in a State
  Navigator.of(context).pop();
}
```

- In a `State`, check `mounted` before `setState` or any use of `context`. Elsewhere check `context.mounted`.
- The `use_build_context_synchronously` lint finds most cases. Do not silence it.

## Own what you create

- Dispose every `AnimationController`, `TextEditingController`, `ScrollController`, `FocusNode`; cancel every `StreamSubscription` and `Timer`; remove every listener; close every `StreamController`. Cancel before `super.dispose()`.
- In Riverpod use `ref.onDispose`; a Bloc or Cubit is closed by whoever created it.
- An undisposed listener keeps the whole `State` alive and keeps calling into it.

## `build`, `initState` and friends

- `build` runs often and must be pure: no I/O, no creating futures, streams or controllers.
- **`FutureBuilder` and `StreamBuilder` take an object created once**, in `initState` or in the state holder. A future created inside `build` restarts on every rebuild: duplicate requests and flicker.
- `initState` cannot be `async` and cannot read inherited widgets; use `didChangeDependencies` for those, or schedule with `WidgetsBinding.instance.addPostFrameCallback`.
- Never call `setState` during a build.

## Futures and errors

- An un-awaited future's error becomes an uncaught asynchronous error. Await it, or mark it deliberately with `unawaited(...)` and handle errors inside it.
- Futures cannot be cancelled. For "latest wins" (search as you type, quick tab switches) tag each request and ignore results that are no longer current.
- `Future.wait` runs everything even when one fails; decide what a partial failure means.
- Catch exceptions you can handle. An `Error` (a failed assertion, a null check, a range error) is a bug to fix, not a condition to catch.
- Wire `FlutterError.onError` and `PlatformDispatcher.instance.onError` to crash reporting, or failures in release are silent.

## Streams

- A single-subscription stream can be listened to once; a second listener throws. Use a broadcast stream when several are needed, knowing that late listeners miss earlier events.
- `await for` and `listen` both need an end: cancel the subscription when the owner goes away.
- Debounce user input before it reaches the network.

## App lifecycle

- `AppLifecycleListener` (or `WidgetsBindingObserver`) reports pause and resume. Stop timers, animations, camera and location when paused; refresh stale data on resume.
- The OS may kill a backgrounded app. In-memory state is gone on return: persist drafts and anything the user would be upset to lose. On Android, state restoration (`RestorationMixin`, a `restorationScopeId`) brings back navigation and small UI state.
- Dart timers do not run while the app is suspended. Work that must happen in the background needs the platform's scheduler through a plugin, within that platform's limits.

## Tests

Widget tests run in a fake-async zone: timers and delays advance only when the test pumps. See `testing.md`.
