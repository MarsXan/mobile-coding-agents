# React Native: setup, builds and build failures

Facts checked 2026-10-13 against reactnative.dev, docs.expo.dev, the Expo changelog and the npm registry. Versions move every few weeks: confirm against the project's own `package.json` and the linked pages.

## Where things stand

| | Current (October 2026) | Notes |
|---|---|---|
| React Native | 0.87 stable; a minor about every 8 weeks; the latest three minors are supported | the repository moved to `github.com/react/react-native` |
| Expo SDK | 57 (React Native 0.86); SDK 58 in beta | one SDK tracks one React Native minor and lives about a year |
| Architecture | the New Architecture is the only one since 0.82 | `newArchEnabled=false` is ignored; SDK 55 removed the setting |
| JavaScript engine | Hermes V1 by default since 0.84 (Expo SDK 56) | JavaScriptCore left core in 0.81 |
| Minimum OS | iOS 15.1 and Android API 24 for React Native; Expo SDK 56 and later needs iOS 16.4 | |
| Tools for 0.87 | Node 22.13 or later, Kotlin 2 or later, JDK 17, first AGP 9 support | Expo SDK 56 and later needs Xcode 26.4 |

reactnative.dev recommends starting new apps with a framework and names Expo. Apps without one stay supported.

## Expo: generated native folders

- With Continuous Native Generation the app config (`app.json` or `app.config.*`) and config plugins are the source; `npx expo prebuild` writes `ios/` and `android/` from them. New projects keep those folders out of git.
- **Since SDK 57 `npx expo prebuild` deletes and regenerates both folders by default** (`--no-clean` keeps them). A hand edit there is gone on the next run.
- To change native settings: an app-config key, an existing config plugin's options (`expo-build-properties` for SDK levels, deployment target, Gradle and Podfile properties), or a small plugin of your own. `patch-project` stores diffs of hand edits in `cng-patches/` and re-applies them: use it only where the project already does.
- `expo run:ios` and `expo run:android` prebuild only when the folders are missing. After changing app config or adding a native dependency, run prebuild again.
- If `ios/` and `android/` are committed, the project manages them by hand: do not run prebuild there, it can overwrite the customisations, and EAS Build skips it.
- "Ejecting", "managed versus bare" and the global `expo-cli` are old vocabulary. Use `npx expo`.

## Expo Go and development builds

- Expo Go contains a fixed set of native modules. A library with native code that is not in it (MMKV, op-sqlite, most payment and maps SDKs) needs a **development build**: `expo-dev-client` plus a build with `eas build` or `expo run`.
- Expo's own docs call Expo Go a playground, not the way to build an app you will ship. Do not diagnose native problems or measure performance in it.
- Adding or upgrading a native dependency means a new development build, not just a reload.

## Dependencies

- Expo: `npx expo install <package>` picks the version tested with the SDK, and `npx expo install --check` (or `--fix`) and `npx expo-doctor` report mismatches. The pinned version is often an older major than npm's latest: on SDK 57, AsyncStorage 2.x, Gesture Handler 2.x, Reanimated 4.5. Write code for the installed major.
- One package manager per repository: the one whose lockfile is there.
- `react` must be the version the React Native release pins, not npm's latest.
- After changing native dependencies in a project with committed native folders: `npx pod-install` for iOS, and a Gradle sync or build for Android.

## Failures and their usual cause

| Symptom | Cause |
|---|---|
| A native module is `null` or "could not be found" at run time | the binary was built before the dependency was added: rebuild the development build; in Expo Go the module does not exist |
| Works in debug, fails in release | code that relies on dev-only behaviour, an R8 rule missing for a reflective library (Expo SDK 58 turns R8 on by default), or an environment variable that is not inlined in release |
| `pod install` fails after an upgrade | stale `Pods/` and lockfile state from the old version, or a pod not built for the New Architecture. Read the first error, not the last |
| Type errors on `react-native/Libraries/...` imports | deep imports: deprecated in 0.80 and type errors by default in 0.87. Import from `react-native` |
| Jest cannot find its preset | it moved: `@react-native/jest-preset` since 0.85 (`testing.md`) |
| Metro resolves the wrong file or a duplicate React | two copies of a package in a monorepo, or a `resolveRequest` hook that newer Metro now honours. Check the lockfile before the Metro config |
| A stale bundle after config changes | Metro's cache: `npx expo start --clear` or `npx react-native start --reset-cache`. Do this before deeper theories, not instead of reading the error |
| Android build breaks after a Kotlin, Gradle or AGP bump | the React Native Gradle plugin supports a window of versions per release: use the versions of that release's template |

## Platform dates that affect a build

- Google Play needs target API 36 for new apps and updates since 31 August 2026, and 16 KB page-size support for apps that target API 35 or later.
- App Store Connect uploads need Xcode 26 with the iOS 26 SDK since 28 April 2026.
- The CocoaPods registry stops accepting new versions on 2 December 2026; existing pods keep installing. React Native's Swift Package Manager support is experimental in 0.87.
- The iOS 27 SDK needs the scene-based life cycle: Expo SDK 58 and React Native 0.88 add `SceneDelegate` support, and custom `AppDelegate` code has to move.
