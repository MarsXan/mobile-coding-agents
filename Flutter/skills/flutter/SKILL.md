---
name: flutter
description: Flutter and Dart engineering reference, including legacy apps. Covers toolchain and pub failures, native iOS and Android build failures inside a Flutter project, flavors and code generation, migrations of state management (setState, Provider, GetX, BLoC, Riverpod), navigation, null safety and deprecated APIs, platform channels and Pigeon, async and isolates, drift, sqflite and Hive migrations, widget, golden and integration tests, jank, startup and app-size work, security, accessibility and store requirements. Use when writing, reviewing, debugging, migrating or building Flutter or Dart code, or when flutter analyze, test or build fails.
---

# Flutter engineering

Read the project facts first: the session-start profile, or `mobile detect`. Dart SDK constraint, pinned Flutter version, state-management, routing and persistence packages, and the embedded iOS and Android minimums. Language features and framework APIs depend on those versions.

## Working in this codebase

- **Use the project's Flutter.** If a version is pinned (`.fvmrc`), run `fvm flutter` and `fvm dart`. Never state an SDK version from memory: `flutter --version` and `pubspec.lock` are the facts.
- **Keep the architecture that is there.** Use the state-management and routing libraries already in the profile. Do not add a second one, and do not restructure to a pattern the task did not ask for (`mobile-core:safe-change`, `mobile-core:migrate`).
- Check with `mobile verify`. For raw commands and what failures mean, read `references/build.md`.
- Generated files are outputs. Change the annotated source and run the generator.

## Load the reference that matches the task

| Task | Reference |
|---|---|
| Toolchain, pub resolution, code generation, flavors, iOS and Android build failures, the Dart MCP server | [references/build.md](references/build.md) |
| Migrating state management, navigation, null safety, deprecated APIs, platform channels | [references/legacy.md](references/legacy.md) |
| `async` and `await`, `mounted`, disposal, streams, isolates, app lifecycle | [references/concurrency.md](references/concurrency.md) |
| drift, sqflite, Hive, shared_preferences, secure storage, files, JSON models | [references/persistence.md](references/persistence.md) |
| Unit, widget, golden and integration tests, Patrol, flaky tests | [references/testing.md](references/testing.md) |
| Jank, rebuilds, startup, memory, app size | [references/performance.md](references/performance.md) |
| Secrets, network security, accessibility, localisation, store requirements | [references/release.md](references/release.md) |

## Specialist tools

- The plugin wires the Dart language server, so definitions, references and diagnostics come from the analyzer instead of text search.
- The official Dart and Flutter MCP server adds run-time tools for a running debug app (errors, widget tree, hot reload). It is opt-in; see `build.md`. Its tool names change between Dart releases: discover them, do not assume them.

## Mistakes to expect from yourself

1. Dart syntax or Flutter APIs newer than the project's SDK allows, or a version stated from memory.
2. A second state-management or routing library, or a rewrite toward a preferred architecture.
3. Editing a generated file, or forgetting to run the generator.
4. Using `context` or calling `setState` after an `await` without checking `mounted`; controllers and subscriptions never disposed.
5. Creating a future or stream inside `build`, so it restarts on every rebuild.
6. Answering a native build failure with `flutter clean`, a deleted lockfile, `dependency_overrides` or `pub upgrade --major-versions`.
7. Deprecated APIs: `WillPopScope`, `withOpacity`, `MaterialStateProperty`, `textScaleFactor`.
8. Treating `--dart-define` as a place for secrets, or accepting every certificate to "fix" a TLS error.
9. `pumpAndSettle` on a screen with an endless animation; updating goldens to get a test green.
10. Heavy synchronous work on the UI isolate, or an isolate spawned for I/O that was already asynchronous.
