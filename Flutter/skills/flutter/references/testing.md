# Flutter: testing

## Commands

```sh
flutter test                                        # unit and widget tests
flutter test test/cart_test.dart --name "applies discount"
flutter test --exclude-tags golden                  # tag slow or environment-bound tests
flutter test --coverage                             # writes coverage/lcov.info
flutter test --test-randomize-ordering-seed random  # exposes order dependence
flutter test integration_test                       # on a device or emulator
```

Pure Dart packages use `dart test`. Use the test and mocking libraries the project already has.

## Widget tests

- Give the widget what it needs: wrap it in the app's `MaterialApp`, theme, localisation and providers. Projects usually have a `pumpApp` helper; use it or add one.
- `pump()` advances one frame; `pump(duration)` advances time; `pumpAndSettle()` runs until no frame is scheduled and **times out on an endless animation** such as a progress indicator. Use `pump(duration)` there.
- The test runs in a fake-async zone. Real timers, real network and real file I/O do not complete. Inject fakes, or wrap genuinely real work in `tester.runAsync`.
- Network images fail in tests. Provide a fake image provider or the mock the project uses.
- Find by `Key`, type, text or semantics label. Prefer keys and semantics for things whose text is localised.
- Size, pixel ratio, text scale, platform and locale are test inputs: set them explicitly and reset them in a tear-down (`addTearDown(tester.view.reset)`, `debugDefaultTargetPlatformOverride = null`).
- Platform channels are faked with `setMockMethodCallHandler`; `SharedPreferences.setMockInitialValues({})` for preferences.

## State holders

- Bloc and Cubit: `blocTest` with `build`, `act` and `expect`.
- Riverpod: a `ProviderContainer` with overrides, disposed in a tear-down.
- Fakes over mocks. A hand-written fake repository is clearer than a chain of stubs and survives refactoring.
- Global service locators keep state between tests: reset them in `tearDown`, or tests pass alone and fail together.

## Golden tests

- Text renders as blocks unless fonts are loaded in the test; load the app's fonts through the project's golden setup.
- Pixels differ across operating systems, GPUs and Flutter versions. References are generated in one environment only, usually CI's. A golden that passes on a laptop and fails in CI is this, not a bug.
- `--update-goldens` changes what the test accepts. Look at the images, and say in the summary that they were regenerated and why. Never loosen a comparator tolerance to get green.
- Cover the states that break: light and dark, a large text scale, a narrow and a wide size, right-to-left.

## Integration tests

| Need | Tool |
|---|---|
| A flow inside the Flutter UI on a device | `integration_test` |
| Native dialogs, permissions, notifications, web views | Patrol, if the project uses it |
| Black-box flows written by QA, replayable in CI | Maestro; it sees `Semantics`, not `Key`s, so give controls a semantics identifier |

Keep these for the few journeys that must not break. Everything a widget test can prove belongs in a widget test.

## Accessibility checks in tests

```dart
final handle = tester.ensureSemantics();
await expectLater(tester, meetsGuideline(androidTapTargetGuideline));
await expectLater(tester, meetsGuideline(labeledTapTargetGuideline));
await expectLater(tester, meetsGuideline(textContrastGuideline));
handle.dispose();
```

Add them for screens the change touches.

## The analyzer is a test

`flutter analyze` with the project's `analysis_options.yaml` must be clean. Do not relax a rule or add `// ignore:` to pass; the guard asks for approval when a suppression is added.

## Flaky tests

Reproduce with a randomised order and repeated runs. The causes are almost always: `pumpAndSettle` against an ongoing animation, a real timer or network call, shared global state, or golden environment drift. Fix that cause; a retry or a skip hides it.
