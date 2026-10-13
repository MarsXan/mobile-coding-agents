# iOS: architecture patterns, state ownership and navigation structure

Use this to work inside the pattern a project already has, or to choose one for new code. It is never a reason to change a project's pattern: that is a migration (`legacy.md`, `mobile-core:migrate`). Facts checked 2026-10-13 against Apple's documentation and release notes and the libraries' repositories.

## Find the pattern before writing

| Markers (`mobile recon` counts them) | Pattern | Where new behaviour goes |
|---|---|---|
| view controllers that do everything | MVC, UIKit's default | in the controller or a helper it owns; no view model for one change |
| `*ViewModel` with `@Observable` or `ObservableObject` | MVVM | a view-model method and state; the view binds and forwards |
| `*Coordinator` classes, a `Coordinator` protocol | coordinators own navigation | the screen reports an event; the coordinator creates and shows the next screen |
| `*Presenter`, `*Interactor`, `*Router` or `*Wireframe`, protocol contracts | VIPER (or Clean Swift) | every layer of the module, and its protocols |
| `@Reducer`, `Store`, `@ObservableState` | The Composable Architecture (TCA) | state, an action and a reducer case; side effects in an effect |
| `*UseCase`, `*Repository`, `Domain` and `Data` targets | layered ("Clean") | repository contract, implementation, use case, then the UI |

Mixed codebases are normal. Follow the pattern of the feature you are in, not the newest one in the repository.

## Rules inside each pattern

**MVVM.**

- A view model imports no view types and holds no view. It exposes state and takes intents as methods.
- SwiftUI with Observation: an `@Observable` class, owned by `@State` in the view that creates it, passed down as a plain property (`@Bindable` where bindings are needed), shared with `@Environment(Type.self)`. Reading `@Environment(Type.self)` when nothing was injected crashes.
- Built with Xcode 26 or earlier, a `@State` default value is created again every time SwiftUI initialises the view, and only the first is kept: no side effects there, start work in `.task`. Built with the Xcode 27 SDK the default is evaluated once, and a default value plus an assignment in `init` no longer compiles.
- `@Observable` adds no actor isolation. An app target created with Xcode 26 defaults its module to the main actor, so a view model there is already isolated; in a Swift package or an older project, mark it `@MainActor` yourself. The session profile shows the setting.
- A view model does not navigate unless this project does it that way: it reports through a closure or a router it was given.

**Coordinators (UIKit).**

- A view controller never creates or pushes another screen. It calls back; the coordinator decides.
- A parent keeps its child coordinators strongly and removes one when its flow ends, **including when the user swipes or taps back**. The navigation controller's `delegate` is weak and is one slot.
- The common way to notice a back gesture is the navigation delegate's `didShow`, checking the transition's `.from` controller. There is no transition to inspect after a non-animated pop, and a pop of several screens reports only the top one. `didMove(toParent: nil)` on the flow's controllers fires for each removed controller and was the more reliable signal in a test on iOS 18 and 26. Release there, not in `willMove(toParent:)`, which also fires for a swipe that is cancelled.
- A sheet dismissed in code does not call `presentationControllerDidDismiss`: end the flow on that code path too.
- Deep links, and the launch options of a cold start, go to the root coordinator, which builds the stack.

**VIPER.** A module is a view, a presenter, an interactor, a router and entities, wired by a builder, each behind a protocol. The presenter imports no UIKit, the interactor knows no view, and only the router navigates. The view holds the presenter strongly; the presenter holds the view weakly, and so does the interactor its output. A new screen means every piece, from the project's own template. Skipping a layer because "it is one line" is the mistake.

**The Composable Architecture (1.x; 2.0 is not released).**

- Current API: `@Reducer`, `@ObservableState`, `@Dependency`, `@Presents` with `PresentationAction`, `StackState` and `StackAction`, `@Shared`, `@Bindable var store`. The `ViewStore` family (`WithViewStore`, `IfLetStore`, `ForEachStore`, `SwitchStore`, `NavigationStackStore`) and `@BindingState` are deprecated since 1.24 and still compile. Do not write new code with them, and do not rewrite existing uses unasked.
- Since 1.24 it needs iOS 16 and Swift 6.1. Below iOS 17, views need `WithPerceptionTracking`.
- Reducers run on the main thread and have no side effects. I/O and heavy work go in `.run`, which is `@Sendable`: capture values, as in `[id = state.id]`.
- Share logic through a method that takes `inout State` and returns an effect, not by sending another action. Avoid actions at slider or scroll frequency.
- Never send an action after `await dismiss()`.
- `TestStore` is exhaustive by default: every state change and received action is asserted. Keep it so for unit tests.
- Swift 6.2's default main-actor isolation is not supported by 1.x (nested `@Reducer enum` destinations fail to compile). Leave that setting off for a TCA module unless the project already works around it.
- CI builds need `-skipMacroValidation`.

**Layered ("Clean").** The UI depends on the domain; the data layer implements the domain's repository protocols; the domain imports no UIKit, SwiftUI, networking or persistence framework. Map transport and storage models at the data boundary. Add a use case when logic is shared or not trivial, not one per call.

## SwiftUI navigation

- One `NavigationStack` per stack of screens, with a path the app owns: a typed array, or `NavigationPath` when the types are mixed. A deep link and "pop to root" are changes to that path.
- `navigationDestination(for:)` sits outside lazy containers (`List`, `LazyVStack`), once per type, inside the stack. Do not put a `NavigationStack` inside a destination.
- A router is an `@Observable` object that owns a path, one per tab or per sheet. Views ask it; they do not build each other's destinations.
- `NavigationPath.codable` is `nil` when any element is not `Codable`, so restoration needs every route to be. Check a restored path still makes sense.
- A sheet is its own navigation context, with its own stack and router.
- Built with the iOS 27 SDK, a `TabView` whose selection is not a visible tab can crash. Select only tabs that exist.

## A default for new code

Apple documents data flow, not an architecture. A workable default: SwiftUI views, `@Observable` models owned with `@State`, one router per navigation stack, dependencies passed in initialisers behind protocols, and plain types for domain logic. Choose TCA when the team wants every state change tested through one reducer and accepts the dependency. Choose coordinators for a UIKit app. Record the choice in a design document (`mobile-core:design`).

## Mistakes to expect from yourself

1. Pushing a view controller from another view controller in a coordinator-based app.
2. A view model added to one screen of an MVC app, or business logic left in a view of an MVVM app.
3. Old TCA (`WithViewStore`, `@BindingState`, `ReducerProtocol`) written into a project on a current version, or new TCA forced onto a file that still uses the old one.
4. A side effect in a reducer, or in a `@State` default value.
5. A child coordinator that is never released after a swipe back.
6. Skipping a VIPER layer.
