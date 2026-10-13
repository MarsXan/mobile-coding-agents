# Flutter: legacy code and migrations

Every migration here goes through `mobile-core:migrate`: inventory, coexistence rule, small slices, gates. This file holds what is specific to each one.

## State management

**Rules for any move between libraries.**

- One library per feature at a time. Old and new meet at feature boundaries, never inside one widget tree.
- First move the logic, then the state holder: pull business logic out of widgets and controllers into plain Dart classes with unit tests. After that, swapping what exposes the state is mechanical.
- Leaf features first. The app shell, authentication state and navigation last.
- Ephemeral UI state (a text field's focus, an animation, a toggle nobody else reads) stays in `setState`. Migrate shared and business state only.

**GetX is four libraries.** Plan four migrations, in this order:

1. **Dependency injection**: `Get.put`, `Get.lazyPut`, `Get.find` and `Bindings` become constructor injection or the target library's scoping.
2. **Reactive state**: `.obs` with `Obx`, `GetBuilder` and `GetxController` become the target's state holder. `onInit` and `onClose` map to its init and dispose; GetX disposed controllers when their route left, so check who disposes them now.
3. **Context-free UI calls**: `Get.snackbar`, `Get.dialog`, `Get.back` become context-based calls or a small navigation service you own.
4. **Navigation last**: `Get.to` and named routes become the app's router, `Get.arguments` becomes typed route parameters, and `GetMaterialApp` becomes `MaterialApp.router` in the final slice.

**Provider to Riverpod.** Both can live in the tree together (`ProviderScope` above the existing providers). `context.watch`, `read` and `select` become `ref.watch`, `ref.read` and `ref.watch(p.select(...))`; a `ProxyProvider` becomes a provider that watches others.

**Riverpod 2 to 3 and BLoC major versions.** Read the migration guide for the exact versions. They change behaviour as well as names: Riverpod 3 retries failed providers by default and wraps errors; BLoC since version 8 handles events concurrently unless a transformer says otherwise, where older code relied on sequential handling. Pin the old behaviour explicitly (`sequential()`, retry off) and test error paths before changing anything else.

## Navigation: Navigator 1.0 to go_router

- Map each named route or `MaterialPageRoute` to a `GoRoute`. Pass arguments as path or query parameters; `extra` is not restorable and does not survive a deep link.
- `context.go` replaces the stack; `context.push` adds to it and can return a result (`context.pop(value)`).
- Bottom navigation with preserved tab state is `StatefulShellRoute`.
- Authentication guards belong in `redirect` with a `refreshListenable`, not in each screen's `initState`.
- Existing imperative `Navigator.push` calls keep working above a go_router page, which allows a screen-by-screen migration.
- Deep links need platform configuration (associated domains on iOS, verified intent filters on Android) and tests from a terminated app.
- Back handling uses `PopScope`. Test Android's predictive back gesture.

## Null safety and Dart 3

- A Dart 3 SDK cannot run code that is not null-safe, and the migration tool no longer exists in it. Very old code must be migrated with a Dart 2.19 toolchain first (pin it with fvm), in dependency order, then upgraded.
- Do not fill the code with `!` and `late`. Each `!` is a crash site and each `late` is a run-time check. Prefer flow analysis, defaults and early returns.

## Deprecated APIs

Check each against the project's Flutter version before changing it; `dart fix --apply` handles many.

| Old | Current |
|---|---|
| `WillPopScope` | `PopScope` with `canPop` and `onPopInvokedWithResult` |
| `color.withOpacity(x)` | `color.withValues(alpha: x)` |
| `MaterialStateProperty`, `MaterialState` | `WidgetStateProperty`, `WidgetState` |
| `MediaQuery.of(context).textScaleFactor` | `MediaQuery.textScalerOf(context)` |
| `MediaQuery.of(context).size` | `MediaQuery.sizeOf(context)`, which rebuilds only when size changes |
| `Scaffold.of(context).showSnackBar` | `ScaffoldMessenger.of(context).showSnackBar` |
| `FlatButton`, `RaisedButton`, `OutlineButton` | `TextButton`, `ElevatedButton`, `OutlinedButton` |
| `describeEnum(value)` | `value.name` |
| `RawKeyboardListener`, `RawKeyEvent` | `KeyboardListener`, `KeyEvent` |

- Material 3 is the default; an app that sets `useMaterial3: false` did so on purpose. Moving to Material 3 is a visual migration with design review, not a clean-up.
- Material and Cupertino widgets are moving out of the SDK into packages, opt-in from Flutter 3.47. Do not start that migration unasked.
- Deprecation lists and what the SDK actually removed sometimes disagree. Verify a "removed" API against the project's SDK before rewriting code that still compiles.

## Platform channels to Pigeon

- Define the API once in a Dart file; Pigeon generates type-safe Dart, Kotlin and Swift. This removes string method names and untyped maps, which are where channel bugs live.
- One channel per change. Keep the old `MethodChannel` until that feature's slice has switched on all platforms.
- Errors become typed (`FlutterError`) on the native side; map them deliberately.
- Handlers run on the platform's main thread: move slow work off it.
- A plugin used from a background isolate needs `BackgroundIsolateBinaryMessenger.ensureInitialized`.

## Host-project migrations that Flutter upgrades bring

The iOS scene lifecycle (from Flutter 3.38), Swift Package Manager for plugins (default from 3.44), the Gradle Kotlin DSL, and built-in Kotlin under AGP 9 (supported from 3.47) each have an official guide. Do them one at a time, each with a build on both platforms, and keep them out of feature changes.
