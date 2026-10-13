# Android: architecture patterns, state holders and navigation structure

Use this to work inside the pattern a project already has, or to choose one for new code. It is never a reason to change a project's pattern: that is a migration (`legacy.md`, `mobile-core:migrate`). Facts checked 2026-10-13 against developer.android.com, AndroidX release notes and the libraries' repositories.

## Find the pattern before writing

The session profile and `mobile recon` give the counts. Read one finished feature end to end and copy its shape.

| Markers | Pattern | Where new behaviour goes |
|---|---|---|
| `ViewModel` exposing one `StateFlow<UiState>`, functions called from the UI | state holder with one-way data flow (what Google documents; teams call it MVVM) | a ViewModel function that updates the state |
| a sealed `Intent` / `Action` / `Event` type, a reducer, `ContainerHost`, `MavericksViewModel` | MVI | a new intent and its handling; state changes only in the reducer |
| `Presenter` and a `View` interface | MVP (legacy) | a presenter method and a view-interface method; no new patterns here |
| `*UseCase` classes, `domain` / `data` / `ui` packages or modules | layered ("Clean") | repository contract, implementation, use case, then the ViewModel |
| Circuit `Presenter` + `Ui`, Molecule | Compose-driven presenters | a new event in the screen's event sink |

## What Google's guide actually says

The official guide never uses the words MVVM or MVI. It describes a UI layer (UI elements and state holders), a data layer (repositories over data sources) and an optional domain layer, with one-way data flow and a single source of truth per kind of data.

- **Expose one UI state** per screen as a `StateFlow`, usually `stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), initial)`, and collect it with `collectAsStateWithLifecycle()`.
- **Do not send events from the ViewModel to the UI** (rated "strongly recommended"). Something the UI must do once, such as showing a message or navigating, becomes state, and the UI tells the ViewModel when it is done (`userMessageShown()`). A `Channel` or `SharedFlow` can lose the event when the UI is not collecting. Many codebases still use a channel: follow the file you are in, and do not add a second mechanism.
- **A ViewModel holds no `Activity`, `Context`, `View` or `Resources`**, is not an `AndroidViewModel`, and is not passed down to child composables: pass state and lambdas. One screen's ViewModel does not depend on another's.
- **Do not start work in a ViewModel's `init`.** Start it from the first collection or from an explicit call. Work longer than a few seconds belongs to WorkManager, not `viewModelScope`.
- **Process death:** a ViewModel does not survive it. Keep small things (an id, a query, a scroll position) in `SavedStateHandle` or `rememberSaveable`, and everything else in Room or DataStore.
- **Repositories are the only way to the data sources**, are main-safe, and for offline-first apps the local database is the source of truth.

## The domain layer and "Clean Architecture"

- Google rates a domain layer "recommended in big apps" and says to add use cases only when needed: to reuse logic across ViewModels or to keep one ViewModel simple. Forcing every data access through a use case "can add complexity for little benefit".
- A use case does one thing, holds no mutable state, is named verb + noun + `UseCase`, is called through `operator fun invoke`, and is main-safe.
- In a project that does have the layer, keep its rules: the UI depends on the domain, the data layer implements the domain's repository interfaces, and the domain imports no Android, Retrofit or Room types. A new feature goes contract, implementation, use case, ViewModel, even when a shortcut would compile.
- Map between network, database and domain models where the project already does. Do not add a model per layer to a small app.

## MVI libraries: the traps

- **Orbit** (12.x): a side effect goes to exactly one collector and is cached while nobody collects; two collectors silently compete. `reduce` cannot call suspend functions: do the I/O first. Version 12 renamed `ContainerHost` and `container()`; the old names are deprecated aliases.
- **Mavericks** (3.x): `setState` is queued and runs on a background thread, so state is not updated when the call returns. Only `@PersistState` properties survive process death.
- **Circuit** (0.x): `rememberRetained` survives rotation, not process death; use `rememberSaveable` for that. Events go through the `eventSink` in the state.
- In any MVI code: no I/O inside a reducer, and keep the state small enough to save.

## Navigation

| | Navigation 3 (`androidx.navigation3`, stable since late 2025, 1.2 current) | Navigation Compose 2.x (in maintenance: critical fixes only) |
|---|---|---|
| Model | you own the back stack: a list of keys; `NavDisplay` renders it | `NavController` owns it; `NavHost` with destinations |
| Routes | `@Serializable` keys implementing `NavKey` | `@Serializable` routes (since 2.8) |
| Per-screen ViewModel | only with `rememberViewModelStoreNavEntryDecorator()`, added after the saveable-state decorator | automatic per destination |
| Results | `ResultEventBus` is in memory: lost on process death | `SavedStateHandle` results survive |
| Deep links | `DeepLinkMatcher` (since 1.2); you build the starting back stack | declared per destination |

- The back stack survives rotation and process death only when it comes from `rememberNavBackStack` and every key is both a `NavKey` and `@Serializable`.
- Pass ids, not objects. A screen reports what happened through a lambda; the ViewModel does not hold the navigator unless the project does that everywhere.
- In a multi-module app each feature exposes its keys (Navigation 3) or its `NavGraphBuilder` and `NavController` extensions (2.x), and the app module assembles them.
- Moving from 2.x to 3 is a migration with preconditions: typed routes first, one atomic change, and several graph shapes unsupported. The official guide tells agents to stop and confirm the plan with a person. Google's `navigation-3` skill covers it.

## A default for new code

Google's layering: Compose, one activity, one ViewModel per screen exposing one state, repositories, Hilt, Navigation 3. Add use cases when logic is shared or a ViewModel grows. Choose MVI only when the team wants every change to pass through one reducer. Record the choice in a design document (`mobile-core:design`).

## Mistakes to expect from yourself

1. A ViewModel that calls Retrofit or a DAO directly in a project that has repositories or use cases.
2. A new one-off event channel in a codebase that models events as state, or the reverse.
3. Navigation 2 code in a Navigation 3 project, or assuming a Navigation 3 entry gets its own ViewModel without the decorator.
4. State that lives only in the ViewModel and is gone after process death.
5. A use case, an interface and a mapper for a one-line call in a small app.
6. Passing a whole object through navigation instead of its id.
