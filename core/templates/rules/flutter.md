---
paths:
  - "**/*.dart"
  - "**/pubspec.yaml"
  - "**/analysis_options.yaml"
---

# Flutter rules

Facts first: the session-start profile lists this project's Dart SDK constraint, pinned Flutter version, and its state-management, routing and persistence packages. Language features and framework APIs depend on those versions. Do not write syntax or call APIs newer than the constraint allows, and never state an SDK version from memory.

- **Use the project's Flutter.** If the version is pinned with fvm, run `fvm flutter` and `fvm dart`, not the global SDK.
- **Match the app's architecture.** Keep the state-management and routing libraries already in use. Do not introduce a second one or restructure to a pattern the task did not ask for.
- **Generated files** (`*.g.dart`, `*.freezed.dart` and similar) are outputs. Change the annotated source and run `dart run build_runner build --delete-conflicting-outputs`.
- **Async and lifecycle.** After every `await` in a `State`, check `mounted` (or `context.mounted`) before using `context` or calling `setState`. Dispose every controller, focus node, subscription and animation you create.
- **`build` stays pure and cheap.** No I/O and no futures created in `build`. Use `const` constructors. Extract widgets rather than helper methods that return widgets.
- **Deprecated APIs that models still write:** `WillPopScope` (use `PopScope`), `Color.withOpacity` (use `withValues(alpha:)`), `MaterialState*` (use `WidgetState*`). Check what the project's Flutter version supports before replacing.
- **Stored data.** A drift or sqflite table change needs a `schemaVersion` bump and a tested upgrade step. Hive field indexes are never reused. SharedPreferences keys and JSON shapes on disk are a format.
- **Native side.** A failure under `ios/` or `android/` is a native build problem. Read the actual Xcode or Gradle error. Do not answer it with `flutter clean`, deleted lockfiles or `pub upgrade --major-versions`.
- **Accessibility is part of done** for a UI change: `Semantics` labels on custom controls, text scales, 48dp targets.

Detail is in the `mobile-flutter:flutter` skill. Load the reference for the task: `build.md` (toolchain, native build failures, flavors), `legacy.md` (state-management, navigation and null-safety migrations), `architecture.md` (working inside BLoC, Riverpod or MVVM; layering), `modules.md` (dependency injection, packages and workspaces), `concurrency.md` (async, isolates), `persistence.md`, `testing.md`, `performance.md`, `release.md` (security, accessibility, store requirements).
