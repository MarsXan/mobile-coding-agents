# iOS: performance

Method and metrics are in `mobile-core:diagnose` (`references/performance.md`): measure on a Release build on a device, several runs, before and after. This file is where to look and what usually causes it on iOS.

## Launch

- **Measure**: Instruments *App Launch*; `XCTApplicationLaunchMetric` in a performance test; MetricKit launch data from the field.
- The system may prewarm the process before the user taps. Measure to the first frame, not from process start, and do not assume protected data is readable before `didFinishLaunching`.
- **Causes**: many dynamic frameworks (prefer static linking or mergeable libraries); static initialisers and Objective-C `+load`; SDKs initialised eagerly in `didFinishLaunching`; synchronous disk, keychain or network work before the first frame; building the whole dependency graph up front; a heavy first screen.
- **Fix pattern**: only what the first frame needs runs before it. Everything else is lazy or starts after the first frame is on screen.

## Hangs

- **Measure**: Instruments *Hangs* and *Time Profiler*; Xcode's Thread Performance Checker; MetricKit hang diagnostics from the field.
- **Causes**: file, database or keychain access on the main thread; decoding large JSON; image decoding at draw time; Core Data fetches on `viewContext`; `DispatchQueue.main.sync`; waiting on a lock or semaphore; layout invalidated in a loop.
- **Images**: `UIImage(data:)` decodes when first drawn, on the main thread. Decode off the main thread with `preparingForDisplay()` or `preparingThumbnail(of:)` (iOS 15+), and downsample to the size shown.

## Scrolling and animation

- **Measure**: Instruments *Animation Hitches*; the SwiftUI instrument for view-update causes; `XCTOSSignpostMetric` scroll metrics in a performance test.
- **UIKit**: cell configuration must be cheap and synchronous. Prefetch data and images. Give shadows a `shadowPath`. Avoid masks and clipped corner radii on many layers.
- **SwiftUI**:
  - Identity must be stable. Never `id: \.self` on values that repeat or change, never a `UUID()` created in `body`.
  - `body` is cheap: no sorting, filtering, formatting or object creation. Compute outside and store.
  - Long content uses `List` or lazy stacks.
  - Split views so a state change invalidates the smallest subtree. `@Observable` tracks per property; `ObservableObject` invalidates every observer.
  - `let _ = Self._printChanges()` in a debug build shows why a view re-evaluated.

## Memory

- **Measure**: Xcode's memory graph for cycles; Instruments *Allocations* with generations (mark, repeat a flow five times, mark: persistent growth is a leak or an unbounded cache); `leaks` and `vmmap` on a saved `.memgraph`.
- A decoded image costs width x height x 4 bytes whatever the file size. Downsample to display size.
- Use `NSCache` (purged under pressure) rather than a dictionary for caches.
- Extensions (widgets, notification service, share) have far lower limits than the app and are killed without a crash report.
- Cycle checklist is in `legacy.md` under "Memory".

## Energy and background work

- No polling timers. Use push, `BGTaskScheduler`, or a background `URLSession`.
- Ask for the least location accuracy that works and stop updates when done.
- Batch network requests; every wake of the radio costs.

## App size

- **Measure**: an export with thinning enabled produces *App Thinning Size Report.txt* with per-device download and install sizes.
- **Causes**: assets outside asset catalogs or at unused scales; unused code and resources; duplicated dependencies (the same library linked into the app and an extension); debug symbols in the product; large bundled media.
- Check size after adding a dependency, as part of the same change.

## Command line

```sh
xcrun xctrace list templates
xcrun xctrace record --template 'Time Profiler' --launch -- /path/App.app --output out.trace
xcrun xctrace export --input out.trace --toc
```

Performance tests assert a budget and fail when it regresses: `measure(metrics: [XCTClockMetric(), XCTMemoryMetric()]) { ... }` with a stored baseline. Mark intervals with `OSSignposter` so they appear in Instruments and can be measured with `XCTOSSignpostMetric`.
