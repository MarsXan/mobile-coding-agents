# iOS: legacy code and migrations

## UIKit view controllers

**Lifecycle: put work where the facts are true.**

| Callback | True at this point | Use for |
|---|---|---|
| `viewDidLoad` | view loaded; size and traits not final | one-time setup that needs no geometry |
| `viewWillAppear` | about to show; runs on every appearance | refresh that must precede display |
| `viewIsAppearing` | in the hierarchy with final traits and geometry (back-deploys to iOS 13 with the iOS 17 SDK) | geometry- or trait-dependent configuration |
| `viewDidLayoutSubviews` | layout done; runs many times | idempotent layout adjustments only |
| `viewDidAppear` | visible | start animations, analytics, focus |
| `viewWillDisappear`, `viewDidDisappear` | leaving | stop timers, cancel tasks, save drafts |

- Touching `view` in `init` forces the view to load early. In tests call `loadViewIfNeeded()`.
- `traitCollectionDidChange` is deprecated from iOS 17; new code uses `registerForTraitChanges`. Leave existing overrides alone unless the task is that change.
- `UIApplication.shared.keyWindow` and `.windows` are deprecated. Reach the window through the scene: `view.window?.windowScene`.

**Memory: who keeps the controller alive.**

- An object the controller owns must not own it back. Use `[weak self]` in closures stored by the controller or by something it owns: timers, block-based `NotificationCenter` observers, Combine `sink` stored in `cancellables`, `DispatchWorkItem`, completion handlers kept by a service.
- `Timer` and `CADisplayLink` retain their target; invalidate them. `URLSession` retains its delegate until invalidated.
- A `Task` started by a controller holds `self` until it finishes. A `for await` loop over a stream that never ends holds it forever: store the task and cancel it in `viewDidDisappear` or `deinit`.
- Delegates are `weak` and their protocols class-bound.
- Prove a fix: `deinit` runs when the screen is dismissed. Xcode's memory graph shows the cycle when it does not.

**Lists.**

- A reused cell carries old state: reset it in `prepareForReuse` and cancel its image load.
- An async callback must not capture the cell. Capture the item identifier and look the cell up again.
- `Invalid update: invalid number of rows` means the model and the batch update disagree. Diffable data sources remove that class of bug; adopt them when the task allows.

## Objective-C interop

- **Headers.** A bridging header exposes Objective-C to Swift. `<Module>-Swift.h` exposes Swift to Objective-C: import it in `.m` files only, and use `@class` or `@protocol` forward declarations in `.h` files.
- **Visibility.** Objective-C sees only `@objc` members of `NSObject` subclasses. Structs, enums with associated values, generics and Swift-only types are invisible to it.
- **Names are API.** Renaming an `@objc` method changes its selector and breaks Objective-C callers, `#selector` uses, storyboard actions and KVO key paths without a compile error. Keep the old name with `@objc(oldName:)`.
- **Archived classes.** `NSCoding` stores the class name, and a Swift class's name includes its module. Renaming or moving an archived class makes old data undecodable. Pin it with `@objc(StableName)` or register the old name with `NSKeyedUnarchiver.setClass(_:forClassName:)`.
- **Nullability.** An Objective-C API without annotations imports as an implicitly unwrapped optional and crashes on `nil`. Treat such values as optional in Swift, and annotate headers (`NS_ASSUME_NONNULL_BEGIN`, `nullable`) when you own them.
- **Collections.** `NSArray *` without lightweight generics imports as `[Any]`. Add `NSArray<Type *> *` in headers you own.
- **Exceptions.** Swift cannot catch `NSException`. An API that raises (key-value coding, some unarchiving, collection bounds) needs an Objective-C `@try` wrapper or a precondition check.
- **Concurrency.** Objective-C headers carry no `Sendable` or isolation information. `@preconcurrency import Module` at the import site is the legitimate bridge during migration. A completion handler from Objective-C may arrive on any queue.
- **SwiftPM.** One target cannot mix Swift and Objective-C; split them into two targets.

## Adding SwiftUI to a UIKit app

