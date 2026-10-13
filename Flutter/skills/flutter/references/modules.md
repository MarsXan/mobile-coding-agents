# Flutter: dependency injection and splitting an app into packages

Follow what the project does. Facts checked 2026-10-13 against docs.flutter.dev, dart.dev and pub.dev.

## Dependency injection

Whatever the tool, the rule is the same: a class receives what it needs through its constructor, and one place at the top of the app builds the graph. A widget or state holder that looks things up for itself hides its dependencies and is hard to test.

| The project uses | How to add a dependency | Trap |
|---|---|---|
| `provider` (what Flutter's guide uses) | add a `Provider` at the app root; read it where the state holder is created and pass it in | `context.read` deep inside widgets instead of at that one point |
| `RepositoryProvider` and `BlocProvider` (flutter_bloc) | provide the repository above the bloc; create the bloc with `context.read<Repo>()` | `BlocProvider.of` from the same `context` that provided the bloc fails |
| Riverpod | one provider per dependency; replace it in tests and flavours with `overrides` | a provider whose initialiser has side effects |
| `get_it` 9, often with `injectable` | register in the one setup function, before `runApp`; resolve in constructors or at the composition point | resolving inside methods; see below |

**get_it 9 specifics.**

- Async setup: `registerSingletonAsync` with `dependsOn`, then `await getIt.allReady()` before `runApp`. A lazy async singleton does not hold up `allReady()`.
- Disposal is strictly last-in-first-out by registration order since 9.0.
- Tests: the package's testing guide says not to call `reset()` between tests. `pushNewScope` in `setUp`, register the fakes there, `await popScope()` in `tearDown`. A scope left open gives "already registered" errors in the next test.
- An instance cannot be shared across isolates. A background isolate needs its own setup.
- With `injectable` the registrations are generated: change the annotations and run build_runner, never the `*.config.dart` file.

## Splitting into packages

**When.** A package boundary costs a pubspec, a resolution and code-generation wiring. It earns that when it enforces a rule the team keeps breaking (the domain must not import Flutter; features must not import each other), when code is shared between apps, or when analysis and test time have to come down. Otherwise a folder is enough.

**Shapes in use.**

- By layer: `packages/<name>_repository` and `packages/<name>_api_client`, with features in the app's `lib/`. Repositories do not depend on each other.
- By feature: `features/<name>/{domain,data,presentation}` packages, `shared/`, and `apps/`. Nothing depends on an app; domain depends on neither data nor presentation.
- Flutter's own sample mixes them: UI by feature, data and domain by type.

**Pub workspaces** (Dart 3.6 and later) are the standard way to keep several packages in one repository.

- The root `pubspec.yaml` lists the members under `workspace:` (globs need Dart 3.11); each member has `resolution: workspace`. There is one `pubspec.lock` and one `.dart_tool/package_config.json`, both at the root.
- Everything resolves together: a dependency has one version across all members, so a version bump is a repository-wide change.
- `dependency_overrides` go in the root: a package can be overridden only once.
- A stray `pubspec.yaml` between the root and a member breaks `pub get`.
- Run Flutter commands from the member directory. `flutter test <member>` from the root does not bundle that member's assets (flutter/flutter#193342, open in October 2026).
- `melos` 7 and later sits on top of workspaces for scripts, filters and versioning. Its settings live under `melos:` in the root pubspec, and `melos.yaml` is gone. Older repositories still have the earlier layout: check which one this is.

**Code generation across packages.** `dart run build_runner build` generates for the current package and what it depends on. `--workspace` (build_runner 2.11 and later) builds every member and keeps one `.dart_tool` at the root. Switching between the two forces a clean build.

**Analysis options.** A package with its own `analysis_options.yaml` does not inherit the root's. Share rules with `include:` (a path or a `package:` URI); local entries win.

**Publishing.** pub.dev rejects a package that has path dependencies. Internal packages set `publish_to: none`.

## Mistakes to expect from yourself

1. Resolving from `get_it` inside a method or a `build`, so the dependency is invisible and cannot be replaced in a test.
2. Registering after first use, or skipping `allReady()` for async singletons.
3. A new package for a feature that has one screen.
4. A feature package importing another feature package, or the domain importing Flutter.
5. A dependency version in one member that conflicts with another: the workspace resolves once for everyone.
6. Editing a generated registration or route file instead of its annotated source.
