# Flutter: security, accessibility, store requirements

A Flutter app is an iOS app and an Android app. Both stores' rules apply, and both change every year. If the native platform skills are installed, their `release.md` files have the current detail; the essentials are repeated here.

## Store requirements (checked 2026-10-13; confirm on the official pages)

- **Google Play**: new apps and updates must target API 36. Flutter takes `targetSdk` from the SDK version in use unless the app overrides it, so an old pinned Flutter can leave an app targeting too low. Check the value in the built manifest, not in memory.
- **App Store**: uploads need the current Xcode and SDK. From April 2027 Apple lists the iOS 27 SDK and a minimum deployment target of iOS 15. Built with that SDK, the app must use the scene lifecycle (Flutter's migration guide, from 3.38).
- **16 KB pages** on Android apply to the native libraries that plugins ship. An old plugin version can fail it.
- **Privacy**: iOS privacy manifest (the engine and current plugins ship theirs; the app declares its own use), purpose strings for every permission, Google Play's Data safety form, account deletion in the app.
- **Permissions plugins** can compile in code for permissions the app never requests, which App Store review flags. Follow the plugin's instructions for stripping unused permissions on iOS.
- Version is `version: 1.2.3+45` in `pubspec.yaml`; the build number increases with every upload.

## Secrets

- `--dart-define` and `--dart-define-from-file` values are compiled into the binary and can be read from it. A bundled `.env` asset is a plain file inside the app. Neither is a secret store.
- Client keys that must ship (maps, analytics) are restricted on the provider's side to the app's bundle identifier and signing certificate.
- Real secrets stay on a server. Tokens are kept in `flutter_secure_storage` (`persistence.md`).
- `--obfuscate` renames symbols. It does not hide strings.

## Network

- Never "fix" a TLS error with `badCertificateCallback: (_, __, ___) => true` or a global `HttpOverrides` that accepts everything. That removes TLS for every user.
- Cleartext stays off: App Transport Security on iOS, the network security config on Android.
- Certificate pinning, if used, has a backup pin and a rotation plan.

## Untrusted input

- Deep links, push payloads and web content are attacker-controlled. Validate them, and require confirmation before a link changes anything.
- In a web view: JavaScript only when needed, a navigation delegate that allows only expected hosts, and every JavaScript-channel message treated as hostile.

## Logs

`print` and `debugPrint` output is readable on the device in release builds. No tokens or personal data in logs, analytics or crash breadcrumbs. Use a logger with levels and keep verbose output out of release.

## Release build

```sh
flutter build appbundle --release --obfuscate --split-debug-info=build/symbols
flutter build ipa --release --obfuscate --split-debug-info=build/symbols
```

Archive the symbols directory, the Android R8 mapping file and the iOS dSYMs with every release, and upload them to the crash reporter. Without them stack traces from the field are unreadable (`mobile-core:diagnose`, `references/crash.md`).

Signing credentials come from untracked files and CI secrets. Uploading to a store is a person's decision; the guard asks before any release command runs.

## Accessibility

Part of done for any UI change:

- **Semantics.** Custom controls get `Semantics` (label, role, value, actions). Icons and images that carry meaning get a `semanticLabel`; decorative ones are excluded. Related content is merged with `MergeSemantics`.
- **Text scaling.** Do not clamp the text scaler to 1.0. Layout survives 200%: text wraps, rows become columns, nothing essential is clipped.
- **Targets** at least 48 by 48 logical pixels. **Contrast** at least 4.5:1 for text. Meaning never by colour alone.
- **Focus and order** follow the visual order; dynamic changes are announced.
- **Check**: `meetsGuideline` tests (`testing.md`), then TalkBack and VoiceOver on real devices. The two screen readers behave differently.

## Localisation

- Strings in ARB files through `gen-l10n`, with ICU plurals and selects. No concatenation of translated fragments.
- Dates, numbers and currency through `intl` with the user's locale.
- Directional layout: `EdgeInsetsDirectional`, `AlignmentDirectional`, `start` and `end`. Check a right-to-left locale.

## Rollout

- Risky changes ship behind a flag that defaults off.
- Use staged rollout on Google Play and phased release on the App Store. Decide beforehand which metric halts it and who watches.
- A shipped build cannot be recalled: the rollback plan is a flag or a server change. Code-push tools, where a team uses them, update Dart code only and are bound by store policy.
