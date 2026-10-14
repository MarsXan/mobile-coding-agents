# mobile-coding-agents

An agentic engineering toolkit for mobile teams who use Claude Code. It covers native iOS, native Android, Flutter, React Native and Kotlin Multiplatform. It is a plugin marketplace with a small deterministic core and one expertise pack per stack, kept separate from application code.

It concentrates on what the skill packs surveyed in [the shortlist](docs/01-shortlist.md) cover least: understanding and changing legacy code safely, incremental migrations, stored-data safety, release guards, and sensors that give the same answer every time.

Version 0.3.0, built and tested with Claude Code 2.1.296 in October 2026.

## Fast by default

Guardrails that stop a person at every step make agent work slower than working alone. This toolkit is built not to do that.

- **It refuses instead of asking.** A secret pasted into source, a hand edit to a generated file or a lockfile, a force push to a protected branch: the agent is told why and takes the right route. Nobody is interrupted.
- **It asks a person only before something hard to undo:** uploading or publishing a build, changing signing assets, a git command that would discard uncommitted work, skipping the repository's own checks.
- **It never sends the agent back to run a build.** If a session ends with source changes that were not verified, you get one line saying so.
- **It adds no prompts to routine work.** The settings it offers are mostly allow rules, for everyday build, test, lint, simulator and git commands.
- **Its hooks are quick:** 50 ms before a command or an edit, about 140 ms after an edit and at the end of a turn, measured on a 350,000-line iOS project.

A team that wants more can set `"prompts": "strict"` and `"verifyGate": "require"` in `.mobile-coding-agents.json`. Section 5 of the [setup guide](docs/03-setup-and-validation.md) lists exactly what each setting does.

## It follows the architecture you have

The toolkit brings no architecture of its own. It finds the pattern a project uses and keeps new code inside it.

- **One line at session start.** `mobile detect` counts pattern markers in file names (coordinators, routers, presenters, interactors, view models, use cases, repositories, blocs and cubits) and tells the agent what it found. When the project has coordinators or routers, the line adds that they own navigation. In a test app that navigates through a coordinator, the bare model sent a new screen through the coordinator in 8 of 16 runs and pushed it from the view controller in the other 8. With this line it used the coordinator in 16 of 16.
- **Notes for working inside a pattern.** Every pack has an `architecture.md`, and the iOS, Android and Flutter packs have a `modules.md`. They cover MVVM, MVI, VIPER, layered ("Clean") code, TCA, BLoC, Riverpod and Redux-style stores; coordinators, routers, Navigation 3, go_router, React Navigation and Expo Router; dependency injection with Hilt, Koin, Factory, swift-dependencies and get_it; Swift packages and Tuist, Gradle convention plugins, pub workspaces and melos.
- **Counts for a migration.** `mobile recon` reports the same markers, so a move from one pattern to another has a number that goes down.

On the model tested, the notes changed no outcome: the agent already kept a VIPER module, a layered Android feature and a BLoC page intact without help, and it already knew the four dated facts it was asked about. They are a checked reference, not a measured gain. Changing a project's pattern is a migration, which `mobile-core:migrate` covers.

## Documentation

| Document | What is in it |
|---|---|
| [Shortlist of existing tools](docs/01-shortlist.md) | what to use beside this toolkit, what each costs, exact install commands, and what to check on your own machine first |
| [Architecture](docs/02-architecture.md) | what is reused, what is built, which mechanism does which job, and what each guardrail can promise |
| [Setup and validation](docs/03-setup-and-validation.md) | install, configure, sandbox settings tested per toolchain, and how to prove the setup helps |
| [Learning roadmap](docs/04-learning-roadmap.md) | seven stages from using an agent to leading a team that does |

## What is in the box

```
.claude-plugin/marketplace.json   the marketplace: six plugins
core/                             mobile-core
  bin/mobile                        CLI: detect, verify, recon, risk, doctor, adopt, hook
  lib/mobilekit/                    its code (Python 3.9+, standard library only)
  hooks/hooks.json                  session facts, shell guard, edit guard, lint on edited lines, stop notice
  skills/                           recon, safe-change, migrate, diagnose, review, design, release-check
  agents/                           cartographer (maps code), reviewer (fresh-context review)
  workflows/migration-audit.js      read-only, parallel assessment of every module for a migration
  templates/                        AGENTS.md, CLAUDE.md, settings fragments, path-scoped rules, CI jobs, Keel fragments
  tests/                            126 unit tests
  evals/                            8 eval cases for the core alone
iOS/  Android/  Flutter/          one skill each, with nine reference files: build, legacy, architecture,
                                  modules, concurrency, persistence, testing, performance, release; plus a
                                  one-line session-start pointer to the skill. Flutter also wires the Dart analyzer.
ReactNative/                      one skill, eight reference files: build, legacy, architecture, native,
                                  persistence, testing, performance, release
KotlinMultiplatform/              one skill, five reference files: build, shared-code, swift-api, architecture,
                                  testing. It works beside the Android pack, and the iOS pack when the iOS app
                                  is in the same repository.
evals/                            12 eval cases that load a platform pack with the core
scripts/check.sh                  every static check in one command (free: no model calls)
scripts/sandbox-probe.sh          does a command work inside Claude Code's sandbox with these settings?
docs/                             the four documents above
```

