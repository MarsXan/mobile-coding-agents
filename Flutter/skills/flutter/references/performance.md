# Flutter: performance

Method and metrics are in `mobile-core:diagnose` (`references/performance.md`). On Flutter that means **profile mode on a real device** (`flutter run --profile`). Debug mode runs a JIT with assertions and its numbers mean nothing.

## First question: which thread is over budget

DevTools' performance view shows two bars per frame.

- **UI thread** (your Dart code: build, layout, paint) is slow: too much work per frame.
- **Raster thread** (the GPU side) is slow: the scene is expensive to draw.

The fixes are different. Find out before changing anything.

## UI thread

- **Rebuilds too wide.** `setState` high in the tree, or a state object watched whole. Push state down, split large widgets into smaller widget classes, and select only what is needed (`context.select`, `BlocSelector`, `ref.watch(p.select(...))`).
- **Non-const widgets** rebuilt needlessly. Use `const` constructors.
- **Work in `build`.** Sorting, filtering, formatting, parsing. Compute when data changes, not when the frame is built.
- **Long lists built eagerly.** `ListView(children: [...])` and `Column` in a scroll view build everything. Use `ListView.builder` or slivers, with `itemExtent` or `prototypeItem` when rows are uniform, and a `ValueKey(id)` per item.
- **`shrinkWrap: true` on a nested list** builds every child. Use a `CustomScrollView` with slivers.
- **Expensive layout.** `IntrinsicHeight` and `IntrinsicWidth` lay children out twice.
- **Heavy synchronous work.** Move it to an isolate (`concurrency.md`).
- DevTools can track widget rebuild counts; use it to confirm which widget is rebuilding before optimising.

## Raster thread

- **`saveLayer`** is the usual cost: `Opacity` over a subtree, `ShaderMask`, `ColorFiltered`, `Clip.antiAliasWithSaveLayer`. Animate with `FadeTransition` or `AnimatedOpacity`, and apply opacity to the leaf rather than the group.
- **Large blurs and shadows**, heavy clipping, and overdraw.
- **Oversized images.** Decode at display size with `cacheWidth` and `cacheHeight` (or `ResizeImage`).
- `RepaintBoundary` isolates a subtree that repaints often from one that does not. Measure: a boundary in the wrong place costs memory for nothing.
- **Impeller** is the renderer on iOS and the default on current Android. The old shader warm-up advice (bundled SkSL) does not apply to it. If a rendering problem looks renderer-specific, confirm on a real device before changing code.

## Startup

- Measure: `flutter run --profile --trace-startup` writes `build/start_up_info.json`.
- The native splash stays until the first Flutter frame. Awaiting initialisation before `runApp` lengthens it. Show the first frame, then initialise what it does not need.

## Memory

- DevTools' memory view shows growth across a repeated flow.
- Usual causes: undisposed controllers and subscriptions (they retain whole widget states), an oversized image cache, images decoded at full resolution, lists that keep every item alive.

## App size

```sh
flutter build apk --analyze-size --target-platform android-arm64
flutter build appbundle --analyze-size
flutter build ipa --analyze-size
```

Each writes a breakdown that DevTools' app-size tool opens. `--split-debug-info` with `--obfuscate` reduces size and requires archiving the symbol files. Look at assets, fonts and the native libraries plugins bring. Check size after adding a dependency, in the same change.

## Guarding against regressions

An integration test can record frame timings for a scripted interaction (`binding.traceAction` or `watchPerformance`) and report average and percentile build and raster times. Run it on the same device in CI and compare with the stored result.
