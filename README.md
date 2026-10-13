# mobile-coding-agents

An agentic engineering toolkit for iOS, Android and Flutter teams who use Claude Code. It is a plugin marketplace with a small deterministic core and one expertise pack per platform, kept separate from application code.

It concentrates on what the skill packs surveyed in [the shortlist](docs/01-shortlist.md) cover least: understanding and changing legacy code safely, incremental migrations, stored-data safety, release guards, and sensors that give the same answer every time.

Version 0.2.0, built and tested with Claude Code 2.1.296 in October 2026.

## Fast by default

Guardrails that stop a person at every step make agent work slower than working alone. This toolkit is built not to do that.

- **It refuses instead of asking.** A secret pasted into source, a hand edit to a generated file or a lockfile, a force push to a protected branch: the agent is told why and takes the right route. Nobody is interrupted.
- **It asks a person only before something hard to undo:** uploading or publishing a build, changing signing assets, a git command that would discard uncommitted work, skipping the repository's own checks.
- **It never sends the agent back to run a build.** If a session ends with source changes that were not verified, you get one line saying so.
- **It adds no prompts to routine work.** The settings it offers are mostly allow rules, for everyday build, test, lint, simulator and git commands.
- **Its hooks are quick:** 50 ms before a command or an edit, about 140 ms after an edit and at the end of a turn, measured on a 350,000-line iOS project.

A team that wants more can set `"prompts": "strict"` and `"verifyGate": "require"` in `.mobile-coding-agents.json`. Section 5 of the [setup guide](docs/03-setup-and-validation.md) lists exactly what each setting does.

## Documentation

| Document | What is in it |
|---|---|
| [Shortlist of existing tools](docs/01-shortlist.md) | what to use beside this toolkit, what each costs, exact install commands, and what to check on your own machine first |
| [Architecture](docs/02-architecture.md) | what is reused, what is built, which mechanism does which job, and what each guardrail can promise |
| [Setup and validation](docs/03-setup-and-validation.md) | install, configure, sandbox settings tested per toolchain, and how to prove the setup helps |
| [Learning roadmap](docs/04-learning-roadmap.md) | seven stages from using an agent to leading a team that does |

## What is in the box

```
.claude-plugin/marketplace.json   the marketplace: four plugins
core/                             mobile-core
  bin/mobile                        CLI: detect, verify, recon, risk, doctor, adopt, hook
  lib/mobilekit/                    its code (Python 3.9+, standard library only)
  hooks/hooks.json                  session facts, shell guard, edit guard, lint on edited lines, stop notice
  skills/                           recon, safe-change, migrate, diagnose, review, design, release-check
  agents/                           cartographer (maps code), reviewer (fresh-context review)
  workflows/migration-audit.js      read-only, parallel assessment of every module for a migration
  templates/                        AGENTS.md, CLAUDE.md, settings fragments, path-scoped rules, CI jobs, Keel fragments
  tests/                            92 unit tests
  evals/                            8 eval cases for the core alone
iOS/  Android/  Flutter/          one skill each, with seven reference files: build, legacy, concurrency,
                                  persistence, testing, performance, release; plus a one-line session-start
                                  pointer to the skill. Flutter also wires the Dart analyzer.
evals/                            6 eval cases that load a platform pack with the core
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

Use `mobile-android` or `mobile-flutter` in place of `mobile-ios`, or install several. Each platform pack needs `mobile-core`.

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
| `mobile detect` | platforms, minimum OS versions, toolchain versions, read from project files | no |
| `mobile verify --level quick\|test\|full` | runs the project's checks and prints only failures with file and line | no |
| `mobile recon` | sizes, legacy-pattern counts, largest files, churn hotspots | no |
| `mobile risk` | schema changes without migrations, new permissions, weakened tests, secrets, in the current diff | no |
| `mobile doctor` | toolchain, project overlay, risky permission rules, always-on context | no |
| `mobile adopt` | writes the project overlay | no |

Inside a Claude Code session with the plugin enabled, `mobile` is on the path. Anywhere else, call `core/bin/mobile`.

## What was verified, and what was not

Verified on the machine this was built on (macOS 26, Xcode 26.0, Flutter 3.44.8, Claude Code 2.1.296):

- 92 unit tests pass on Python 3.13 and on the system Python 3.9.
- All four plugins and the marketplace pass `claude plugin validate --strict`.
- Always-on cost: about 1,270 tokens for the core, about 230 for each platform pack.
- `detect`, `recon` and `doctor` were run read-only against a production iOS codebase of about 350,000 lines.
- Toolchain behaviour inside Claude Code's sandbox, for SwiftPM, `xcodebuild`, `simctl` and Flutter.
- The eval suites, three runs per arm on Sonnet: with the plugins the suite scores 0.99; five cases fail without them (a live key written to source, a generated file hand-edited, a deep link that only works while the app is running, no measurement before a performance fix, no behaviour pinning before a legacy refactor). Details in the setup guide.
- Overhead with the 0.2.0 defaults, on the six cases that edit code: 17% more time and 31% more cost per task than no plugin. With the stop gate of 0.1.0 it was 56% and 51%.
- Hook time on that iOS codebase: about 50 ms before a command or an edit, about 140 ms after an edit and at the end of a turn.
- One live session confirming that the end-of-turn notice reaches the person and does not send the agent back.
- Session-start facts reaching the model, and the Dart language server answering through the Flutter pack, in a live session.
- Installing from GitHub into a clean Claude Code configuration: the marketplace, then `mobile-core` and `mobile-ios`.

Not verified:

- Anything Android beyond parsing project files: there is no JDK or Android SDK on that machine.
- The workflow script and both CI templates in a live run. They follow the documented formats and parse.
- The adopt-then-trust path in an interactive session (the trust prompt cannot be scripted). `--plugin-dir` loading was tested.
- Any effect on a real team's speed or defect rate. The setup guide says how to measure that.

## Licence

No licence has been chosen yet. Until one is added, the default applies: all rights reserved.
