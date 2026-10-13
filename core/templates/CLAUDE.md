@AGENTS.md

## Claude Code

- The session starts with this project's facts (minimum OS versions, toolchain versions, package managers). Trust them over memory.
- Platform detail lives in one skill per platform: `mobile-ios:ios`, `mobile-android:android`, `mobile-flutter:flutter`. Load the reference file that matches the task instead of answering from memory.
- Changing code you have not read, or code without tests: `mobile-core:safe-change`. A multi-step migration or upgrade: `mobile-core:migrate`. A crash, bug, hang or slowness: `mobile-core:diagnose`.
- For a review that is not anchored on your own reasoning, delegate to the `mobile-core:reviewer` agent. For mapping a large unfamiliar area, delegate to `mobile-core:cartographer`.
