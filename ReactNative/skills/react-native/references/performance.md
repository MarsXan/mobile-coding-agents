# React Native: performance

Measure first, in a release build, on a real mid-range Android device. `mobile-core:diagnose` has the method; this file has what is specific to React Native. Facts checked 2026-10-13 against reactnative.dev and the libraries' documentation.

## Where to look

| Symptom | Tool |
|---|---|
| Slow renders, too many re-renders | React Native DevTools: the React Profiler and the Performance panel (available from 0.83) |
| Memory growth | DevTools memory heap snapshots; Xcode Instruments and Android Studio Profiler for the native side |
| Dropped frames while scrolling or animating | the DevTools Performance panel for the JavaScript side; Perfetto (Android) or Instruments (iOS) for native frames |
| Slow start | native start-up tools (Instruments App Launch, Android Studio / Macrobenchmark) plus the bundle analysis below |
| Bundle size | Expo Atlas (`EXPO_ATLAS=true npx expo start --no-dev`), or `react-native bundle --sourcemap-output` with source-map-explorer |

Debug builds run unoptimised JavaScript with extra checks, and Expo Go is not your app. Numbers from either mean nothing. Android has a `debugOptimized` build type since 0.82 for faster development runs.

## Re-renders and the React Compiler

- The React Compiler is stable (1.0). Expo enables it with `experiments.reactCompiler` and its SDK 57 template turns it on; the bare community template does not include it. **Check whether this project runs it** before giving memoization advice.
- With the compiler on: write plain components. Do not add `useMemo`, `useCallback` and `React.memo` by reflex, and **do not remove existing ones in bulk either**: React's guidance is to leave them, because removing them can change what the compiler produces.
- Without it: memoize where the profiler shows a cost. A component that re-renders is not a problem by itself; a slow one is.
- The usual real causes: a new object, array or function created on every render and passed to a list item or a context value; one context that holds everything, so every consumer re-renders; a store selector that returns a new object each time (in Zustand 5 that is an infinite loop: use `useShallow`).
- Keep state as low in the tree as it can live. State at the screen root re-renders the screen.

## Lists

- For long or heavy lists use FlashList. **Version 2** needs the New Architecture and dropped `estimatedItemSize`; do not carry v1 props or advice into it.
- FlashList recycles rows: an item component keeps its state when it is reused for another item. Reset local state when the item changes, do not set a `key` inside the item, and give mixed row kinds a `getItemType`.
- With `FlatList`: a stable `keyExtractor`, `renderItem` defined outside the JSX or with `useCallback`, memoized rows, and `getItemLayout` when rows have a fixed height. Tune `initialNumToRender`, `maxToRenderPerBatch` and `windowSize` only after measuring.
- Images in rows: fixed dimensions, cached, sized to the display. An unsized remote image causes layout on every load.
- Never nest a vertical virtualized list inside a `ScrollView` of the same direction: it renders every row.

## Animations and gestures

- Animations that must not drop frames run on the UI thread: Reanimated worklets, or `Animated` with `useNativeDriver: true` for transforms and opacity.
- **Reanimated 4** (New Architecture only): worklets live in `react-native-worklets`, whose Babel plugin goes last; `runOnJS` and `runOnUI` are now `scheduleOnRN` and `scheduleOnUI`. Each Reanimated release supports a window of React Native versions and a matching worklets version: check the compatibility table before bumping either.
- Do not read a shared value's `.value` during render, and do not destructure a shared value; read it inside a worklet or an animated style.
- Use Gesture Handler for gestures, not `PanResponder`, and do not mix its gestures with React Native's own touch handlers on the same view. Version 3 has a hook-based API; follow the major the project has.
- Animate `transform` and `opacity`. Animating layout properties (`width`, `height`, `top`) runs layout on every frame.

## Start-up

- Hermes compiles JavaScript to bytecode at build time, so parse time is not the cost; **running** module top-level code is. Keep work out of module scope, and load heavy screens and libraries lazily (`React.lazy`, inline `require`).
- Do not block the first render on storage reads, remote config or fonts that can arrive after it.
- Each native module that initialises at launch costs time on the main thread. Remove the unused ones: a dependency you no longer import is still linked.
- Measure cold start on a device, from tap to first usable screen, before and after.

## Network and data

- Wire TanStack Query's `onlineManager` and `focusManager` (see `architecture.md`); set sensible `staleTime` so a screen does not refetch on every focus.
- Batch and paginate. Rendering 1,000 rows from one response is a list problem and a memory problem at once.
- Strip `console.*` calls from release builds (the Babel plugin for it); logging large objects is slow even with nobody reading.

## Mistakes to expect from yourself

1. Proposing a fix before measuring, or measuring in a debug build.
2. Wrapping everything in `useMemo` and `useCallback`, or stripping them, without knowing whether the compiler runs.
3. FlashList v1 props in a v2 project; a `key` inside a recycled row.
4. Reanimated 3 function names in a Reanimated 4 project.
5. A `FlatList` inside a `ScrollView`.
6. Blaming JavaScript for a slowness that is native start-up or an oversized image.
