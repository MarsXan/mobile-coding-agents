# Android: security, privacy, accessibility, Google Play

Play requirements change every year. The dates below were checked on 2026-10-13; confirm before relying on them: `developer.android.com/google/play/requirements/target-sdk`.

## Google Play requirements

- Since 31 August 2026, new apps and updates must target API 36 (Android 16). Existing apps must target API 35 or later to stay available to new users on current devices. An extension to 1 November 2026 could be requested.
- Raising targetSdk turns on that level's behaviour changes. It is its own change with its own testing. See "Behaviour that changes with targetSdk" in `legacy.md`.
- Apps with native code that target API 35 or later must support 16 KB memory pages; from 1 February 2027 updates that do not are blocked.
- The Data safety form must match what the app and its SDKs actually collect. Apps that create accounts must offer account deletion in the app and on the web.
- Sensitive permissions (SMS, call log, all-files access, background location, exact alarms, some foreground-service types, broad media access) need a declaration and may be refused. Prefer the system photo picker, which needs no permission.
- `versionCode` increases with every upload. R8 mapping files and native debug symbols are uploaded for every release.

## Security

- **Nothing secret in the APK.** Not in `BuildConfig`, resources, `strings.xml`, assets or native libraries. Anything shipped can be extracted. `local.properties` and signing files stay out of version control.
- **Components.** `android:exported` is set deliberately on every component with an intent filter; export only what other apps must reach, and protect it with a signature permission where possible. Receivers registered at run time declare `RECEIVER_NOT_EXPORTED` unless they must be public.
- **Intents.** Everything read from an incoming `Intent` or deep link is attacker-controlled: validate it. Never launch an `Intent` that arrived inside another one. `PendingIntent`s are `FLAG_IMMUTABLE` unless mutation is required. Internal communication uses explicit intents.
- **Deep links.** Verified App Links (`autoVerify`) for anything sensitive; a custom scheme can be claimed by another app. A link never performs a state-changing action without the user confirming it.
- **Network.** No cleartext traffic. A network security config with pins has a backup pin and an expiry plan. Release builds do not trust user-installed certificates.
- **Storage.** Tokens and keys are protected by the Android Keystore. Backups exclude secrets (`persistence.md`).
- **WebView.** JavaScript only when needed; no `addJavascriptInterface` for content you do not control; file access off; validate every URL loaded.
- **Biometrics.** `BiometricPrompt` with a `CryptoObject` bound to a Keystore key. A bare success callback can be bypassed.
- **Logs.** No tokens or personal data in Logcat, analytics or crash reports.
- **Sensitive screens.** `FLAG_SECURE` keeps them out of screenshots and the recents view.
- **Supply chain.** Pin dependency versions; consider Gradle dependency verification for release builds.

Reference standard: OWASP MASVS (storage, crypto, auth, network, platform, code, resilience, privacy).

## Accessibility

Part of done for any UI change:

- **TalkBack.** Icons and images that convey meaning have a content description; decorative ones have none. Related content is merged into one node. Headings are marked. Custom controls expose role, state and actions.
- **Text.** Sizes in `sp`. Layout survives a 200% font scale: nothing essential clipped or overlapped.
- **Targets** at least 48 by 48 dp. **Contrast** at least 4.5:1 for text. Meaning never by colour alone.
- **Focus.** Order follows the visual order; focus moves sensibly after navigation and when a dialog opens or closes. Dynamic changes are announced.
- **Check**: the Accessibility Scanner app; `AccessibilityChecks.enable()` in Espresso tests; accessibility checks on the Compose test rule where available; lint.

## Localisation

- Strings in resources with `<plurals>`; no concatenation of translated fragments.
- Dates, numbers and currency through `java.time` and locale-aware formatters.
- `start` and `end`, not `left` and `right`. Check a right-to-left locale and the pseudolocales (`en-XA`, `ar-XB`).

## Rollout

- Risky changes ship behind a flag that defaults off.
- Use a staged rollout. Decide beforehand which vitals (crash rate, ANR rate, the feature's success metric) halt it, and who watches.
- A halted rollout does not remove the build from devices that already have it: the rollback plan is a flag or a server change.
