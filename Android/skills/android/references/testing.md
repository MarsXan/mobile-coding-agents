# Android: testing

## Where a test lives and how it runs

| Kind | Source set | Runs on | Command |
|---|---|---|---|
| Unit (plain Kotlin and Java, Robolectric) | `src/test` | the JVM | `./gradlew :module:testDebugUnitTest --tests 'pkg.ClassTest'` |
| Instrumented (Espresso, Compose UI, real database) | `src/androidTest` | a device or emulator | `./gradlew :module:connectedDebugAndroidTest -Pandroid.testInstrumentationRunnerArguments.class=pkg.ClassTest` |
| Screenshot | depends on the library | usually the JVM | the library's `record` and `verify` tasks |

Reports: `module/build/reports/tests/`. Machine-readable results: `module/build/test-results/`. Use the test framework the module already uses; do not add a second one.

## Coroutines and ViewModels

- `runTest` with a `StandardTestDispatcher`. Replace `Dispatchers.Main` with a test-dispatcher rule. Inject every other dispatcher.
- Advance virtual time (`advanceUntilIdle()`, `advanceTimeBy`); never `Thread.sleep` or a real `delay`.
- A `StateFlow` built with `SharingStarted.WhileSubscribed` emits only while collected: collect it in `backgroundScope` during the test.
- Fakes over mocks: a hand-written fake repository is clearer and survives refactoring.
- A ViewModel that reads saved state is constructed with `SavedStateHandle(mapOf(...))`.

## What agents skip, and what to add for a UI change

Public benchmarks of agents on Android tasks show the same residual failures. Cover them explicitly:

1. **State restoration.** Compose: `StateRestorationTester`. Views: `ActivityScenario.recreate()`. Assert the state the user had is still there.
2. **Dark theme and a large font scale.** A screenshot or UI test in each.
3. **The app actually starts.** After a dependency-injection, manifest or navigation change, a launch smoke test (instrumented or Robolectric) exercises the real graph. Compiling is not enough.

## Compose UI tests

- `createComposeRule()`, or `createAndroidComposeRule<Activity>()` when the Activity matters.
- Find nodes by semantics: text, content description, or `Modifier.testTag` for things with no stable text.
- The rule waits for Compose to be idle. For other asynchrony use `waitUntil { }`, not sleeps. Control animations with `mainClock`.
- Many Compose tests run on the JVM with Robolectric, which is faster than a device.

## Espresso (Views)

- `ActivityScenario` and `launchFragmentInContainer`. Each test sets up its own state.
- Asynchrony the framework cannot see needs an idling resource, or better, injected test dispatchers so the app itself is deterministic.
- Animations are off on test devices (`testOptions.animationsDisabled = true`).

## Screenshot tests

- Use the library the project has (Roborazzi, Paparazzi, or AGP's own screenshot testing). Each has a task that records references and one that verifies against them.
- Pin device, density, locale, font scale and theme. Record light and dark, default and large font, and right-to-left for components that changed.
- A re-recorded reference is a change to what the test accepts. Look at the images and say in the summary that they were re-recorded and why.
- Never raise a diff threshold to get green. `mobile risk` reports when one changes.

## Database

- DAO tests against `Room.inMemoryDatabaseBuilder`.
- Migrations with `MigrationTestHelper`. See `persistence.md`.

## Hilt

`@HiltAndroidTest` with `HiltAndroidRule`, replacements through `@TestInstallIn`, and a test runner that uses `HiltTestApplication`.

## Accessibility as a test

- Views: `AccessibilityChecks.enable()` in Espresso tests makes every interaction run the accessibility checks.
- Compose: enable accessibility checks on the test rule where the project's Compose version supports it.
- `./gradlew lintDebug` reports missing content descriptions and similar issues.

## Flaky tests

Reproduce by running the single test in a loop. Then classify: real time or animation, a dispatcher that was not injected, shared static state, order dependence, or the network. Fix that cause. A retry rule, a sleep or `@Ignore` hides it, and the guard asks for approval before a test is skipped.
