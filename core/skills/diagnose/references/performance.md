# Measuring performance

## Rules that make a number trustworthy

- **Release-like build.** iOS: Release configuration. Android: a non-debuggable build with R8 on. Flutter: `--profile` or `--release`. Never debug: debug builds are several times slower and differently shaped.
- **Real device**, and on Android a mid-range or low-end one. Simulators and emulators have desktop CPUs and no thermal limits.
- **Same scenario, same data, several runs.** Report the median and the spread. One run is an anecdote.
- **Change one thing** between measurements.
- **Name the user-visible metric** before optimising: what the user waits for or sees stutter.

## What to measure, and with what

| Complaint | Metric | iOS | Android | Flutter |
|---|---|---|---|---|
| Slow to open | cold start to first frame, and to usable | Instruments *App Launch*; `XCTApplicationLaunchMetric` in a performance test; MetricKit launch histograms | `adb shell am start -W -n <pkg>/<activity>` (`TotalTime`); Macrobenchmark `StartupTimingMetric` | `flutter run --profile --trace-startup` writes `build/start_up_info.json` |
| Stutter while scrolling or animating | frame time against the display budget (16.7 ms at 60 Hz, 8.3 ms at 120 Hz); share of slow frames | Instruments *Animation Hitches*; `XCTOSSignpostMetric` scroll metrics | Macrobenchmark `FrameTimingMetric`; JankStats; Perfetto | DevTools performance view: UI thread against raster thread per frame |
| Freezes | main-thread stalls | Instruments *Hangs* (flags stalls from 250 ms); MetricKit hang diagnostics | ANR traces (about 5 s without handling input); `StrictMode` in debug builds | long frames on the UI thread in DevTools; synchronous work in `build` or in an event handler |
| Memory grows, app is killed in background | footprint over a repeated flow; leaked objects | Xcode memory graph; Instruments *Allocations* and *Leaks*; `XCTMemoryMetric` | Android Studio memory profiler; LeakCanary in debug builds; `adb shell dumpsys meminfo <pkg>` | DevTools memory view; image cache size |
| Battery | CPU wake-ups, network and location use in background | Xcode energy gauge; MetricKit | `adb shell dumpsys batterystats`; WorkManager constraints; wake locks | platform tools above |
| App too large | download and install size per device | App Thinning Size Report from an export with thinning enabled | `bundletool build-apks` then `bundletool get-size total`; `apkanalyzer apk download-size` | `flutter build <apk|appbundle|ipa> --analyze-size` |
| Slow network screens | request count, payload size, sequencing | Instruments *Network*; a proxy tool | Android Studio Network Inspector; a proxy tool | DevTools network view |

## Where the time usually goes

- **Startup.** Eager initialisation of SDKs and singletons, synchronous disk or network before the first frame, large dependency graphs built up front, heavy first-screen layout. Defer everything the first frame does not need.
- **Scrolling.** Work in the per-item render path (image decoding, date and number formatting, layout passes, allocation), unstable identities that defeat diffing, synchronous I/O, shadows and clipping on many layers.
- **Freezes.** Disk or database access, JSON parsing, image processing or lock contention on the main thread.
- **Memory.** Full-resolution images held for small views, caches without limits, retain cycles (closures capturing `self`, listeners never removed, a `Context` held past its lifecycle).
- **Size.** Unused assets and localisations, duplicated dependencies, uncompressed media, debug symbols or unshrunk code in the release artefact.

## Reporting

State the scenario, device, OS, build type and number of runs, then before and after. Example: "Cold start to first frame, Pixel 6a, Android 15, release with baseline profile, 10 runs: median 1,240 ms before, 870 ms after."
