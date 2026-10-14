---
name: react-native
description: React Native engineering reference for Expo and bare projects in TypeScript or JavaScript, including older ones. Covers Expo prebuild and generated native folders, Metro, CocoaPods and Gradle failures, upgrades and the New Architecture, removed and deprecated APIs, state and navigation structure (Redux Toolkit, Zustand, TanStack Query, React Navigation, Expo Router), native modules and config plugins, AsyncStorage, MMKV and SQLite migrations, Jest and end-to-end tests, list and animation performance, and release with over-the-air updates. Use when writing, reviewing, debugging, upgrading or building React Native or Expo code, or when a Metro, Jest, pod or Gradle step of such a project fails.
---

# React Native engineering

Read the project facts first: the session-start profile, or `mobile detect`. The `react-native` and Expo SDK versions, whether `ios/` and `android/` are generated, the package manager, and the state, navigation and storage libraries. React Native ships a minor version every two months and removes APIs in most of them, so advice from memory is often for a different version.

## Working in this codebase

- **Read the installed versions; do not recall them.** `package.json` and the lockfile are the facts. For an Expo project read the docs for its SDK version, not "latest".
- **Is the native code generated?** If the profile says `ios/` and `android/` come from `expo prebuild`, never edit them: change `app.json` / `app.config.*` or a config plugin. The edit guard refuses otherwise. In a project that keeps them in git they are ordinary source.
- **Add dependencies the project's way.** In an Expo project use `npx expo install <package>`, which picks the version that matches the SDK; `npm install <package>` often picks a newer major with a different API. Use the package manager in the profile and never mix lockfiles.
- **Match the code you are in.** Class components stay class components, the existing state library stays the state library, unless the task is that migration (`mobile-core:migrate`).
- **Components draw; they do not decide.** Logic goes to hooks, the store or the query layer. If the project has Storybook, each new or changed component gets one story per state it draws.
- Check with `mobile verify`: the type check, lint on changed files, and Jest.

## Load the reference that matches the task

| Task | Reference |
|---|---|
| Expo or bare setup, prebuild, development builds, Metro, pod and Gradle failures, version and store requirements | [references/build.md](references/build.md) |
| Upgrading React Native or the Expo SDK, the New Architecture, removed and renamed APIs, library major versions | [references/legacy.md](references/legacy.md) |
| Project structure, client and server state, React Navigation and Expo Router, deep links | [references/architecture.md](references/architecture.md) |
| Native modules and views, Codegen specs, Expo modules, config plugins, the old-module interop layer | [references/native.md](references/native.md) |
| AsyncStorage, MMKV, SQLite, secure storage, migrating stored data | [references/persistence.md](references/persistence.md) |
| Jest presets, React Native Testing Library, mocking native modules, Maestro and Detox | [references/testing.md](references/testing.md) |
| Lists, re-renders and the React Compiler, animations and gestures, startup, profiling | [references/performance.md](references/performance.md) |
| Over-the-air updates and what the stores allow, secrets, source maps, store submission | [references/release.md](references/release.md) |

## Specialist skills

If installed, use these for their speciality and this skill for everything around it: Expo's official plugin (`expo`: router, upgrades, EAS, modules), Callstack's `react-native-best-practices` (performance) and `upgrading-react-native`, Software Mansion's skill (Reanimated, Gesture Handler), and the React Navigation migration skills.

## Mistakes to expect from yourself

1. An API that was removed: `InteractionManager`, `StyleSheet.absoluteFillObject`, core `SafeAreaView`, StatusBar `backgroundColor`, `preset: 'react-native'` in Jest. `legacy.md` has the list with versions.
2. Editing `ios/` or `android/` in a project that generates them, or telling the user to "eject".
3. `npm install` of the newest version of a library in an Expo project, then code written for a different major than the one installed.
4. Advice for the old architecture: `newArchEnabled=false` (ignored since 0.82), bridge modules, `NativeModules.X` for new code.
5. Importing `@react-navigation/*` in an Expo Router app on SDK 56 or later.
6. Tests written synchronously for React Native Testing Library 14, where `render` and `fireEvent` are awaited.
7. A secret in `EXPO_PUBLIC_*`, in app config, or anywhere else in the JavaScript bundle.
8. Shipping a change that needs new native code through an over-the-air update.
9. Adding `useMemo` and `useCallback` everywhere in a project that runs the React Compiler, or stripping the ones that are there.
10. Judging performance in a debug build, or in Expo Go.
