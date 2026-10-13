# Keel stack fragments for mobile

[Keel](https://github.com/MarsXan/keel) is a separate, stricter harness: approvals bound to content, a fail-closed stop gate, and its own tested shell policy. mobile-coding-agents does not duplicate any of that. In a project that has adopted Keel, mobile-coding-agents' stop notice and lint-on-edit stand down automatically, and its release, signing and device guards keep running beside Keel's.

These files are the mobile equivalent of `keel-nestjs/templates/keel.config.json`: the paths, checks and banned patterns to merge into a project's `.keel/config.json`.

They are **templates**, not a stack pack:

- Replace the placeholders: `APP`, `SCHEME`, `SIMULATOR` and `TOOLKIT` (the path to a checkout of this toolkit).
- Narrow `paths.source` and `paths.tests` to the project's real layout.
- Merging them into a project that already committed its Keel layer is a guardrail change and goes through `/keel:amend`.
- There are no canaries here. `keel-nestjs` proves every checker rule with a planted violation; a real `keel-ios`, `keel-android` or `keel-flutter` pack would need the same for SwiftLint, detekt or Android Lint, and the Dart analyzer. That is the next step if Keel becomes the governance layer for mobile work.

The fragments were checked for shape against Keel 0.5.1's configuration schema on the machine where this toolkit was built. They were not run through a full Keel workflow on a mobile project.
