# React Native: upgrades, the New Architecture, and APIs that are gone

Every upgrade here goes through `mobile-core:migrate`: inventory, small slices, a check after each. Facts checked 2026-10-13 against the React Native release posts, the Expo changelog and the libraries' own migration guides.

## How to upgrade

- **Expo**: one SDK version at a time. `npx expo install expo@^<next> --fix`, then `npx expo-doctor`, read that SDK's changelog for breaking changes, regenerate the native folders (or `npx pod-install` if they are committed), and rebuild the development build. Skipping an SDK skips its migration notes.
- **Bare**: the Upgrade Helper shows the file-by-file diff between two React Native versions. Bump `react-native` and `react` together to the pair that release pins, apply the template changes to `ios/`, `android/` and the config files, then fix the app. New bare projects come from `npx @react-native-community/cli@latest init`.
- Upgrade libraries with native code in the same change as the React Native version they require, not before.
- Do not combine an upgrade with feature work. One version step per change, with a build on both platforms and the test suite.

## The New Architecture

- It has been the default since 0.76 and the only architecture since 0.82. Legacy code is being removed release by release: Android legacy classes went in 0.84 and 0.85, and iOS builds leave the legacy code out by default from 0.84.
- A project still on 0.81 or Expo SDK 54 or earlier can be on the old architecture. Moving it is a migration of its own: first every native dependency needs a New Architecture release.
- Old native modules and views still load through an **interop layer**. It has limits (no custom shadow nodes, no concurrent features) and 0.88 adds flags to switch it off. New native code is written as a Turbo Native Module or a Fabric component (`native.md`).
- In JavaScript, `UIManager` view-creation calls log that they are unavailable; `UIManager.measure*` is deprecated in favour of methods on the ref; `ref.measureLayout` needs a ref, not a numeric handle. `setNativeProps` and `findNodeHandle` still exist, but do not write new code on them.

## Removed and renamed, by version

Check the project's version before "fixing" code that still works there.

| Gone or deprecated | Since | Use instead |
|---|---|---|
| Remote JS debugging | 0.79 | React Native DevTools |
| Deep imports `react-native/Libraries/...` | deprecated 0.80, type errors by default in 0.87 | the public `react-native` exports |
| Core `SafeAreaView` | deprecated 0.81 | `react-native-safe-area-context` |
| JavaScriptCore in core | removed 0.81 | Hermes |
| `newArchEnabled=false` | ignored from 0.82 | nothing: it cannot be turned off |
| `StyleSheet.absoluteFillObject` | removed 0.85 | `StyleSheet.absoluteFill` |
| `preset: 'react-native'` in Jest | moved 0.85, shim gone 0.87 | `@react-native/jest-preset` |
| `InteractionManager` | removed 0.87 | split long tasks into smaller ones and schedule them with `requestIdleCallback` |
| StatusBar `backgroundColor` and `translucent`, Modal `animated` | removed 0.87 | edge-to-edge layout; Modal `animationType` |
| `NativeMethods` types | removed 0.87 | `HostInstance` |
| `react-native init` | left core in 2024 | `npx @react-native-community/cli init` or Expo |

Since 0.82 an unhandled promise rejection is reported through `console.error`: errors that were always there start to show after that upgrade.

## Expo SDK changes that break code

- **SDK 55**: the old architecture removed; `expo-av` gone from Expo Go (use `expo-video` and `expo-audio`); Expo Router's major version now equals the SDK's.
- **SDK 56**: an Expo Router app may not import `@react-navigation/*`; use `expo-router/react-navigation` and the `expo-router/js-*` entry points (a codemod exists). `expo/fetch` became the global `fetch`. `copy` and `move` in `expo-file-system` are async. Hermes V1 is the default.
- **SDK 57**: `prebuild` is clean by default. Early 57 releases had a Hermes V1 memory regression: use 57.0.9 or later.
- **SDK 58 (beta)**: R8 on by default in release builds, the iOS scene life cycle, and each CLI command sets `NODE_ENV` itself, so `.env.test` or `.env.staging` files are no longer picked up the old way.

## Library major versions that changed their API

| Library | Change |
|---|---|
| Reanimated 4 | New Architecture only; needs `react-native-worklets` with its Babel plugin listed last; `runOnJS` and `runOnUI` became `scheduleOnRN` and `scheduleOnUI`; `useAnimatedGestureHandler` is gone. Each 4.x release supports a window of React Native versions |
| Gesture Handler 3 | hook-based gestures; the `Gesture.X()` builders are the old style |
| FlashList 2 | New Architecture only; `estimatedItemSize` is gone; `MasonryFlashList` became the `masonry` prop |
| AsyncStorage 3 | instances from `createAsyncStorage(name)`; callbacks, `merge` and the hook removed. Expo SDK 57 still pins 2.x |
| MMKV 4 | a Nitro Module: `createMMKV()` instead of `new MMKV()`, `.remove()` instead of `.delete()` |
| React Navigation 7 | `navigate` no longer goes back to an existing screen (`popTo` does); nested screens need `navigate(parent, { screen })`. Version 8 is still alpha |
| React Native Testing Library 14 | `render`, `fireEvent` and `act` are async; `test-renderer` replaces `react-test-renderer`; needs React 19 |
| Jotai 3 | ESM only; `atomFamily` moved to `jotai-family` |
| Zustand 5 | a selector that returns a new object each time loops: wrap it with `useShallow` |

## Older code you will meet

- **Class components and higher-order components** work. Convert one only when the task is that conversion, and then one component per change with its tests.
- **Redux without Redux Toolkit**, `connect`, sagas: follow the file. Moving to Redux Toolkit is slice by slice.
- **`PropTypes` checks and string refs** are gone in React 19: remove them when the project moves to it.
- **CodePush**: App Center was retired in March 2025 and the CodePush repositories are archived. A project that still depends on it has to move (`release.md`).
