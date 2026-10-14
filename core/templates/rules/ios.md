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
- **Names the compiler does not check.** Asset names, XIB and storyboard names, localization keys and reuse identifiers resolve at runtime, so a green build proves nothing about them. Before renaming or deleting one, search the whole tree for the exact, case-sensitive name.
- **Capabilities.** A new permission needs its `NS…UsageDescription`, a denial path, and a privacy-manifest check (`PrivacyInfo.xcprivacy`, required-reason APIs).
- **Every view has previews.** Each SwiftUI view, and each new UIKit view or view controller, gets one named `#Preview` per state that changes what is drawn: empty, loading, error, each enum case, both values of each flag, the longest text. Nothing else renders a view before someone launches the app; a wrong-looking screen still builds and passes its tests. Previews use fixture data, never a live service, and go where this project already keeps them. State a preview exercises is `@Previewable @State` passed as a binding, not a wrapper view; `.constant` is for a read-only variant. `@Previewable` and UIKit previews need iOS 17: below that minimum, mark the preview `@available(iOS 17, *)`.
- **No logic in views.** A view draws the state it is given and reports what the user did. Rules, validation, formatting decisions, networking and storage go where this project's pattern puts them (view model, presenter, interactor, reducer). A button action calls one named method; no business logic inline in `body`, `.task` or `.onAppear`. State the control owns stays in the view as `@State`: the text being typed, focus, scroll position. Keystrokes sent on an asynchronous round trip to be redisplayed get dropped and reordered. A child view gets only the values it draws and the actions it raises, never the parent's whole view model, interactor or store. Colours and type come from the project's tokens when it has them.
- **A one-shot request kept in state needs an identity.** A navigation or toast request that a view observes carries an id (a `UUID`) and compares on it. `onChange` fires only on a difference, so the same request twice in a row is otherwise dropped.
- **Accessibility is part of done** for a UI change: labels on icon-only controls, Dynamic Type survives, 44-point targets, sensible VoiceOver order.

Detail is in the `mobile-ios:ios` skill. Load the reference for the task: `build.md` (xcodebuild, signing, SwiftPM and CocoaPods failures), `legacy.md` (UIKit, Objective-C interop, incremental SwiftUI, migrations), `architecture.md` (MVVM, coordinators, VIPER, TCA, navigation structure), `modules.md` (dependency injection, packages, generated projects), `concurrency.md`, `persistence.md`, `testing.md`, `performance.md`, `release.md` (privacy, accessibility, security, App Store requirements).