## Quick start

Install the plugins from GitHub, inside Claude Code:

```
/plugin marketplace add MarsXan/mobile-coding-agents
/plugin install mobile-core@mobile-coding-agents
/plugin install mobile-ios@mobile-coding-agents
```

Use `mobile-android`, `mobile-flutter`, `mobile-react-native` or `mobile-kotlin-multiplatform` in place of `mobile-ios`, or install several. Each pack needs `mobile-core`. A React Native repository needs only its own pack. A Kotlin Multiplatform repository takes its pack together with `mobile-android`.

To look before installing, or to adopt the toolkit in a repository, work from a checkout:

```sh
git clone https://github.com/MarsXan/mobile-coding-agents
cd mobile-coding-agents

# 1. Check the toolkit itself (about 30 seconds, no model calls)
scripts/check.sh

# 2. See what it says about a project, without changing anything
core/bin/mobile doctor --root /path/to/your/app
core/bin/mobile recon  --root /path/to/your/app

# 3. Try it for one session, nothing installed
cd /path/to/your/app
claude --plugin-dir "/path/to/this/toolkit/core" --plugin-dir "/path/to/this/toolkit/iOS"

# 4. Adopt it in a repository (writes a small overlay; never overwrites)
cd /path/to/your/app
"/path/to/this/toolkit/core/bin/mobile" adopt --dry-run
"/path/to/this/toolkit/core/bin/mobile" adopt
```

Details, team installation from git, and sandbox settings are in [docs/03-setup-and-validation.md](docs/03-setup-and-validation.md).

## The `mobile` command

| Command | What it does | Calls a model |
|---|---|---|
| `mobile detect` | platforms, minimum OS versions, toolchain versions and the architecture pattern, read from project files | no |
| `mobile verify --level quick\|test\|full` | runs the project's checks and prints only failures with file and line | no |
| `mobile recon` | sizes, legacy-pattern and architecture-marker counts, largest files, churn hotspots | no |
| `mobile risk` | schema changes without migrations, new permissions, weakened tests, secrets, in the current diff | no |
| `mobile doctor` | toolchain, project overlay, risky permission rules, always-on context | no |
| `mobile adopt` | writes the project overlay | no |

Inside a Claude Code session with the plugin enabled, `mobile` is on the path. Anywhere else, call `core/bin/mobile`.

## What was verified, and what was not

Verified on the machine this was built on (macOS 26, Xcode 26.0, Flutter 3.44.8, Claude Code 2.1.296):

- 126 unit tests pass on Python 3.13 and on the system Python 3.9.
- All six plugins and the marketplace pass `claude plugin validate --strict`.
- Always-on cost: about 1,230 tokens for the core, 250 to 275 for each platform pack.
- `detect`, `recon` and `doctor` were run read-only against a production iOS codebase of about 350,000 lines. `detect`, architecture counts included, takes about 90 ms there.
- `detect`, `recon`, `doctor`, `risk` and `verify --dry-run` were run read-only on three public Android apps: Now in Android, Architecture Samples and Sunflower. No Gradle task ran.
- Toolchain behaviour inside Claude Code's sandbox, for SwiftPM, `xcodebuild`, `simctl` and Flutter.
- The eval suite, 20 cases, three runs per arm on Sonnet, on this version: with the plugins it scores 0.98, without them 0.80. Six cases fail without them (a live key written to source, a generated Dart file hand-edited, a generated `Info.plist` hand-edited in an Expo app, a deep link that only works while the app is running, no measurement before a performance fix, no behaviour pinning before a legacy refactor). Thirteen cases come out the same either way. Details in the setup guide.
- Overhead on the six cases that edit code, against no plugin in the same batch: 8% more turns, 27% more cost, and about the same time (14.5 against 14.2 seconds). Turns and cost per task are unchanged from 0.2.0. With the stop gate of 0.1.0 the overhead was 38% in turns, 51% in cost and 56% in time.
- The architecture line at session start, on a coordinator-based test app: the agent went through the coordinator in 16 of 16 runs with the plugins and in 8 of 16 without.
- Hook time on that iOS codebase: about 50 ms before a command or an edit, about 140 ms after an edit and at the end of a turn.
- One live session confirming that the end-of-turn notice reaches the person and does not send the agent back.
- Session-start facts reaching the model, and the Dart language server answering through the Flutter pack, in a live session.
- Installing from GitHub into a clean Claude Code configuration: the marketplace, then `mobile-core` and `mobile-ios`.

Not verified:

- Anything Android or Kotlin Multiplatform beyond parsing project files: there is no JDK or Android SDK on that machine.
- Anything React Native beyond parsing project files: no React Native project was installed or built there. The parsers for TypeScript, ESLint and Jest output were tested on sample output written by hand.
- The workflow script and both CI templates in a live run. They follow the documented formats and parse.
- The adopt-then-trust path in an interactive session (the trust prompt cannot be scripted). `--plugin-dir` loading was tested.
- Any gain from the notes on architecture, dependency injection and modules. In the eval cases that could show one, the model did the right thing without them.
- Any effect on a real team's speed or defect rate. The setup guide says how to measure that.

## Licence

No licence has been chosen yet. Until one is added, the default applies: all rights reserved.
