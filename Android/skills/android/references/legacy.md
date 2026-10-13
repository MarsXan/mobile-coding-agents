# Android: legacy code and migrations

Every migration here goes through `mobile-core:migrate`: inventory, coexistence rule, small slices, gates. This file holds what is specific to each one, above all where the old and the new **mean different things**.

## Views and Fragments (working in them, not replacing them)

- A Fragment's view dies before the Fragment does. Clear view bindings in `onDestroyView`, and observe with `viewLifecycleOwner`, never the Fragment itself.
- No fragment transaction or navigation after `onSaveInstanceState`. `commitAllowingStateLoss` hides the bug; deliver the result when the lifecycle is `STARTED`.
- Fragments are re-created by the system through the no-argument constructor. Pass data in `arguments`, not through a custom constructor or setters.
- `RecyclerView`: use `ListAdapter` with `DiffUtil`. In a click listener read `bindingAdapterPosition` at click time and check for `NO_POSITION`. Reset every view in `onBindViewHolder`.
- Deprecated and still common. Replace when the task touches them, not as a drive-by:

| Legacy | Current |
|---|---|
| `startActivityForResult`, `onActivityResult`, `requestPermissions` | Activity Result APIs; `registerForActivityResult` is called before the lifecycle reaches `STARTED` |
| `onBackPressed()` | `OnBackPressedDispatcher` and `OnBackPressedCallback` |
| `AsyncTask`, `IntentService`, `Loader` | coroutines, WorkManager, `ViewModel` |
| `kotlinx.android.synthetic` | view binding |
| `LocalBroadcastManager` | a shared flow or other in-process signal |
| `Handler()` with no looper | `Handler(Looper.getMainLooper())`, or a coroutine |

**Behaviour that changes with targetSdk** (confirm against the behaviour-change pages for the level the project targets):

- Target 35: the app draws edge to edge. Handle insets (`ViewCompat.setOnApplyWindowInsetsListener` with system bars, display cutout and IME; in Compose the `WindowInsets` padding modifiers, applied once: IME padding added twice is the common bug).
- Target 36: the edge-to-edge opt-out no longer works; predictive back is on, so `onBackPressed` is not called; orientation, aspect-ratio and resizability restrictions are ignored on large screens (smallest width 600dp and up), so layouts must adapt.

## Java and Kotlin together

- A Java type without nullability annotations arrives in Kotlin as a platform type and crashes on null. Treat it as nullable; annotate the Java (`@Nullable`, `@NonNull`) when you own it.
- For Java callers of Kotlin: `@JvmStatic` on companion members, `@JvmOverloads` for default arguments, `@JvmField` for fields, `@Throws` for checked exceptions.
- **Converting a file**: rename it to `.kt` with `git mv` in its own commit, then convert, so history survives. Keep behaviour identical first; make it idiomatic in a later change. Check what Kotlin changes silently: classes are `final` (mocking frameworks and some libraries need `open`), `static` members become companion members, field nullability must now be decided.
- **Gson** creates objects without calling constructors: a Kotlin non-null property can be null at run time, and R8 renames fields it reads by reflection. Keep `@SerializedName` and keep rules, or move that model to a code-generating serialiser as its own change.

## RxJava to coroutines and Flow

Bridge with `kotlinx-coroutines-rx2` or `-rx3` (`await()`, `asFlow()`, `rxSingle { }`) so one layer moves at a time.

| RxJava | Coroutines | The difference that bites |
|---|---|---|
| `Single<T>`, `Maybe<T>`, `Completable` | `suspend fun` returning `T`, `T?`, `Unit` | errors become thrown exceptions, including cancellation |
| `Observable<T>`, `Flowable<T>` | `Flow<T>` | a flow is cold and suspends instead of buffering |
| `BehaviorSubject` | `MutableStateFlow` | needs an initial value; conflates; **drops values equal to the current one** |
| `PublishSubject` | `MutableSharedFlow` | with no buffer `tryEmit` fails and `emit` suspends on slow collectors |
| `subscribeOn(io())` | `flowOn(Dispatchers.IO)` | affects upstream only, as before |
| `observeOn(mainThread())` | collect in a main-dispatcher scope | **there is no `flowOn` for this**: `flowOn(Dispatchers.Main)` moves the upstream to main |
| `CompositeDisposable.clear()` | cancel the jobs, or `coroutineContext.cancelChildren()` | `scope.cancel()` kills the scope for good; nothing launches in it afterwards |
| `switchMap`, `flatMap`, `concatMap` | `flatMapLatest`, `flatMapMerge`, `flatMapConcat` | `flatMapMerge` has a default concurrency limit |
| `onErrorReturn`, `retry` | `catch { emit(...) }`, `retry` | `catch` sees upstream errors only |
| `replay(1).refCount()` | `stateIn` or `shareIn` with `WhileSubscribed` | pick the stop timeout deliberately |

Structured concurrency also changes failure behaviour: one failing child cancels its siblings unless they run under a supervisor. Check every place the Rx code relied on independent streams.

## LiveData to StateFlow

- `MutableLiveData<T>()` could be unset; `MutableStateFlow` needs an initial value. Decide what "nothing yet" is.
- LiveData delivered every `setValue`, including equal values. StateFlow skips equal values. **One-off events** (navigate, show a message) modelled as LiveData stop working as state: send them through a channel, or model them as state the UI acknowledges.
- LiveData stopped itself when the UI was inactive. A flow does not: collect with `repeatOnLifecycle(STARTED)` or `collectAsStateWithLifecycle()`, or it keeps running in the background.
- `Transformations.map` and `switchMap` become `map` and `flatMapLatest` followed by `stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), initial)`.

## kapt to KSP

One processor at a time: Room, Moshi, Hilt and Dagger, Glide all support KSP in current versions. Replace `kapt(...)` with `ksp(...)`, move processor arguments to `ksp { arg(...) }`, and remove the kapt plugin only when the last processor has moved. A library with no KSP support (data binding with Kotlin binding adapters) keeps kapt alive: say so instead of forcing it.

## Dagger to Hilt, and other dependency-injection changes

Migrate component by component, using `@EntryPoint` to reach Hilt from code not yet migrated. **A dependency graph that compiles can still fail at run time** in one variant, one dynamic feature or one multibinding. After any DI change, launch the app or run an instrumented smoke test; a green compile is not evidence.

## Views to Compose

- **Interop both ways.** `ComposeView` in a layout or Fragment (in a Fragment set `ViewCompositionStrategy.DisposeOnViewTreeLifecycleDestroyed`); `AndroidView` to host a View in Compose, with a cheap, idempotent `update`.
- **Order.** Leaf components, then screen content, then navigation last. Keep Fragment navigation until most screens are Compose.
- **State.** Hoist it to the ViewModel and collect with `collectAsStateWithLifecycle()`. UI state that must survive rotation and process death uses `rememberSaveable` or `SavedStateHandle`, not `remember`.
- **Lists.** `LazyColumn` items need stable `key`s and a `contentType`.
- **Theme.** The Compose theme must carry the same colours, type and shapes as the XML theme, in light and dark.
- **Per migrated screen, check**: rotation, process death, dark theme, large font scale, TalkBack order, a screenshot against the old screen. These are where migrated screens regress.
- Compose performance advice depends on the Kotlin and Compose compiler version (strong skipping is the default from Kotlin 2.0.20). Read the project's versions before "fixing" stability.

## Navigation

Moving between the Fragment navigation component, Navigation Compose and Navigation 3 is its own migration. Deep links, back-stack behaviour and state restoration need tests before and after.
