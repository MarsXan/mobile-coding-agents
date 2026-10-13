# Forces that shape mobile designs

Each is a question to answer in the design, with the consequence of ignoring it. Keep only the ones that apply.

## You do not control the installed base

- **Old app versions stay in use for months or years.** Which server contract does each installed version speak? Every API change must be additive or versioned, and removal waits for the last version that needs it. Is there a forced-upgrade mechanism, and a minimum supported version the server can enforce?
- **A release takes hours to days to reach users** and cannot be recalled. What can be changed without a release: remote flags, server-driven configuration, a kill switch for the new path?
- **Fragmentation.** Which OS versions, screen sizes, densities and device classes must work? What is the behaviour on the oldest supported OS: a guarded fallback or a hidden feature?

## The device is hostile to assumptions

- **The network is slow, flaky or absent.** What does every screen show with no connection, with a 30-second timeout, with a half-finished request? Are writes queued, and are they idempotent when retried?
- **The OS kills the process at will.** What state must survive a kill in the background (in-progress forms, navigation position, an upload)? Where is it stored, and how is it restored?
- **Background time is rationed.** What needs to run when the app is not in front: sync, upload, location, push handling? Which sanctioned mechanism covers it (BGTaskScheduler, background URLSession; WorkManager, a foreground service with a declared type), and what happens when the OS does not grant the time?
- **Memory, battery, storage and size are budgets.** What is the largest list, image or dataset, and what bounds it? What does the feature cost at app start?

## Data on the device is forever

- **Every stored format is a public contract with your own future versions.** What is the schema version, how is each change migrated, and how is a migration tested against data written by old versions? What happens if migration fails halfway?
- **Sync and conflicts.** If data is edited offline or on two devices, who wins, per field or per record, and how does the user learn of a conflict? What is the source of truth?
- **Deletion and privacy.** What must be deleted on sign-out or account deletion, including caches, keychain or keystore items, files and push tokens?

## The platform has rules

- **Permissions and privacy.** Which permissions, at what moment, with what explanation, and what works when the user says no or later revokes it? What must be declared (iOS privacy manifest and usage descriptions, Google Play data safety)? Does a third-party SDK collect data on the app's behalf?
- **Store policy and review.** Does the feature touch payments, account deletion, user-generated content, background location, health or children's data? Those carry review requirements that can block a release.
- **Lifecycle.** How does the feature behave across rotation and resizing, split screen, backgrounding, an incoming call, low-power mode, a locale or text-size change while running?
- **Security boundary.** The app binary and everything in it is readable by an attacker, and the device may be compromised. What must therefore live on the server? Where are tokens stored (Keychain, Keystore-backed storage), and what is validated from deep links, intents, pasteboard and web content?

## The team has to live with it

- **Module boundaries and build time.** Which module owns the feature, what does it depend on, and does it lengthen every build?
- **Shared or per-platform.** If iOS and Android (or a Flutter and a native part) both implement this, what is specified once (API contract, analytics names, error codes, test vectors) so the implementations cannot drift?
- **Observability.** Which logs, metrics and crash breadcrumbs will tell you it is failing in production, and are they free of personal data?
- **Accessibility and localisation** as design inputs: dynamic text, screen readers, right-to-left, long translations, colour contrast.
