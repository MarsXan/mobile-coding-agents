# Flutter: toolchain, pub, code generation, native builds

## Commands

```sh
flutter --version                     # the SDK actually in use (prefix with fvm when pinned)
flutter analyze
flutter test test/path_test.dart --name "pattern"
dart format --output=none --set-exit-if-changed .
dart run build_runner build --delete-conflicting-outputs
flutter pub outdated                  # what is resolvable and what is latest
flutter build apk --debug             # proves the Android side builds
flutter build ios --debug --no-codesign --simulator
flutter analyze --suggestions         # checks Java, Gradle, AGP and Kotlin compatibility
```

`mobile verify` wraps analyze and test and prints only the failures.

## Dependencies

- `pubspec.lock` is committed for apps and is never hand-edited or deleted wholesale. Deleting it upgrades every transitive dependency at once.
- Upgrade one package per change: `flutter pub upgrade <package>`. `--major-versions` is an upgrade project, not a fix.
- `dependency_overrides` is temporary, with a comment saying why and when it goes.
- After a Flutter or Dart upgrade, `dart fix --dry-run` lists the automated migrations; apply them as their own change.
- In a workspace (melos, or pub workspaces with `resolution: workspace`), run commands at the level the repository's scripts use.

## What a failure means

| Message | Cause and next step |
|---|---|
| `version solving failed` | Read the chain: it names the two constraints that conflict. `flutter pub outdated` shows which package holds the other back. Not solved by `any`, an override, or deleting the lockfile. |
| `The current Dart SDK version is X. Because <app> requires SDK version ...` | The wrong Flutter is on the path (use the pinned one), or the constraint and the pinned version disagree. Changing either is a decision. |
| `Target of URI hasn't been generated`, missing `part '*.g.dart'` | Run build_runner. `Conflicting outputs`: add `--delete-conflicting-outputs`. |
| `MissingPluginException` | The native side is not registered: stop and rebuild fully (hot reload does not add plugins), check the plugin supports this platform, and that a background isolate initialised its messenger. |
| `Gradle task assembleDebug failed with exit code 1` | That line is not the error. The cause is above it, or run `cd android && ./gradlew assembleDebug --stacktrace`. |
| `Your project requires a newer version of the Kotlin Gradle plugin`, `Minimum supported Gradle version is X` | Raise the Kotlin plugin version in `android/settings.gradle*`, or the wrapper's `distributionUrl`. One at a time; `flutter analyze --suggestions` shows a compatible set. |
| `Unsupported class file major version` | JDK mismatch. Point Flutter at the right one: `flutter config --jdk-dir <path>`. |
| `Namespace not specified` in a plugin | The plugin predates AGP 8. Upgrade the plugin. |
| `minSdkVersion N cannot be smaller than version M declared in library` | A plugin needs a higher Android minimum. Raising `minSdk` drops users: a product decision. |
| `CocoaPods could not find compatible versions`, `sandbox is not in sync with the Podfile.lock` | `cd ios && pod install` (add `--repo-update` if the spec repo is stale). `requires a higher minimum iOS deployment version`: the Podfile platform and the Runner target must both be raised, which is a product decision. |
| iOS signing errors | Do not change team, bundle identifier or provisioning settings to get a build. Ask. |
| A change does not appear after hot reload | Changes to `main`, global initialisers, enum and generic types, and native code need a hot restart or a full rebuild. |

## Native projects inside a Flutter app

- `ios/` and `android/` are real Xcode and Gradle projects. For anything beyond the table, the native platform skill (`mobile-ios:ios`, `mobile-android:android`) applies if installed.
- Flutter rewrites parts of them during upgrades (Swift Package Manager integration, the scene lifecycle, Gradle Kotlin DSL, built-in Kotlin under AGP 9). Follow the migration guide for the project's Flutter version and commit the tool's changes separately from feature work.
- Swift Package Manager is the default for iOS plugins from Flutter 3.44; plugins without a package fall back to CocoaPods. The CocoaPods registry becomes read-only on 2 December 2026.
- `flutter create .` regenerates missing platform files. Review its diff before keeping any of it.

## Flavors and configuration

- A flavor needs matching pieces on both sides: Android `productFlavors`, and iOS schemes with build configurations named for the flavor. Run with `--flavor <name>` and the flavor's entry point or `--dart-define-from-file`.
- Values passed with `--dart-define` are compiled into the app and can be read out of it. They are configuration, not secrets.

## The Dart and Flutter MCP server (opt-in)

```sh
claude mcp add --transport stdio dart -- dart mcp-server
```

- Gives the agent analyzer results, pub search, and for a running debug or profile app: run-time errors, the widget tree, hot reload.
- With fvm, pass the project's SDK: `dart mcp-server --flutter-sdk .fvm/flutter_sdk`.
- It is marked experimental, its tool names have changed between Dart releases, and on recent SDKs the command fetches the server package from pub.dev rather than using a bundled copy. Review that against your policy before enabling it for a team.

## Inside Claude Code's sandbox (tested with Flutter 3.44)

`flutter analyze` and `flutter test` run sandboxed when the sandbox may write the Flutter SDK's own cache, `~/.pub-cache`, `~/.dartServer`, `~/.config/flutter`, `~/.flutter` and `~/.dart-tool`, and `network.allowLocalBinding` is on (the test runner opens a localhost socket). Without those the tool fails before analysing anything. `flutter build` for iOS or Android calls Xcode or Gradle and inherits their limits. Settings are in the toolkit's `docs/03-setup-and-validation.md`.
