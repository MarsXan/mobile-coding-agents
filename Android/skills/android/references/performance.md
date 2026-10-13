# Android: performance

Method and metrics are in `mobile-core:diagnose` (`references/performance.md`): measure a release build with R8 on a real mid-range or low-end device, several runs, before and after. This file is where to look and what usually causes it on Android.

## Startup

- **Measure**: `adb shell am force-stop <pkg>` then `adb shell am start -S -W -n <pkg>/<activity>` (`TotalTime`); Macrobenchmark `StartupTimingMetric` for time to initial and full display; call `reportFullyDrawn()` when content is usable.
- **Causes**: work in `Application.onCreate`; libraries that initialise themselves through content providers; building the whole dependency graph up front; synchronous preference or disk reads; a heavy first layout.
- **Fixes**: initialise lazily or after the first frame; consolidate provider-based initialisers with the App Startup library; ship a **Baseline Profile** (and a startup profile) generated with Macrobenchmark, which precompiles the startup and hot paths.

## Jank

- **Measure**: Macrobenchmark `FrameTimingMetric`; `adb shell dumpsys gfxinfo <pkg> framestats`; a Perfetto trace with custom sections from `androidx.tracing`.
- **Views**: nested weights and deep hierarchies; work in `onBindViewHolder`, `onDraw` or `onMeasure`; images decoded at full size.
- **Compose**:
  - Measure in release. Debug Compose is far slower and misleads.
  - Lazy lists need stable `key`s and a `contentType`.
  - Read fast-changing state as late as possible: lambda modifiers (`Modifier.offset { }`, `graphicsLayer { }`) defer the read to layout or draw and skip recomposition.
  - `derivedStateOf` for state computed from frequently changing state; `remember` with keys for expensive computations.
  - No allocation or I/O in composition or in draw scopes. No writing to state that the same composition already read.
  - Stability rules depend on the compiler version. With strong skipping (default from Kotlin 2.0.20) unstable parameters are compared by instance. Use the Compose compiler reports and the Layout Inspector's recomposition counts before changing anything for "stability".

## ANR

- The main thread did not handle input for about five seconds, a `BroadcastReceiver` ran too long, or a foreground service did not call `startForeground` in time.
- **Causes**: disk or network on the main thread; a lock held by a background thread; a slow binder call into another process; a slow `ContentProvider`; a deadlock.
- Read the `main` thread's stack in the ANR trace first. `StrictMode` in debug builds catches most causes before release.

## Memory

- **Measure**: LeakCanary in debug builds reports leaks with the reference chain; the Android Studio memory profiler; `adb shell dumpsys meminfo <pkg>`.
- **Leaks**: an Activity, Fragment, View or its `Context` reachable from a singleton, a static field, a long-lived coroutine or callback; a view binding not cleared in `onDestroyView`; a listener never unregistered; a `Handler` with pending messages.
- **Size**: bitmaps decoded larger than shown (let the image library downsample to the view size); unbounded in-memory caches. Respond to `onTrimMemory`.

## App size

- **Measure**: `bundletool build-apks` then `bundletool get-size total`; `apkanalyzer apk download-size`; the APK Analyzer view.
- **Wins**: R8 with resource shrinking; an App Bundle so devices get only their ABI, density and language; removing unused dependencies and resources; vector or WebP assets; native libraries stored uncompressed and page-aligned.
- Check size after adding a dependency, in the same change.

## Battery

No polling. Batch network work, use WorkManager constraints, release wake locks, request the least location accuracy that works, and stop work when the UI is not visible.

## Field data

Google Play's Android vitals report crash rate, ANR rate, startup time and slow frames from real devices, and flag an app that exceeds the bad-behaviour thresholds. A lab measurement that improves and a vital that does not means the lab scenario is not what users do.