- **Host a SwiftUI view** in `UIHostingController` added as a child: `addChild`, add its view with constraints, `didMove(toParent:)`. For cells use `UIHostingConfiguration` (iOS 16+).
- **Keep UIKit in charge of navigation** until most screens are migrated: push hosting controllers on the existing `UINavigationController`. A `NavigationStack` inside a pushed hosting controller gives two navigation bars.
- **Host a UIKit view in SwiftUI** with `UIViewRepresentable` or `UIViewControllerRepresentable`. `make...` runs once; `update...` runs often and must be cheap and idempotent. Delegates live in the `Coordinator`.
- **Share state** through one model object owned on the UIKit side and passed into the SwiftUI root view. The SwiftUI environment does not cross a hosting controller: pass dependencies in explicitly.
- **Order.** Leaf screens first, one screen per change, with a snapshot of the old screen to compare against. Accessibility, Dynamic Type, keyboard handling and state restoration are where migrated screens regress.

## Scene lifecycle (required with the iOS 27 SDK)

Apple's TN3187: when built with the SDK of the major release after iOS 26, a UIKit app that has not adopted the scene lifecycle will not launch. Adopting the lifecycle is required; supporting multiple scenes is not.

1. Add `UIApplicationSceneManifest` to `Info.plist` with a scene configuration (delegate class, storyboard if any).
2. Create the window in `scene(_:willConnectTo:options:)` from the `UIWindowScene`, not in `application(_:didFinishLaunchingWithOptions:)`.
3. Move lifecycle code: `applicationDidBecomeActive` to `sceneDidBecomeActive`, `applicationWillResignActive` to `sceneWillResignActive`, `applicationDidEnterBackground` to `sceneDidEnterBackground`, `applicationWillEnterForeground` to `sceneWillEnterForeground`.
4. Move URL, user-activity and shortcut handling to the scene delegate. **Handle the cold-launch case too**: at launch they arrive in `connectionOptions` of `scene(_:willConnectTo:options:)`, not in the "already running" callbacks. Missing this silently breaks deep links and universal links from a terminated state.
5. Replace `UIApplication.shared.keyWindow`, `.windows`, `UIScreen.main` and app-delegate `window` lookups.
6. Check SDKs that hook the app delegate (analytics, deep-link, push libraries) for scene support.
7. Test launch from a terminated state by deep link, universal link, push and home-screen shortcut, and on iPad in Split View.

## `ObservableObject` to `@Observable` (needs a minimum of iOS 17)

| Before | After |
|---|---|
| `class M: ObservableObject` with `@Published var` | `@Observable class M` with plain `var` |
| `@StateObject private var m = M()` | `@State private var m = M()` |
| `@ObservedObject var m: M` | `let m: M`, or `@Bindable var m: M` when bindings are needed |
| `@EnvironmentObject var m: M`, `.environmentObject(m)` | `@Environment(M.self) private var m`, `.environment(m)` |

What changes in behaviour:

- Views now update only for properties they read. Code that relied on any change refreshing a view will stop updating.
- `$property` publishers and `objectWillChange` are gone. A model that feeds Combine pipelines stays an `ObservableObject` until those pipelines are migrated.
- `@StateObject` created its object once. The initial value of `@State` may be evaluated each time the view is initialised, depending on the toolchain: keep the initialiser cheap and free of side effects.
- `@AppStorage` inside an `@Observable` class does not trigger view updates.
- `@Observable` does not make a class main-actor isolated. Mark UI-bound models `@MainActor` unless the module defaults to it.
- Both systems can coexist. Migrate one model at a time; never use both on one class.

## CocoaPods to SwiftPM

1. **Inventory** from `Podfile` and `Podfile.lock`. For each pod: does a Swift package exist at the same version; subspecs (map to package products); resource bundles (code using `Bundle(for:)` or a named bundle changes to `Bundle.module`); `post_install` hooks and build-setting changes; binary pods (need an XCFramework); pods that only exist to run a script (move to a build-tool plugin or an installed tool).
2. **One pod, or one cohesive family, per change.** Remove it from the `Podfile`, `pod install`, add the package at the same version, build, test, compare app size and launch time. CocoaPods and SwiftPM coexist during the migration.
3. **Never the same library through both.** The result is duplicate symbols or "Class X is implemented in both" at run time.
4. **Finish**: `pod deintegrate`; remove `Podfile`, `Podfile.lock`, `Pods/` and the CI steps and caches for them. Re-check settings the Pods xcconfigs injected (`-ObjC`, header and framework search paths) and schemes that lived in the workspace.

Traps: different transitive versions; static versus dynamic linking changing size, launch time or producing duplicates when a package is linked into both the app and an extension; private pods that mix Swift and Objective-C and must be split into two targets.

## Storyboards and XIBs

Outlets and actions are bound by name at run time. Renaming a property or method, or deleting a class a storyboard references, compiles and then crashes with "not key value coding-compliant". Search `.storyboard` and `.xib` files for the name before renaming.
