# Kotlin Multiplatform: tests

Facts checked 2026-10-13 against kotlinlang.org, developer.android.com and the libraries' repositories.

## Where tests go and how they run

- Tests for common code live in `commonTest` and use `kotlin.test` (`@Test`, `assertEquals`, `assertFailsWith`). They are compiled and run once **per target**: a test can pass on the JVM and fail on iOS.
- Tasks: `./gradlew :<module>:allTests` runs every target; `jvmTest` and `iosSimulatorArm64Test` run one. iOS tests need a Mac. Reports are under `<module>/build/reports/tests`.
- Platform-specific tests go in the platform's test source set: `iosTest`, and for Android `androidHostTest` (JVM unit tests) and `androidDeviceTest` (instrumented) with the Android multiplatform library plugin, or `androidUnitTest` and `androidInstrumentedTest` in older projects. With the new plugin both are off until enabled (`withHostTest {}`, `withDeviceTest {}`).
- Run the iOS tests, not only the JVM ones, when a change touches `expect`/`actual`, threading, serialization of platform types, or anything in `iosMain`. The JVM run says nothing about those.

## Coroutines and flows

- `runTest` from `kotlinx-coroutines-test`. It skips delays and has a 60-second default timeout.
- Inject dispatchers. In a test pass a `StandardTestDispatcher` or `UnconfinedTestDispatcher` that shares the test scheduler.
- **`Dispatchers.Main` in a native test**: nothing processes the main queue in a unit-test process, so code that uses it hangs. Call `Dispatchers.setMain(testDispatcher)` in `@BeforeTest` and `Dispatchers.resetMain()` in `@AfterTest`.
- Test a `Flow` with Turbine (`flow.test { awaitItem() ... }`), which is multiplatform. For a `StateFlow`, remember that equal values are conflated: assert on the states that matter, not on a count of emissions.

## Test doubles

- Prefer hand-written fakes for the interfaces in common code. Mocking libraries that rely on JVM reflection or bytecode generation do not work on native targets; a mock that works in `jvmTest` will not compile or run in `iosSimulatorArm64Test`.
- A fake repository backed by an in-memory list, and Ktor's `MockEngine` for the HTTP client, cover most shared logic.
- For storage, test against a real database: an in-memory driver for SQLDelight or Room, created per test.

## Schema and serialization tests

- A database schema change needs a test that opens a database created by the previous version and migrates it. SQLDelight can verify migrations against stored schema files (`verifyMigrations`); Room has its migration test helper on Android and the same idea applies in common code.
- JSON that is stored or exchanged with a server: a test that decodes a payload written in the old shape. `kotlinx.serialization` fails on unknown keys unless the `Json` instance sets `ignoreUnknownKeys`; check what the project's instance does before adding a field on the server side of a contract.

## Compose Multiplatform UI tests

- The API is experimental: `runComposeUiTest { setContent { ... } }` with `@OptIn(ExperimentalTestApi::class)`, in `commonTest`, with the `org.jetbrains.compose.ui:ui-test` dependency.
- They run per target with the usual test tasks. The Android run needs the extra test manifest and JUnit 4 artifacts and runs as an instrumented test.
- Snapshot tests are per platform. Do not compare an iOS render with an Android reference.

## The Swift side

A change to the shared API is tested in two places: Kotlin tests for the behaviour, and the iOS app's own tests (or at least a build of the app target) for the Swift call sites. A Kotlin test suite that passes says nothing about whether the Swift code still compiles.

## Mistakes to expect from yourself

1. Running only `jvmTest` or the Android unit tests and reporting the shared change as tested.
2. A JVM-only mocking library in `commonTest`.
3. A native test that hangs on `Dispatchers.Main`.
4. A hard-coded dispatcher or `delay` that makes a test slow or flaky.
5. Changing a stored format or a schema with no test against old data.
6. Updating a snapshot or loosening an assertion to get a target green.
