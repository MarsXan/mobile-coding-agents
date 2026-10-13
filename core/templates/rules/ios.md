---
paths:
  - "**/*.swift"
  - "**/*.{m,mm,h}"
  - "**/*.{xib,storyboard,xcconfig,entitlements,xcprivacy}"
  - "**/Info.plist"
  - "**/Package.swift"
  - "**/Podfile"
  - "**/project.pbxproj"
---

# iOS rules

Facts first: the session-start profile lists this project's minimum iOS version, Swift language mode, strict-concurrency level, default actor isolation and package managers. They decide which advice applies. Read them before proposing an API or a concurrency fix.

- **Availability.** An API newer than the minimum iOS version needs `if #available` or `@available` and a real fallback. A warning-free build does not prove the API exists on the oldest supported OS.
- **Match the file you are in.** UIKit stays UIKit, Objective-C stays Objective-C, completion handlers stay completion handlers, unless the task is that migration. Suggest modernisation separately; do not apply it unasked.
- **Concurrency.** Fix the isolation; do not hide the diagnostic. No new `@unchecked Sendable`, `nonisolated(unsafe)`, `@preconcurrency`, `Task.detached` or `DispatchQueue.main.async` just to quiet the compiler. The correct fix depends on the language mode and default actor isolation in the profile.
- **UIKit lifecycle.** Nothing that needs final geometry in `viewDidLoad`. `[weak self]` in escaping closures a view controller owns or is owned by. Remove observers, invalidate timers, cancel tasks. UI work on the main actor only.
- **Stored data.** Never edit a shipped Core Data model version in place. SwiftData changes beyond an optional or defaulted property need a `VersionedSchema` and a migration plan. `UserDefaults` and Keychain keys and `Codable` shapes written to disk are a format.
- **Project file.** In a project with explicit file references, a new file must be added to its target. Make the smallest `project.pbxproj` edit and confirm with `xcodebuild -list`.
- **Capabilities.** A new permission needs its `NS…UsageDescription`, a denial path, and a privacy-manifest check (`PrivacyInfo.xcprivacy`, required-reason APIs).
- **Accessibility is part of done** for a UI change: labels on icon-only controls, Dynamic Type survives, 44-point targets, sensible VoiceOver order.

Detail is in the `mobile-ios:ios` skill. Load the reference for the task: `build.md` (xcodebuild, signing, SwiftPM and CocoaPods failures), `legacy.md` (UIKit, Objective-C interop, incremental SwiftUI, migrations), `architecture.md` (MVVM, coordinators, VIPER, TCA, navigation structure), `modules.md` (dependency injection, packages, generated projects), `concurrency.md`, `persistence.md`, `testing.md`, `performance.md`, `release.md` (privacy, accessibility, security, App Store requirements).
