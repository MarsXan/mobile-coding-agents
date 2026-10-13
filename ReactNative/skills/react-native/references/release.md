# React Native: release, over-the-air updates and secrets

Facts checked 2026-10-13 against docs.expo.dev, reactnative.dev, Apple's and Google's policy pages and Microsoft's retirement notice. Store rules carry dates: confirm on the linked pages before a release.

## Two ways to ship a change

| | A store build | An over-the-air update |
|---|---|---|
| Carries | everything: native code, permissions, JavaScript, assets | JavaScript and assets only |
| Path | build, sign, upload, review | published to a channel, downloaded by installed apps |
| Use for | any change to native code or native dependencies, permissions, app config that prebuild writes into the native projects, an SDK or React Native upgrade | fixes and small changes to JavaScript that the installed binary can run |

**An update that needs native code the installed binary does not have crashes the app.** With EAS Update the `runtimeVersion` is the guard: an update is delivered only to builds with the same runtime version. Bump it whenever the native side changes, or use a policy that derives it (the `fingerprint` policy hashes the native project). Roll back by republishing the previous update.

Both commands, and every other publishing command, need a person: the guard asks before `eas update`, `eas submit`, `eas build --auto-submit` and `npm publish`.

## What the stores allow an update to change

- **Apple**: the Developer Program License Agreement (3.3.1(B)) allows downloaded interpreted code only if it does not change the app's primary purpose with features inconsistent with what was advertised and reviewed, does not bypass signing, the sandbox or other security features, and does not create a store for other code. App Review guideline 2.5.2 forbids code that introduces or changes features or functionality.
- **Google Play**: an app may not update itself outside Play or download executable code such as dex, JAR or `.so` files. Code that runs in an interpreter, as JavaScript does, is exempt, and must not be used to break policy.
- In practice: bug fixes and small improvements, yes. A new feature that review never saw, or turning on something hidden from review, no. When unsure it goes through the store.

## CodePush is gone

Visual Studio App Center was retired on 31 March 2025, and Microsoft's CodePush repositories are archived. A project that still has `react-native-code-push` is shipping nothing through it. The replacements are EAS Update (works in bare apps once `expo` and `expo-updates` are installed) or a self-hosted server. Moving is a migration with a native change, so it starts with a store build.

## Secrets

- **Everything in the JavaScript bundle is public.** Anyone can unpack the app and read it, Hermes bytecode included. React Native's security guide: never store sensitive API keys in app code.
- **`EXPO_PUBLIC_*` variables are inlined into the bundle** as plain text. They are for values that are not secret (a public API base URL, a publishable key). The same is true of `extra` in the app config and of `react-native-config`-style files.
- A key that grants something (a payment secret, an admin token, a private API key) stays on a server; the app calls your server.
- Build-time credentials (the Sentry auth token, store credentials, signing keys) live in the CI or EAS secret store, never in the repository or in `eas.json`.
- Session tokens on the device go in secure storage (`persistence.md`), and never in a deep link.

## Crash reports and source maps

- A release stack trace is useless without the source map for that exact bundle. Hermes builds produce a composed map (the Gradle and Xcode build steps do it).
- Sentry's React Native SDK uploads maps during native release builds. **An over-the-air update is a new bundle**: upload its map as part of the same job that publishes it (with Expo, `npx sentry-expo-upload-sourcemaps dist` after `eas update`), or crashes from that update will not symbolicate.
- Do not ship source maps inside the app or serve them publicly.

## Before a store submission

- Version and build numbers raised; with EAS, `autoIncrement` or the remote version source decides, so do not also edit them by hand.
- The release build was run on a device, not only the development build: R8 or ProGuard and Hermes release behaviour differ from debug.
- Permissions and their purpose strings match what the app does; for Expo they come from app config and plugins, so check the generated `Info.plist` and manifest after a prebuild.
- Privacy declarations: the iOS privacy manifest covers your code and every SDK; Google Play's data-safety form must match. A new SDK can change both.
- Current platform gates (build date October 2026): Google Play target API 36 and 16 KB page support; App Store uploads built with Xcode 26. See `build.md`.
- `eas submit` uploads the binary. It does not manage Play listing metadata, and a first Android release goes to the internal track.

## Mistakes to expect from yourself

1. Publishing an update for a change that added a native module or a permission.
2. Leaving `runtimeVersion` unchanged after a native change.
3. A secret in `EXPO_PUBLIC_*`, app config or the bundle.
4. Publishing an update without uploading its source map.
5. Treating an update as a way around store review for a new feature.
6. Assuming CodePush still works.
