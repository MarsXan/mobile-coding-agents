# {{PROJECT}}

<!-- Keep this file short and written by people. Every line is sent with every
     request. Measured on real repositories, long or generated context files
     raise cost by about 20% without raising success (arXiv 2602.11988).
     Put here only what an agent cannot work out from the code. -->

{{PLATFORMS}} application.

## Facts the code does not make obvious

<!-- Replace this list with 3 to 10 lines that are true for THIS project. For example:
     - The app must work offline; the sync queue in <path> is the source of truth.
     - Module <name> is frozen until release 4.2; ask before touching it.
     - Screens under <path> are still UIKit by decision, not by neglect. -->
- (to be written by the team)

## Working rules

- **Read before you change.** In an area you have not read in this session, start from the code map (`docs/agent/CODEMAP.md`) or `mobile recon`. Do not infer structure from file names.
- **One change at a time.** A behaviour change, a refactor and a dependency bump are three changes. Do not modernise code the task does not need; propose it separately.
- **Preserve behaviour you were not asked to change.** Before refactoring code that has no tests, pin what it does today with a characterization test.
- **Minimum versions decide which APIs exist.** Guard anything newer than the oldest supported OS, with a real fallback.
- **Stored data outlives the build.** Changing a persisted model, table, key or file format needs a versioned migration and a test that opens data written by the previous version.
- **No secret in the repository or the app binary.** Build-time keys come from untracked files that CI supplies; real secrets stay on a server.
- **Views draw; they do not decide.** Every screen and reusable view has a preview for each state it draws (empty, loading, error, the longest text), built from fixture data. Rules, validation, formatting decisions and data access live where this project's pattern puts them, not in the view.
- **Do not silence a check to make it pass**: no new lint suppressions, skipped tests, looser snapshot thresholds or compiler escape hatches. Fix the cause or ask.
- **Done means verified.** Say what you ran and what it printed. If something could not be verified here, say that instead.

## Commands

- `mobile verify --level quick` after edits, `--level test` when behaviour changed, `--level full` before a pull request. It prints only failures, with file and line.
- `mobile risk` before review: schema, permission, version and test-integrity signals in the diff.
- The `mobile` command comes with the mobile-coding-agents plugin for Claude Code. In another tool, call `core/bin/mobile` from a checkout of the toolkit.

## Never without a person

- Uploading or publishing anything: TestFlight, App Store Connect, Google Play, Firebase App Distribution, an over-the-air update, pub.dev, npm.
- Changing signing material, provisioning profiles, keystores or CI secrets.
- Force-pushing, rewriting history, or deleting branches on the remote.
