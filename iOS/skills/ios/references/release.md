# iOS: privacy, security, accessibility, App Store

Store requirements change every year. The dates below were checked on 2026-10-13; confirm on Apple's pages before relying on them: `developer.apple.com/news/upcoming-requirements/` and `developer.apple.com/ios/submit/`.

## App Store requirements

- Uploads have needed Xcode 26 and the iOS 26 SDK since 28 April 2026. From April 2027 Apple lists the iOS 27 SDK and a minimum deployment target of iOS 15.
- Built with the iOS 27 SDK, an app must use the scene lifecycle or it will not launch. See `legacy.md`.
- Apps that create accounts must offer account deletion inside the app.
- Version (`MARKETING_VERSION`) and build (`CURRENT_PROJECT_VERSION`) must be consistent across every target, and the build number must increase for each upload.
- Release builds produce dSYMs (`DEBUG_INFORMATION_FORMAT = dwarf-with-dsym`); archive them with the build.

## Privacy

- **Purpose strings.** Every protected resource needs its `NS...UsageDescription` in `Info.plist`. Accessing one without it crashes the app.
- **Privacy manifest** (`PrivacyInfo.xcprivacy`): declare collected data types, tracking domains, and a reason for each required-reason API the app or its SDKs use (file timestamps, system boot time, disk space, active keyboards, `UserDefaults`). Listed third-party SDKs must ship their own signed manifest.
- **Ask in context**, when the user does the thing that needs the permission. Handle denied, restricted and limited (Photos) states; the feature must degrade, not dead-end. `PhotosPicker` and `PHPickerViewController` need no permission.
- **Tracking** requires App Tracking Transparency before the advertising identifier is read.
- A new SDK is a privacy change: check what it collects and whether the store privacy answers still hold.

## Security

- **Nothing secret in the binary.** Not in source, `Info.plist`, xcconfig files that are committed, or asset catalogs. Anything shipped can be extracted.
- **Tokens and credentials in the Keychain**, with a deliberate accessibility class. Never in `UserDefaults` or files.
- **Transport.** App Transport Security stays on. No `NSAllowsArbitraryLoads`; a per-domain exception needs a written reason. Pinning, if used, pins public keys with a backup pin and a rotation plan.
- **Logs.** No tokens or personal data in logs, analytics or crash breadcrumbs. With `Logger`, interpolated strings are private by default: mark only non-sensitive values `.public`.
- **Untrusted input.** Deep links, universal links, pasteboard content, push payloads and web content are attacker-controlled. Validate, and never perform a state-changing action from a link without the user confirming it.
- **Web views.** Validate the origin of script messages. Do not hand tokens to page JavaScript. Restrict navigation to expected domains.
- **Biometrics.** `LAContext.evaluatePolicy` alone returns a boolean that can be bypassed. Bind the secret to biometrics with a Keychain access control (`.biometryCurrentSet`).
- **Sensitive screens.** Hide content when the scene resigns active so it does not appear in the app switcher.
- Jailbreak detection and obfuscation delay an attacker; they do not replace server-side checks.

Reference standard: OWASP MASVS (storage, crypto, auth, network, platform, code, resilience, privacy).

## Accessibility

Part of done for any UI change:

- **VoiceOver.** Every control has a label; icon-only buttons especially. Traits are right (`.isButton`, `.isHeader`, `.isSelected`). Related elements are grouped. Reading order is sensible. State changes are announced.
- **Dynamic Type.** Text styles, not fixed sizes. In UIKit: `preferredFont(forTextStyle:)` with `adjustsFontForContentSizeCategory`. Layout adapts at the accessibility sizes: stacks switch axis, nothing essential truncates.
- **Targets** at least 44 by 44 points. **Contrast** at least 4.5:1 for text. Meaning never by colour alone.
- **Motion and transparency.** Respect Reduce Motion and Reduce Transparency.
- **Custom controls** expose a standard representation (adjustable, button) to assistive technology.
- **Check**: Accessibility Inspector audit, and `try app.performAccessibilityAudit()` in a UI test for the changed screens.

## Localisation

- Strings come from the catalog. No concatenation of translated fragments; use format strings and plural rules.
- Dates, numbers and currency go through formatters with the user's locale.
- Layout uses leading and trailing, not left and right. Check a right-to-left language and a long-text pseudo-language.

## Rollout

- Risky changes ship behind a flag that defaults off.
- Phased release limits exposure and can be paused. Decide beforehand which metric (crash-free sessions, the feature's success rate) pauses it and who watches.
- Review takes time and an approved build cannot be recalled: the rollback plan is a flag or a server change, not a new upload.
