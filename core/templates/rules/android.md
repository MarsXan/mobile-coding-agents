---
paths:
  - "**/*.{kt,kts,java}"
  - "**/*.gradle"
  - "**/AndroidManifest.xml"
  - "**/res/**/*.xml"
  - "**/libs.versions.toml"
  - "**/gradle.properties"
  - "**/*.pro"
---

# Android rules

Facts first: the session-start profile lists this project's minSdk, compile and target SDK, AGP, Kotlin and Gradle versions, and whether it uses kapt, KSP, Compose or flavors. Advice that is right for AGP 9 or Kotlin 2.x is wrong for an older project. Check before proposing a build change.

- **API levels.** An API above minSdk needs a `Build.VERSION.SDK_INT` check or an AndroidX compat class. Raising minSdk, targetSdk or compileSdk is a product decision, never a build fix.
- **Match the file you are in.** Views stay Views, Java stays Java, RxJava stays RxJava, LiveData stays LiveData, unless the task is that migration.
- **Survive the system.** State that matters survives rotation and process death: `SavedStateHandle` or `rememberSaveable` for UI state, persistence for data. Never hold a `Context`, `View` or `Activity` in a ViewModel or a singleton.
- **Coroutines.** No `GlobalScope`. No `runBlocking` on the main thread. Inject dispatchers. Never swallow `CancellationException`. Collect flows in the UI with `repeatOnLifecycle` or `collectAsStateWithLifecycle`.
- **Stored data.** A Room entity change needs a version bump, a `Migration` or `AutoMigration`, the exported schema JSON and a `MigrationTestHelper` test. `fallbackToDestructiveMigration` deletes user data and is a product decision. SharedPreferences and DataStore keys and serialized shapes are a format.
- **Manifest.** Every component with an intent filter sets `android:exported` deliberately. A new permission needs a rationale, a denial path and a data-safety check. Validate everything read from an `Intent` or deep link.
- **Build.** Change versions in the version catalog, one upgrade per change. Do not add `-dontwarn`, broad `-keep` rules, lint-baseline entries or `@Suppress` to get a green build.
- **Every composable screen and component has previews.** One `@Preview` per state that changes what is drawn (empty, loading, error, the longest text), as separate functions or through `@PreviewParameter`, plus the multipreview annotations this project's Compose version has, such as `@PreviewLightDark` and `@PreviewFontScale`. Nothing else renders a screen before someone runs the app. Previews use fixture data and never build a real ViewModel, repository or client. XML layouts keep `tools:` sample attributes.
- **No logic in composables.** Split a screen: an outer composable takes the ViewModel, collects its state and passes it down; an inner one takes the state and event lambdas, and is what previews and UI tests use. Rules, validation, formatting decisions and data access live in the ViewModel or below. Child composables get values and lambdas, never the ViewModel. Text being typed stays in synchronous Compose state: an asynchronous round trip through a `Flow` drops and reorders characters. Colours and type come from the theme.
- **Accessibility is part of done** for a UI change: content descriptions, 48dp targets, text scales, sensible TalkBack order.

Detail is in the `mobile-android:android` skill. Load the reference for the task: `build.md` (Gradle, AGP, R8), `legacy.md` (Views, Java, RxJava and LiveData migrations, Compose interop), `architecture.md` (state holders, layering, navigation structure), `modules.md` (dependency injection, modules, build logic), `concurrency.md`, `persistence.md`, `testing.md`, `performance.md`, `release.md` (security, accessibility, Play requirements).
