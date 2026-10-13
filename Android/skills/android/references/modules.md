# Android: dependency injection and modules

Follow what the project does. Facts checked 2026-10-13 against dagger.dev, developer.android.com, docs.gradle.org and the libraries' repositories. For build failures and upgrades see `build.md`.

## Dependency injection

Constructor injection everywhere; one place builds the graph. Google's guide recommends Hilt, and manual injection for a simple app.

**Hilt and Dagger (2.60.x).**

- Versions are coupled. The Hilt Gradle plugin 2.59 and later requires AGP 9. Kotlin 2.4 needs Hilt 2.60 or later, which also raises Hilt's minSdk to 23.
- Use KSP (`ksp`, `kspTest`, `kspAndroidTest`): Dagger calls it stable from 2.60 with KSP 2.3.9. Under AGP 9's built-in Kotlin the old kapt plugin does not work; the choices are KSP or `com.android.legacy-kapt`.
- `hiltViewModel()` for Compose lives in `androidx.hilt:hilt-lifecycle-viewmodel-compose` since AndroidX Hilt 1.3.
- Scope only when correctness needs one instance. A module does not scope anything: the annotation on the binding does. `@ViewModelScoped` is one instance per ViewModel; to share across ViewModels use `@ActivityRetainedScoped` or `@Singleton`.
- A ViewModel that needs a run-time value: `@HiltViewModel(assistedFactory = ...)` with `@AssistedInject`. The assisted value is not saved across process death; put what must survive in `SavedStateHandle`.
- Tests: prefer `@TestInstallIn`, which replaces a module for the whole source set. `@UninstallModules` and `@BindValue` generate a component per test and slow the build. A `@BindValue` field must be set before the activity is created, and `HiltAndroidRule` goes before the rules that need the graph.
- **A graph that compiles can still fail at run time** in one variant, one multibinding or after shrinking. After a DI change launch the app or run an instrumented smoke test.

**Koin (4.x).** Resolution happens at run time. `verify()` checks constructors only: not qualifiers, properties, or `get()` calls inside a definition. The Koin Compiler Plugin (Kotlin 2.x, K2) adds compile-time checks and is what Koin's docs recommend for new projects; the older KSP compiler is deprecated. Replace definitions in tests with `declare` or `declareMock`.

**Others.** Metro is compile-time injection as a Kotlin compiler plugin, with Dagger and Hilt interop; each release supports a window of Kotlin versions, so check that table before a Kotlin bump. Square Anvil is deprecated (K1 only) and kotlin-inject-anvil is in maintenance mode: both point to Metro. kotlin-inject itself works with KSP2 only.

## Modules

**When.** A module earns its cost when it makes builds faster for a large codebase, keeps teams or features from depending on each other, or is shared between apps. Google names the failure modes itself: too fine-grained, too coarse, too complex.

**Shapes** (Google's modularization guide and the Now in Android sample):

- `app` holds the entry point and root navigation and depends on features. `feature` modules hold UI and ViewModels and depend on data. `data` modules expose repositories and hide their data sources. `core` or `common` holds shared code and depends on no feature and not on `app`.
- A feature split into `api` and `impl`: other features depend only on `api` (navigation keys, contracts); `impl` is wired in by the app module. A change inside `impl` does not recompile its consumers.
- Keep things `internal` or `private` unless another module needs them, and declare dependencies with `implementation`; `api` leaks them to consumers and costs build time.

**Build logic.**

- Shared configuration goes in convention plugins inside an included build (`build-logic`), not in `buildSrc`: any `buildSrc` change invalidates the whole build.
- Versions go in `gradle/libs.versions.toml`. One upgrade per change.
- The configuration cache is Gradle's preferred mode since Gradle 9 and becomes the default in Gradle 10. A plugin or script that reads project state at execution time breaks it. Isolated Projects is still incubating.

**AGP 9 changes that show up in multi-module builds** (details in `build.md`):

- Kotlin is built in: `org.jetbrains.kotlin.android` is removed from every module, not added.
- Only the new DSL is available: `applicationVariants` and friends are gone; use `androidComponents`.
- `org.jetbrains.kotlin.multiplatform` cannot share a module with the Android application or library plugin.
- Every library module needs its own package name (`android.uniquePackageNames=true`), and `resValues` and shaders are off unless a module turns them on.
- R classes are non-transitive (since AGP 8) and, from AGP 9, non-final in app modules: no `R` fields in a `when` that needs constants, and a resource is referenced through the module that declares it.
- The opt-out flags for the old DSL and for built-in Kotlin are removed in AGP 10.

## Mistakes to expect from yourself

1. Calling a DI change done because it compiled.
2. Adding `@Singleton` by reflex, or expecting a module to scope a binding.
3. Bumping Kotlin, AGP, KSP or Hilt alone, when they move together.
4. A feature module that depends on another feature's implementation.
5. `api(...)` where `implementation(...)` would do.
6. Build configuration copied into a new module instead of applying the project's convention plugin.
