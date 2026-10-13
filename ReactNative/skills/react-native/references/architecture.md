# React Native: structure, state and navigation

Use this to work inside the structure a project already has, or to choose one for new code. It is never a reason to change a project's pattern. Facts checked 2026-10-13 against the libraries' documentation and the npm registry.

## Find the pattern before writing

The session profile names the state, navigation and storage libraries, and `mobile recon` counts class components, Redux usage and navigators. Read one finished feature end to end and copy its shape.

| Markers | Pattern | Where new behaviour goes |
|---|---|---|
| `createSlice`, `useSelector`, `useDispatch`, RTK Query | Redux Toolkit | a reducer or thunk in the feature's slice; components dispatch and select |
| `create(...)` stores, `useXStore(selector)` | Zustand | an action inside the store; components select the smallest piece they need |
| `atom(...)`, `useAtom` | Jotai | a new atom or a write atom |
| `useQuery`, `useMutation`, a `QueryClient` | TanStack Query for server data | a query or mutation hook next to the feature's API calls |
| `app/` or `src/app/` with `_layout.tsx` | Expo Router: files are routes | a new file in the right folder |
| `createNativeStackNavigator`, `createStaticNavigation` | React Navigation | a screen entry in the navigator and its types |

## Two kinds of state

- **Server data** (anything the backend owns) belongs in a server-state cache: TanStack Query or RTK Query. Loading and error states, caching, refetching and retries come from it. Do not copy fetched data into a client store "to have it globally": that creates a second source of truth.
- **Client state** (form drafts, toggles, the signed-in session, a wizard's progress) belongs in the project's store, or in component state when only one screen needs it.
- In React Native, TanStack Query does not know about connectivity or app focus: wire `onlineManager` to NetInfo (or `expo-network`) and `focusManager` to `AppState` once at start-up, or refetch-on-reconnect and refetch-on-focus do nothing.
- Keep derived values out of state: compute them in selectors.
- One store library per app. Do not add a second for one screen.

## Structure

- Group by feature: a folder holds the screens, components, hooks, state and API calls of one feature. Shared UI and utilities live in their own place. A feature does not import from another feature's internals.
- Screens are thin: they read state through hooks and render. Logic lives in hooks and plain functions that can be tested without rendering.
- Side effects (network, storage, native modules) sit behind small modules that features import, so a test can replace them. React context is the usual way to hand a client or service to a subtree; a module-level singleton is common too. Follow the project.
- Platform differences go in `.ios.tsx` / `.android.tsx` files or behind `Platform.select`, not in scattered conditionals.
- TypeScript: keep `strict` on. Do not add `any`, `@ts-ignore` or `as unknown as` to get past an error; the type is telling you about a real case.

## React Navigation (7.x is stable; 8 is alpha)

- Version 7's static configuration: `createNativeStackNavigator({ screens: {...} })`, rendered once with `createStaticNavigation(RootStack)`. Many projects still use the dynamic `<Stack.Navigator>` form: follow the file.
- Types: with the static API, declare `RootNavigator` once (`declare module '@react-navigation/native'`), and type screen params with `StaticScreenProps<{...}>`. Param lists are `type` aliases, not interfaces.
- Version 7 behaviour that differs from 6: `navigate` no longer goes back to a screen that is already in the stack (use `popTo`), and a nested screen is reached with `navigate('Parent', { screen: 'Child' })`.
- Pass ids in params, not objects. Params are part of the navigation state and of deep links.
- Use the native stack unless a screen needs something it cannot do. A custom `header` turns off native large titles and search bars.

## Expo Router

- Routes are files under `app/` or `src/app/`: `_layout.tsx` wraps a folder, `[id].tsx` is a parameter, `(group)` folders do not appear in the URL, `+not-found.tsx` is the fallback.
- Its major version equals the Expo SDK's (57 on SDK 57). From SDK 56 the app must not import `@react-navigation/*`; the same things come from `expo-router`.
- Typed routes are on with `experiments.typedRoutes`. Navigate with `router.push('/orders/42')` or `<Link href=...>`.
- Do not mix a hand-built React Navigation tree into an Expo Router app.

## Deep links

- A custom scheme is set in the app config (Expo) or the native projects (bare). Universal Links and App Links also need the domain association files on the server; without them the link opens the browser.
- Declare the mapping once: `linking` in React Navigation, the file tree in Expo Router. Test from a terminated app (`npx uri-scheme open`, `xcrun simctl openurl`, `adb shell am start`).
- Validate every parameter that arrives in a link, and never put a token or a secret in one.

## A default for new code

Expo with Expo Router and TypeScript; TanStack Query for server data; one small client store (Zustand or Redux Toolkit) only when component state is not enough; features in folders; native settings through app config. State the choice in a design document (`mobile-core:design`).

## Mistakes to expect from yourself

1. Fetched data copied into a client store, then kept in sync by hand.
2. A second state or navigation library for one screen.
3. Logic written inside a screen component where it cannot be tested.
4. An object passed through navigation params instead of its id.
5. `navigate` used to go back to an earlier screen in React Navigation 7.
6. `@react-navigation/*` imports in an Expo Router app.
