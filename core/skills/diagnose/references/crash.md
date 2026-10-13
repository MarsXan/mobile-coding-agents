# Reading crashes

A crash report is only evidence once its addresses or obfuscated names are mapped back to source, using the symbol files of **that exact build**. Symbol files from another build give confident, wrong line numbers.

## iOS

- **Symbol files.** dSYMs live in the archive (`*.xcarchive/dSYMs`). Match by UUID: `dwarfdump --uuid App.app.dSYM` must equal the UUID in the report's binary-images section. `mdfind "com_apple_xcode_dsym_uuids == <UUID>"` finds a dSYM on this Mac.
- **Symbolicate.** Xcode's Organizer does it when the dSYM is present. By hand: `atos -arch arm64 -o App.app.dSYM/Contents/Resources/DWARF/App -l <load address> <address...>`.
- **Where to look.** The thread marked *Crashed*, and for an uncaught exception the *Last Exception Backtrace*, which shows where it was thrown.

| Signal or code | Meaning | Usual cause |
|---|---|---|
| `EXC_BREAKPOINT (SIGTRAP)` | Swift runtime trap | force unwrap of nil, out-of-range index, failed `as!`, `fatalError`, a failed precondition |
| `EXC_BAD_ACCESS (SIGSEGV/SIGBUS)` | invalid memory access | use after free, unowned reference to a dead object, data race, Objective-C or C interop |
| `EXC_CRASH (SIGABRT)` | abort | uncaught `NSException` (unrecognized selector, inconsistent table or collection view update, constraint or KVO misuse) |
| `0x8badf00d` | watchdog | main thread blocked during launch, resume or a background task |
| `0xdead10cc` | terminated while suspended | holding a file or SQLite lock in a shared container when the app was suspended |
| `0xc00010ff` | thermal | the device overheated; often sustained CPU or GPU load |
| no crash report, app "restarts" | memory (jetsam) | memory growth; check the device's `JetsamEvent` logs and the memory graph |
| top frames `_dispatch_assert_queue_fail` or `swift_task_isCurrentExecutor` | actor isolation checked at run time | code declared for one actor was called on another, typically a callback from an Objective-C or pre-concurrency API arriving on a background queue |

## Android

- **Deobfuscate.** `retrace mapping.txt stacktrace.txt` (in the SDK's `cmdline-tools/latest/bin`). The mapping file is at `app/build/outputs/mapping/<variant>/mapping.txt` and must come from the same build; keep it for every release.
- **Native crashes.** `ndk-stack -sym <directory with unstripped .so files> -dump tombstone.txt`.
- **Device logs.** `adb logcat -b crash -d` prints the crash buffer. `ApplicationExitInfo` (API 30+) records why the last process died: crash, ANR, low memory or the user.
- **ANR.** The main thread did not respond to input for about 5 seconds. In the trace, read the `main` thread first: is it blocked on a lock (which thread holds it), in a binder call, or doing I/O.

| Exception | Usual cause |
|---|---|
| `IllegalStateException: Can not perform this action after onSaveInstanceState` | fragment transaction or navigation from an async callback after the activity stopped |
| `IllegalStateException: Fragment ... not attached` | using `requireContext()` or view bindings after the view was destroyed |
| `TransactionTooLargeException` | large objects in a `Bundle`, saved state or an `Intent` (binder buffer is about 1 MB, shared) |
| `WindowManager$BadTokenException` | showing a dialog on a destroyed activity |
| `IllegalStateException: Room cannot verify the data integrity` | entity changed without a version bump and migration |
| `ForegroundServiceStartNotAllowedException` | starting a foreground service from the background (API 31+) |
| `ClassNotFoundException`, `NoSuchMethodError`, `NoSuchFieldError` in release only | R8 removed or renamed something reached by reflection or serialization; add the narrowest keep rule |
| `NetworkOnMainThreadException`, `StrictMode` violations | blocking I/O on the main thread |
| `SecurityException` | missing permission, a non-exported component, or a background restriction |

## Flutter

- **Dart stack traces.** A release built with `--obfuscate --split-debug-info=<dir>` needs `flutter symbolize -i <stack file> -d <dir>/app.<platform>-<arch>.symbols`. Archive the symbols directory with every release.
- **Native frames.** Crashes inside the engine or a plugin are native: use the iOS dSYMs (including `App.framework` and `Flutter.framework`) or the Android native symbols as above.
- **Where errors surface.** `FlutterError.onError` for framework errors, `PlatformDispatcher.instance.onError` for uncaught asynchronous errors, and each isolate's own error port. If none is wired to crash reporting, failures are silent in release.

| Message | Usual cause |
|---|---|
| `setState() called after dispose()` | no `mounted` check after an `await`; a subscription or timer not cancelled |
| `Looking up a deactivated widget's ancestor is unsafe` | `context` used after an async gap or after the widget left the tree |
| `Null check operator used on a null value` | `!` on a value that is legitimately null in some state |
| `type 'Null' is not a subtype of type ...` | JSON shape differs from the model; a field the server omits |
| `MissingPluginException` | plugin not registered: hot restart needed after adding it, a background isolate without registration, or release shrinking |
| `A RenderFlex overflowed` | unbounded or oversized child; not a crash, but the layout is wrong on that screen size or text scale |
