---
paths:
  - "**/*.{ts,tsx,js,jsx}"
  - "**/app.json"
  - "**/app.config.{js,ts}"
  - "**/eas.json"
  - "**/metro.config.{js,cjs,mjs}"
  - "**/babel.config.{js,cjs}"
  - "**/package.json"
---

# React Native rules

Facts first: the session-start profile lists the `react-native` and Expo SDK versions, whether `ios/` and `android/` are generated, the package manager, and the state, navigation and storage libraries. React Native removes APIs in most releases: read the installed versions before writing an API from memory.

- **Generated native folders are not edited.** If the profile says `ios/` and `android/` come from `expo prebuild`, change `app.json` / `app.config.*` or a config plugin. In a project that keeps them in git they are ordinary source.
- **Dependencies the project's way.** `npx expo install <package>` in an Expo project, and the package manager whose lockfile is here. Write code for the major version that is installed, which is often older than npm's latest. A package with native code needs a new build, not a reload.
- **Match the code you are in.** Keep the state library, the navigation library and the component style already in use. No second store or router for one screen. In an Expo Router app on SDK 56 or later, never import `@react-navigation/*`.
- **Server data lives in the query cache; client state in the store or the component.** Do not copy fetched data into a store.
- **No logic in components.** A component renders props and raises events. Rules, validation, formatting decisions and data access live in hooks, the store or the query layer. Split a screen into a part that wires data and a part that takes plain props; stories and tests use the second. Colours and type come from the project's theme.
- **Previews.** If the project has Storybook, every new or changed component gets one story per state that changes what is drawn (empty, loading, error, the longest text), with fixture props. Do not add Storybook inside another task.
- **New Architecture only** from React Native 0.82. No new bridge modules, no `NativeModules.X` for new code, no advice to turn it off.
- **Removed APIs models still write:** `InteractionManager`, `StyleSheet.absoluteFillObject`, core `SafeAreaView`, StatusBar `backgroundColor`, deep imports from `react-native/Libraries`, `preset: 'react-native'` in Jest. Check the version table in the skill before using or "fixing" one.
- **Stored data.** A persisted store or a key-value shape that changes needs a version and a migration; a SQLite change needs a migration step. Tokens go in secure storage, never AsyncStorage.
- **Nothing secret in the bundle.** `EXPO_PUBLIC_*`, app config `extra` and anything imported by JavaScript can be read from the shipped app.
- **Types and lint are not silenced.** No new `any`, `@ts-ignore`, `@ts-expect-error` or `eslint-disable` to get past an error.
- **Tests match the installed library.** React Native Testing Library 14 awaits `render` and `fireEvent`; 13 does not.
- **A change that needs native code ships as a store build**, not as an over-the-air update.
- **Accessibility is part of done** for a UI change: `accessibilityLabel` and `accessibilityRole` on custom touchables, text that scales, touch targets of at least 44 by 44 points.

Detail is in the `mobile-react-native:react-native` skill. Load the reference for the task: `build.md` (Expo and bare setup, prebuild, build failures, version and store requirements), `legacy.md` (upgrades, the New Architecture, removed APIs, library major versions), `architecture.md` (structure, state, navigation, deep links), `native.md` (native modules, config plugins), `persistence.md`, `testing.md`, `performance.md`, `release.md` (over-the-air updates, secrets, source maps, submission).
