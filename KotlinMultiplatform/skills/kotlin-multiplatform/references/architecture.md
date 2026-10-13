# Kotlin Multiplatform: structure of shared code

Use this to work inside the structure a project already has, or to choose one for new shared code. Facts checked 2026-10-13 against kotlinlang.org, developer.android.com and the libraries' repositories.

## Decide what is shared, per layer

A project shares some layers and keeps others native. Find out which before adding code, and put new code on the side the project already chose.

| Layer | Commonly shared | Notes |
|---|---|---|
| Models, validation, business rules | almost always | the cheapest and safest part to share |
| Networking, storage, repositories | usually | Ktor, Room or SQLDelight, DataStore |
| State holders (view models, presenters) | often | then each platform's UI only renders state and sends events |
| Navigation | sometimes | shared with Compose Multiplatform; native otherwise |
| UI | Compose Multiplatform projects only | SwiftUI and Jetpack Compose otherwise |

Google rates Kotlin Multiplatform production-ready for sharing business logic, and Compose Multiplatform for iOS has been stable since 1.8.

## Modules

- The official template has an Android app module, an iOS app (the Xcode project), and one or more shared modules (`shared`, or `composeApp` plus `sharedLogic` and `sharedUI`). With AGP 9 the Android entry point must be its own module.
- One **umbrella module** produces the iOS framework and re-exports what Swift needs. Two frameworks that each contain the Kotlin runtime and common classes do not share types: an object from one cannot be passed to the other. Add feature modules behind the umbrella, not as separate frameworks.
- Inside shared code the Android layering applies: UI state holders depend on repositories (or use cases, if the project has them); repositories hide data sources; nothing in the domain imports Ktor, Room or platform types. See `architecture.md` and `modules.md` in the Android pack for the rules.

## Shared state holders

- A shared view model exposes one `StateFlow` of immutable state and takes events as function calls. Android collects it with `collectAsStateWithLifecycle()`. iOS needs a bridge for the flow (`swift-api.md`).
- The AndroidX `ViewModel` is multiplatform. In Compose Multiplatform, `viewModel()` needs an explicit initializer outside the JVM. In a SwiftUI app the Swift side must own the Kotlin view model's lifetime: create it once per screen, keep it in a Swift wrapper (`@Observable` or `ObservableObject`), and cancel its scope when the screen goes away.
- No Android lifecycle types (`LifecycleOwner`, `Context`, `SavedStateHandle` from an Activity) in a shared state holder.
- One-off events (navigate, show a message) are modelled as state the UI acknowledges, as on Android. A hot flow with no replay loses events while SwiftUI is not collecting.

## Dependency injection

- **Koin** is the most common choice in multiplatform projects and is what the official template uses: `commonMain` modules, plus platform modules for platform implementations. Resolution is at run time, so start the app (or run a graph check in a test) after changing a module. Swift cannot call the reified `get<T>()`; expose a helper class in `iosMain` that returns the objects the iOS app needs.
- **Metro** and **kotlin-inject** check the graph at compile time. Metro is a compiler plugin tied to a window of Kotlin versions.
- **Hilt and Dagger are Android-only**: they cannot construct anything in common code. A project with Hilt on Android and shared code needs the shared graph to be plain constructors or one of the above, wired into Hilt from `androidMain` or the app module.
- Platform implementations of an interface are registered in each platform's source set, not through `expect`/`actual` on the DI module unless the project already does it that way.

## Navigation

- Native UI: each platform navigates its own way; shared code reports intent ("order selected") through state or a callback and holds no navigator.
- Compose Multiplatform: Navigation Compose (`org.jetbrains.androidx.navigation`) and Navigation 3 (`org.jetbrains.androidx.navigation3`) both have multiplatform artifacts. Outside the JVM there is no reflection, so Navigation 3 keys need explicit polymorphic serialization (`rememberNavBackStack(config)`).
- Deep links arrive through platform code (the Android intent, the iOS scene delegate or `onOpenURL`) and are handed to shared code as a parsed value.

## Storage

- **Room** (multiplatform since 2.7; Room 3 is the `androidx.room3` group) and **SQLDelight** both work in common code. Do not introduce the second one. Schema changes follow the same rule as on Android: version bump, migration, and a test against a database written by the previous version. `persistence.md` in the Android pack has the Room details.
- The database file location is platform code: the app's files directory on Android, the documents or application-support directory on iOS. Changing it orphans users' data.
- **DataStore**: Preferences only, with the path supplied per platform.
- Keys, tokens and anything secret: Android Keystore-backed storage and the iOS Keychain, behind one interface. Not a shared plain file.

## A default for new shared code

Share models, networking, storage and repositories first. Share state holders when both apps show the same screens. Keep the UI native unless the team has chosen Compose Multiplatform. One umbrella framework, constructor injection with Koin or Metro, and the Swift-facing surface designed as in `swift-api.md`. Record the decision in a design document (`mobile-core:design`).

## Mistakes to expect from yourself

1. Moving a screen's logic into shared code in a project that keeps state holders native, or the reverse.
2. A second framework for a new feature module.
3. Hilt annotations in `commonMain`.
4. A shared view model that the iOS side creates on every SwiftUI view update, or never cancels.
5. Navigation logic in shared code of a project with native navigation.
6. A second database library, or a moved database file.
