# Flutter: architecture patterns, state holders and navigation structure

Use this to work inside the pattern a project already has, or to choose one for new code. It is never a reason to change a project's pattern: that is a migration (`legacy.md`, `mobile-core:migrate`). Facts checked 2026-10-13 against docs.flutter.dev, bloclibrary.dev, riverpod.dev and pub.dev.

## Find the pattern before writing

The session profile names the state and routing packages, and `mobile recon` counts the markers. Read one finished feature end to end and copy its shape: file layout, naming, who creates what.

| Markers | Pattern | Where new behaviour goes |
|---|---|---|
| `extends Bloc<` / `Cubit<`, `bloc/` folders | BLoC | an event (or cubit method) and its handler; the widget only adds events and renders states |
| `Notifier` / `AsyncNotifier`, `@riverpod`, `ConsumerWidget` | Riverpod | a notifier method; widgets `ref.watch` state and call methods in callbacks |
| `ChangeNotifier` view models, `ListenableBuilder`, `provider` | MVVM, as in Flutter's own guide | a view-model method or command; the view calls it and listens |
| `GetxController`, `.obs`, `Get.find` | GetX | follow it in place; leaving it is a migration (`legacy.md`) |
| `Store`, reducers, `StoreConnector` | Redux | an action and a reducer case; side effects in middleware |
| `Observable`, `Observer`, `@action` | MobX | an `@action` on the store |

## The layering most projects share

Flutter's architecture guide (docs.flutter.dev/app-architecture) has a UI layer (views and view models, one to one), a data layer (repositories and services) and an optional domain layer.

- **Widgets hold no logic** beyond layout, simple conditions and animation. Logic lives in the state holder.
- **A state holder depends on repositories**, passed in through its constructor. It does not call a service, an HTTP client or a database itself.
- **Repositories** own caching, retry, error mapping and refresh, and return domain models. They do not know about each other: combine two of them in the state holder or in a use case.
- **Services** wrap one external thing (an API, a plugin, a file) and hold no state.
- **Use cases only when earned**: logic that merges several repositories, is complex, or is reused by several state holders. The guide's words are "add use-cases only when needed". No pass-through class per call.
- **State is immutable** (freezed or a hand-written `copyWith`). Data flows down, events flow up.
- **Folders.** The guide puts UI by feature (`lib/ui/<feature>/view_models`, `widgets`) and data and domain by type (`lib/data/repositories`, `lib/data/services`, `lib/domain/models`). Many projects are fully feature-first instead (`lib/<feature>/{data,bloc,view}`). Copy what is there.

## BLoC and Cubit (bloc 9, flutter_bloc 9)

- A bloc receives information only through events and injected repositories. It imports no widgets and takes no `BuildContext`.
- **Events run concurrently by default** (since bloc 7.2). Where order matters (a search box, a submit button) pass a transformer from `bloc_concurrency`: `sequential()`, `droppable()` or `restartable()`.
- **Never `emit` after the handler has returned.** Await everything, including `emit.forEach` and `emit.onEach`; otherwise it is an assertion failure.
- **Blocs do not talk to each other.** Either a `BlocListener` in the widget tree adds an event to the second bloc, or both listen to one repository stream.
- Never mutate a state. A state equal to the current one is dropped, so every field must be in `props`.
- Names (bloclibrary.dev): events in the past tense (`OrdersStarted`, `OrdersRefreshed`, `OrderCancelPressed`); states as nouns, or one state class with a status enum. Follow the project's variant.
- Public cubit methods return `void` or `Future<void>`. A bloc gets no public methods beyond `add`.
- A widget callback that must return a `Future`, such as `RefreshIndicator.onRefresh`: add the event, then await the bloc's stream for the next settled state. Returning at once ends the spinner before the data arrives.
- `hydrated_bloc` has no migrations. If `fromJson` throws, the state silently resets and the cache is overwritten; the storage key is the class name. A state-shape change needs a tolerant `fromJson`, and renaming the bloc drops what users had saved.
- The official linter is `bloc_lint` (`include: package:bloc_lint/recommended.yaml`).

## Riverpod 3 (riverpod 3.x; riverpod_annotation and riverpod_generator are 4.x)

- Use `Notifier`, `AsyncNotifier` and `StreamNotifier`. `StateProvider`, `StateNotifierProvider` and `ChangeNotifierProvider` still exist but moved to `package:flutter_riverpod/legacy.dart`. The `AutoDispose*` and `Family*` class variants and `AsyncValue.valueOrNull` are gone.
- `ref.watch` in `build`; `ref.listen` for side effects; `ref.read` only inside callbacks. No side effects while a provider initialises.
- After every `await` in a notifier, `if (!ref.mounted) return;`. Using a disposed `ref` now throws.
- **A failed provider retries by itself**, up to 10 times, backing off from 200 ms. `Error` subclasses are not retried. Switch it off (`retry: (retryCount, error) => null`) where a retry is wrong: a payment, a form submit, and in a test that asserts an error.
- An error read through `ref.watch` or `ref.read` arrives wrapped in `ProviderException`. `AsyncValue.error` and `ref.listen` see the original.
- Generated providers dispose themselves when unused. Add `keepAlive: true` for state that must outlive the screen.
- Listeners in widgets that are off screen are paused.
- Offline persistence and mutations are marked experimental and can change without a major version.
- Tests: a new `ProviderContainer.test()` per test; override repositories, do not mock notifiers.
- `riverpod_lint` is set up under `plugins:` in `analysis_options.yaml` since 3.1, no longer through `custom_lint`.

## Navigation structure

`legacy.md` has the Navigator 1.0 to go_router migration. For structure:

- Flutter's guide recommends go_router for most apps. The package is feature-complete (fixes only) and is at 18.x. Version 16 made paths case-sensitive; 18 needs Flutter 3.44.
- One route table. Screens navigate by location (`context.go('/orders/42')`) or by typed routes (`go_router_builder`); they do not construct each other.
- Pass identifiers in the path or the query. `extra` is not part of the location: it does not survive a deep link, and on restoration it is dropped unless it is JSON-encodable or an `extraCodec` is set.
- Sign-in and onboarding guards go in the top-level `redirect` with a `refreshListenable`. A redirect loop stops after five hops with an error screen.
- Tabs that each keep a stack: `StatefulShellRoute`, with routes declared per branch.
- Dialogs and `Navigator.push` pages are not deep-linkable, and `PopScope` cannot veto a page-backed route.

## A default for new code

When nothing exists yet and the team has no standard: the guide's layering, and one state library for the whole app. BLoC when the team wants explicit events and a trace of what happened; Riverpod when it wants less ceremony and compile-checked dependencies; `ChangeNotifier` view models for a small app. go_router for navigation. Flutter itself endorses no state package. State the choice and what it costs in a design document (`mobile-core:design`); do not assume one.

## Mistakes to expect from yourself

1. Calling a repository or a service from a widget, or `setState` for data the state holder owns.
2. A second state library "just for this screen".
3. One bloc reading another bloc's state.
4. Assuming bloc events run in order, or that a Riverpod provider reports the first failure.
5. A use case, an interface and a mapper for a one-line call.
6. An object in `extra`, with deep links or restoration expected to work.
