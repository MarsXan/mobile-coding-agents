---
name: ios
description: iOS engineering reference for Swift, SwiftUI, UIKit and Objective-C codebases, including legacy ones. Covers xcodebuild, signing and package-manager failures, UIKit lifecycle and memory, Objective-C interop, adding SwiftUI to UIKit apps, Swift concurrency and Swift 6 migration, Core Data and SwiftData migrations, architecture patterns (MVVM, coordinators, VIPER, TCA), dependency injection and modules, XCTest and Swift Testing, Instruments-based performance work, privacy manifests, accessibility and App Store requirements. Use when writing, reviewing, debugging, migrating or building iOS code, or when an Xcode build, test or archive fails.
---

# iOS engineering

Read the project facts first: the session-start profile, or `mobile detect`. Minimum iOS version, Swift language mode, strict-concurrency level, default actor isolation, package managers, and whether Objective-C is present. Most wrong iOS advice is right advice for a different configuration.

## Working in this codebase

- Match the framework and style of the file you are in. Modernise only when that is the task (`mobile-core:safe-change`, `mobile-core:migrate`).
- Every view gets one named `#Preview` per state it draws, from fixture data, and holds no logic: it draws state and reports what the user did. `@Previewable` and UIKit previews need iOS 17; below that minimum, mark the preview `@available(iOS 17, *)`.
- Check with `mobile verify`. For raw `xcodebuild` commands and what their failures mean, read `references/build.md`.
- Read the toolchain; do not recall it: `xcodebuild -version`, `swift --version`.
- Apple's documentation is available as Markdown: add `.md` to a `developer.apple.com/documentation/...` URL. Xcode also ships Apple-written guides for recent APIs in `/Applications/Xcode.app/Contents/PlugIns/IDEIntelligenceChat.framework/Versions/A/Resources/AdditionalDocumentation/`. Read the relevant one before using an API from the last two releases.

## Load the reference that matches the task

| Task | Reference |
|---|---|
| Build, test, archive, signing, SwiftPM or CocoaPods failures, project-file edits, simulator control | [references/build.md](references/build.md) |
| UIKit lifecycle and memory, Objective-C interop, SwiftUI inside UIKit, scene lifecycle, CocoaPods to SwiftPM, `ObservableObject` to `@Observable` | [references/legacy.md](references/legacy.md) |
| Working inside MVVM, coordinators, VIPER, TCA or layered code; `@Observable` ownership; SwiftUI navigation and routers; choosing a pattern for new code | [references/architecture.md](references/architecture.md) |
| Dependency injection (initialisers, environment, Factory, swift-dependencies, Swinject), Swift packages as modules, generated projects, build time | [references/modules.md](references/modules.md) |
| async/await, actors, `Sendable`, main-actor isolation, Swift 6 language mode, GCD and Combine interop | [references/concurrency.md](references/concurrency.md) |
| Core Data, SwiftData, `UserDefaults`, Keychain, files, schema migration | [references/persistence.md](references/persistence.md) |
| XCTest, Swift Testing, UI tests, snapshot tests, flaky tests | [references/testing.md](references/testing.md) |
| Launch time, hangs, scrolling, memory, energy, app size | [references/performance.md](references/performance.md) |
| Privacy manifest, permissions, security, accessibility, localisation, App Store requirements | [references/release.md](references/release.md) |

## Specialist skills

If one of these is installed, use it for its speciality and this skill for everything around it: `swiftui-pro` (SwiftUI API review), `swift-concurrency` (deep concurrency migration), `core-data-expert` (Core Data).

## Mistakes to expect from yourself

1. Proposing an API that does not exist on the project's minimum iOS version.
2. Rewriting UIKit into SwiftUI, or callbacks into async/await, while fixing something else.
3. Silencing a concurrency diagnostic with `@unchecked Sendable`, `nonisolated(unsafe)`, `@preconcurrency` or a `Task { @MainActor in }` wrapper instead of fixing the isolation.
4. Forgetting that a new file must be added to its target in a project with explicit file references, or rewriting large parts of the project file.
5. Editing a shipped Core Data model version in place.
6. Treating a passing simulator run as proof for a device: signing, entitlements, push, camera, keychain access groups and performance all differ.
7. Stating Swift, Xcode or iOS version facts from memory.
8. "Fixing" a build by deleting DerivedData, `Package.resolved` or `Podfile.lock` without reading the error.
9. Adding a permission request without its `Info.plist` purpose string, which crashes at the first access.
10. Adding `[weak self]` or main-thread hops by reflex. Each changes behaviour; know why it is needed.
