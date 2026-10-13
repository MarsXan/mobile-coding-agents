# React Native: tests

Facts checked 2026-10-13 against reactnative.dev, docs.expo.dev and the libraries' repositories. Read the installed versions first: the test stack changed a lot between 2025 and 2026.

## The Jest setup that matches the project

| Project | Preset | Notes |
|---|---|---|
| Bare, React Native 0.85 and later | `preset: '@react-native/jest-preset'` (its own package) | `preset: 'react-native'` threw a "has moved" error in 0.85 and 0.86 and is gone in 0.87 |
| Bare, older | `preset: 'react-native'` | |
| Expo | `preset: 'jest-expo'` | mocks the native side of the Expo SDK |

- Both presets are built for **Jest 29**. Jest 30 is npm's latest; do not bump it alone.
- A package that ships untranspiled code needs to be let through `transformIgnorePatterns`. Add the one package to the existing pattern; do not replace the pattern.
- `npx jest --ci` runs once without the watcher. `mobile verify --level test` does that.

## React Native Testing Library

- **Version 14** (needs React 19): `render`, `renderHook`, `fireEvent` and `act` are **async**. Every one is awaited: `await render(<Screen />)`, `await fireEvent.press(button)`. The renderer package is `test-renderer` (matching the React minor), not `react-test-renderer`.
- **Version 13** is the React 18 line, with synchronous `render` and `fireEvent`.
- Copying a v13-style test into a v14 project gives tests that pass or fail at random, because nothing is awaited. Check `package.json` before writing one.
- Query the way a user finds things: `getByRole`, `getByLabelText`, `getByText`. `getByTestId` is the last resort. Prefer `userEvent` over `fireEvent` for presses and typing.
- Assert on what is shown, not on component state or on how many times something rendered.
- `findBy...` and `waitFor` for anything that appears after a promise. A fixed `setTimeout` in a test is a flaky test.

## Mocking

- The preset already mocks React Native's own native modules. Mock **your** native modules and third-party ones at the module boundary (`jest.mock('react-native-mmkv', ...)`), and use the library's official Jest mock when it ships one (Reanimated, Gesture Handler, AsyncStorage, safe-area-context do).
- Do not mock `react-native/Libraries/...` paths: those deep imports are type errors from 0.87 and their layout changes between versions.
- Network: mock at the HTTP layer (MSW, or a fake client passed in), not by replacing your own hooks. A test that mocks the hook under test proves nothing.
- Time: `jest.useFakeTimers()` with `userEvent.setup({ advanceTimers: jest.advanceTimersByTime })`; restore real timers after the test.
- A TanStack Query test needs a fresh `QueryClient` per test with retries off, or a failed query keeps retrying past the end of the test.
- Navigation: render the screen inside a real navigator (or Expo Router's `renderRouter`) with test params. Hand-built mocks of `useNavigation` drift from the real API.

## What to test where

- **Plain functions and hooks** (reducers, selectors, formatters, a migration of stored data): fast unit tests, most of the suite.
- **Screens**: a few tests each for what the user sees in the loading, empty, error and success states.
- **Native modules and anything with real layout, gestures or animation**: cannot be judged in Jest, which runs in Node with no native code. They need a device.

## End-to-end tests on a device

- **Maestro**: YAML flows, nothing added to the app, `testID` is matched as `id`. Works with development builds, and EAS Workflows can run it. On iOS a touchable nested in another touchable may need `accessible={false}` on the outer one to be found.
- **Detox**: officially supports a window of React Native versions that trails the newest release (0.77 to 0.84 on the build date). Check its support table before an upgrade that would leave it behind.
- Run end-to-end tests against a **release** build or a development build with the bundle embedded, not against a Metro server that may recompile mid-test.
- Keep them few: the paths that would stop a release (sign in, the main purchase or submit flow, a deep link from a terminated app).

## When a test fails

- Read the first error. A warning about `act` or an update "not wrapped in act" in v14 almost always means a missing `await`.
- A snapshot that changed is a question, not a chore: look at the diff. Do not update a snapshot, loosen a matcher or add `.skip` to get a green run. Lint suppressions and skipped tests are reported by `mobile risk`.
- "Cannot find module" for a native package inside Jest means it needs a mock or an entry in `transformIgnorePatterns`, not a change to the app code.

## Mistakes to expect from yourself

1. `preset: 'react-native'` on 0.87, or Jest 30 with a preset built for 29.
2. Unawaited `render` and `fireEvent` with Testing Library 14, or awaited ones with 13.
3. `react-test-renderer` installed next to React 19.
4. Mocking the unit under test, or a deep import path.
5. Calling a native-module change tested because Jest passed.
6. Updating snapshots in bulk after a change.
