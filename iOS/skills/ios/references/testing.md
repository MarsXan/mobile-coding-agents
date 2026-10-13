# iOS: testing

## Which framework

- **Swift Testing** (`import Testing`, `@Test`, `#expect`, `#require`) for new unit tests when the toolchain supports it (Xcode 16 / Swift 6 or later; check).
- **XCTest** stays for UI tests (`XCUIApplication`) and performance tests (`measure`); Swift Testing does neither.
- Both run in one target under `xcodebuild test`. Do not convert an existing XCTest suite unless that is the task.
- **Do not mix assertion families** unless the toolchain is Swift 6.4 or later, where they interoperate. Before that, an `XCTAssert` inside an `@Test` function fails silently: the test passes whatever the result.

| XCTest | Swift Testing |
|---|---|
| `XCTAssertEqual(a, b)` | `#expect(a == b)` |
| `try XCTUnwrap(x)` | `try #require(x)` |
| `XCTAssertThrowsError` | `#expect(throws: SomeError.self) { ... }` |
| `setUp` / `tearDown` | the suite's `init` / `deinit` |
| `XCTestExpectation` | `await` the async call, or `await confirmation { ... }` |
| `throw XCTSkip` | a `.disabled("reason")` or `.enabled(if:)` trait |

Swift Testing runs tests in parallel, including inside a suite. Shared mutable state (singletons, a common `UserDefaults` suite, files) that XCTest tolerated will make tests interfere. Give each test its own state, or mark the suite `.serialized` and say why.

## Writing tests that mean something

- A test must fail without the change it covers. Run it against the old code once to see it fail.
- Assert on behaviour and outputs, not on which private methods were called.
- **Async**: `await` directly. No `sleep`. For time, inject a `Clock` and advance it. Main-actor code is tested from a `@MainActor` test.
- **Doubles**: a protocol and a hand-written fake beat a mocking framework. Network: a `URLProtocol` stub registered on an ephemeral `URLSessionConfiguration`. Core Data: an in-memory store. SwiftData: `ModelConfiguration(isStoredInMemoryOnly: true)`. `UserDefaults`: a unique `suiteName` per test, removed afterwards.
- **View controllers**: call `loadViewIfNeeded()`; drive appearance with `beginAppearanceTransition` and `endAppearanceTransition`; put the controller in a window when the responder chain matters.
- **Migrations**: a fixture store written by each shipped version, opened by the current code. See `persistence.md`.

## Snapshot tests

- Fix the device, OS, traits and locale. Rendering differs between Xcode versions, OS versions and host architectures, so the simulator used for snapshots is pinned for the whole team and CI.
- Recording is off in CI. A re-recorded reference image is a change to what the test accepts: look at it, and say in the summary that images were re-recorded and why.
- Do not lower `precision` or `perceptualPrecision` to get a test green. A tolerance is a team decision; `mobile risk` reports when one changes.

## UI tests

- Find elements by `accessibilityIdentifier`, never by visible text: text is localised and changes.
- Wait for state with `waitForExistence(timeout:)` or an expectation on a predicate. Never `sleep`.
- Launch arguments and environment put the app in a test mode: stubbed network, animations off, clean state. Every test launches its own app instance.
- Keep UI tests for the few flows that must not break. Everything a unit or snapshot test can prove should be proved there.
- An accessibility audit can run as a UI test: `try app.performAccessibilityAudit()` (Xcode 15+). Add it for screens the change touches.

## Flaky tests

1. Reproduce: `xcodebuild test -only-testing:<id> -test-iterations 50 -run-tests-until-failure`.
2. Classify: fails alone (timing, async, animation) or only in a suite (shared state, order: retry with `-parallel-testing-enabled NO`).
3. Fix the cause: wait on a condition, isolate state, inject time. A retry, a longer sleep or a skip hides it.
4. The sanitizers in the test plan (Thread Sanitizer, Main Thread Checker) often name the race directly.

## Coverage and results

```sh
xcodebuild test ... -enableCodeCoverage YES -resultBundlePath out/Tests.xcresult
xcrun xcresulttool get test-results summary --path out/Tests.xcresult
xcrun xccov view --report --json out/Tests.xcresult
```

Coverage says what ran, not what was checked. A critical path with coverage and no assertion is still untested.
