# Shortlist: what to use beside this toolkit

Researched 2026-10-13. Every link below was opened that day. The mark after each item says how far the claim was checked:

- **T** tested or observed on the build machine while building the toolkit.
- **G** the repository was queried through the GitHub API (exists, last push, licence, not archived); its content was read by a research pass against the primary source.
- **P** read by a research pass against the primary source, not re-checked.
- **U** not verified.

The sharper statements about other projects (ten of them) were re-checked the same day against the project's own files, issue tracker or registry entry; where it helps, the file or issue is named. These are dated notes, not a ranking. Projects change: corrections are welcome as issues.

Stars are never a reason here. The reasons are: does it target mistakes agents actually make, what does it cost in every session, what runs when you install it, is it maintained, and is there any evidence it works.

## The short version

1. **Start with what Claude Code already has.** Most "frameworks" re-implement plan mode, subagents, review and memory with more tokens.
2. **Install this toolkit** for the layer the tools below cover least: legacy work, migrations, stored-data safety, release guards, deterministic sensors.
3. **Add at most one specialist skill per real gap**, per platform. More skills is not more capability: in SkillsBench, tasks given two or three focused skills gained 19 points, tasks given four or more gained 10, and "comprehensive" documentation gained under 1 ([arXiv 2602.12670](https://arxiv.org/abs/2602.12670), **P**).
4. **Measure and prune.** `claude plugin details <name>` shows the per-session cost; `/skill-doctor` shows what never fires.

## Tier 0: already in Claude Code 2.1.296 (**T**, from the docs downloaded on the build date)

| Capability | Use it for | Instead of |
|---|---|---|
| Plan mode, built-in `Explore` and `Plan` subagents | reading and planning without edits | spec frameworks for ordinary work |
| `/code-review`, `/security-review` | general review | third-party review plugins |
| Auto mode with `permissions.ask` and `deny` | few prompts, a classifier in front of risky actions | bypass-permissions mode |
| OS sandbox for shell commands | a real filesystem and network boundary | trusting command patterns |
| `claude plugin eval` | measuring a plugin with and without it loaded | opinion |
| `claude plugin details`, `/skill-doctor`, `/context`, `/usage` | context cost and actual use | guessing |
| LSP tool with language-server plugins | definitions and references without reading files | grep across a large repository |
| `AGENTS.md` read natively (since 2.1.277) | one instruction file for every tool | per-tool copies |

## iOS

| Tier | What | Take from it | Install | Cost and risk |
|---|---|---|---|---|
| 1 | Apple's documentation as Markdown, and the guides bundled in Xcode (**T**: 20 files in `Xcode.app/Contents/PlugIns/IDEIntelligenceChat.framework/.../AdditionalDocumentation/`) | first-party text on recent APIs | nothing: add `.md` to a `developer.apple.com/documentation/...` URL | none |
| 1 | [Xcode MCP server](https://developer.apple.com/documentation/xcode/giving-external-agents-access-to-xcode) (**P**) | build, test, previews, debugger from Apple | `claude mcp add --transport stdio xcode -- xcrun mcpbridge` | needs Xcode 26.3+ with the project open. Not tried: the build machine has Xcode 26.0 |
| 1 | [swift-lsp](https://github.com/anthropics/claude-plugins-official/tree/main/plugins/swift-lsp) (**T**: in use on the build machine) | symbol navigation | `/plugin install swift-lsp@claude-plugins-official` | none in context. For `.xcodeproj` apps sourcekit-lsp may need a build-server bridge (**U**) |
| 1 | [twostraws/SwiftUI-Agent-Skill](https://github.com/twostraws/SwiftUI-Agent-Skill) (**G**, MIT, pushed 2026-10-07; **T**: read from an installed copy) | SwiftUI API review written against model habits | `/plugin marketplace add twostraws/SwiftUI-Agent-Skill` then `/plugin install swiftui-pro@swiftui-agent-skill` | 122-line skill, 12 references, no evals. A SwiftUI reviewer: it prefers SwiftUI over UIKit, says "never use GCD", and has style rules that are noisy on old code. Use it for review, not as a legacy guide |
| 1 | [AvdLee/Swift-Concurrency-Agent-Skill](https://github.com/AvdLee/Swift-Concurrency-Agent-Skill) (**G**, MIT, 2026-09-14) | the deepest Swift 6 migration reference | `npx skills@latest add https://github.com/avdlee/swift-concurrency-agent-skill --skill swift-concurrency` | Markdown only. `npx skills` sends install telemetry unless `DISABLE_TELEMETRY=1` |
| 1 | [AvdLee/Core-Data-Agent-Skill](https://github.com/AvdLee/Core-Data-Agent-Skill) (**G**, MIT) | staged and deferred migrations, threading, history | `npx skills add https://github.com/avdlee/core-data-agent-skill --skill core-data-expert` | Markdown only |
| 1 | SwiftLint (**T**: 0.59.1 installed), swift-format | deterministic checks for hooks and CI | `brew install swiftlint` | none |
| 2 | [getsentry/MobileBuildMCP](https://github.com/getsentry/MobileBuildMCP) (**G**, MIT, 2026-10-09; formerly XcodeBuildMCP) | headless build, simulator, LLDB, UI automation | `claude mcp add MobileBuildMCP -- npx -y mobilebuildmcp@latest mcp` | `@latest` is unpinned; reports errors to Sentry unless `MOBILEBUILDMCP_SENTRY_DISABLED=true`. Tier 2 only because `mobile verify` already covers build and test output; adopt it when you want the agent to drive the simulator |
| 2 | [xcsift](https://github.com/ldomaradzki/xcsift) (**G**, MIT) | compact build output | `brew install xcsift` | installs a hook that rewrites `xcodebuild`; one maintainer. Redundant with `mobile verify` |
| 2 | [Axiom](https://github.com/CharlesWiltgen/Axiom) (**G**, MIT, pushed daily) | the broadest iOS legacy coverage found | `/plugin marketplace add CharlesWiltgen/Axiom` | by its README, 276 skills, 42 agents and 17 commands. Read it for ideas, and measure the context cost before enabling all of it for a team |
| 2 | AvdLee SwiftUI Expert, Swift Testing skills, App Store Connect CLI (`asc`), sosumi.ai, [apple/xcode-project-format](https://github.com/apple/xcode-project-format) (**G**) | Instruments trace scripts; release automation; the JSON project file | see each README | add only when the need is real |

Not considered: [Periphery](https://github.com/peripheryapp/periphery), because its repository is archived (**G**).

**What these cover least** (and this toolkit's iOS pack targets): UIKit lifecycle and memory, Objective-C interop, CocoaPods to SwiftPM, the scene-lifecycle requirement, xcconfig layering and signing failures, app size, and how the toolchain behaves inside the sandbox.

## Android

Nothing in this section was tested locally: the build machine has no JDK and no Android SDK.

| Tier | What | Take from it | Install | Cost and risk |
|---|---|---|---|---|
| 1 | [android/skills](https://github.com/android/skills) (**G**, Apache-2.0, pushed 2026-10-12), Google's own | `agp-9-upgrade`, `edge-to-edge`, `navigation-3`, `r8-analyzer`, `android-profiler`, `migrate-xml-views-to-jetpack-compose` | one skill: `android skills add r8-analyzer --project=.` Whole plugin, as its README writes it: `/plugin install android-skills --marketplace android/skills` | the plugin loads all 25 skills including TV, Wear and XR (about 2.3k tokens of descriptions): cherry-pick. No evals in the repository (**P**) |
| 1 | [Android CLI](https://developer.android.com/tools/agents/android-cli) (**P**) | current docs search, device inspection, IDE diagnostics, with no MCP schema cost | `brew tap android/tap`, `brew install android-cli`, `android init` | closed binary; usage metrics on by default (`--no-metrics`) |
| 1 | [chrisbanes/skills](https://github.com/chrisbanes/skills) (**G**, Apache-2.0, pushed 2026-10-13) | the best Compose and coroutines content found | `/plugin marketplace add chrisbanes/skills` then `/plugin install chrisbanes-skills@chrisbanes-skills` | has evals, none recorded for Claude |
| 1 | [gradle/gradle-skills](https://github.com/gradle/gradle-skills) (**G**, Apache-2.0) | build logic practice, with published A/B evals | `/plugin marketplace add gradle/gradle-skills` then `/plugin install gradle-skills@gradle-skills` | generic Gradle, not AGP-specific |
| 1 | Android Lint, ktlint or Spotless, compose-rules, Roborazzi | the deterministic ground truth | Gradle plugins | none |
| 2 | [Kotlin/kotlin-agent-skills](https://github.com/Kotlin/kotlin-agent-skills) (**G**) | Java to Kotlin conversion procedure | `claude plugin marketplace add Kotlin/kotlin-agent-skills` | its RxJava table (`references/frameworks/RXJAVA.md`) maps `observeOn(mainThread())` to "`flowOn(Dispatchers.Main)` or collect on Main". Only the second keeps the meaning, because `flowOn` changes where the upstream runs; this toolkit's `legacy.md` covers the difference |
| 2 | kotlin-lsp | navigation in pure-Kotlin modules | `brew install JetBrains/utils/kotlin-lsp`, `/plugin install kotlin-lsp@claude-plugins-official` | alpha; open issues on Android modules (**P**) |
| 2 | Firebase MCP (Crashlytics), skydoves Compose skills and compose-stability-analyzer, Develocity | crash triage; Compose stability as a CI gate | see each README | Firebase's default exposes write tools: pass `--only crashlytics` |

**Where the official skills stop**: [Android Bench 2.0](https://developer.android.com/bench) (**P**) reports the best agent passing 32.7% of long tasks, with every XML-to-Compose and Navigation 3 migration task failing, residual failures in dark theme and state lost on rotation, and agents raising screenshot thresholds or deleting assertions to pass. None of the skills surveyed treats LiveData to StateFlow, Room migrations, process death or TalkBack in depth, and RxJava to Flow appears only as a mapping table. The Android pack and the guards here target those.

## Flutter

| Tier | What | Take from it | Install | Cost and risk |
|---|---|---|---|---|
| 1 | Dart language server (**T**: `dart language-server` exists in Dart 3.12.2) | analyzer-backed navigation and diagnostics | shipped in this toolkit's Flutter pack as `.lsp.json`; there is no official Dart LSP plugin | **T**: exercised in a live session; document symbols came back for a real file. Uses the `dart` on the path, which for an fvm-pinned project may not be the project's SDK |
| 1 | [Dart and Flutter MCP server](https://github.com/dart-lang/ai/tree/main/pkgs/dart_mcp_server) (**G**, BSD-3) | run-time errors, widget tree, hot reload on a running app | `claude mcp add --transport stdio dart -- dart mcp-server` | experimental; tool names changed between Dart releases; recent SDKs fetch the server from pub.dev unpinned; sends analytics (**P**). Opt-in, not wired by default |
| 1 | [marionette_mcp](https://github.com/leancodepl/marionette_mcp) (**G**, Apache-2.0) | drive a running app to verify a change | `flutter pub add marionette_flutter`, `dart pub global activate marionette_mcp`, `claude mcp add --transport stdio marionette -- marionette_mcp` | pre-1.0, debug and profile builds only, needs a binding in the app |
| 2 | [VGV AI Flutter plugin](https://github.com/VeryGoodOpenSource/vgv-ai-flutter-plugin) (**G**, MIT) | the best-engineered pack found: 15 skills, a reviewer, 102 two-arm eval cases | `claude plugin marketplace add VeryGoodOpenSource/very-good-claude-code-marketplace && claude plugin install vgv-ai-flutter-plugin` | a hook (`hooks/scripts/block-cli-workarounds.sh`) denies `flutter test`, `dart test` and `flutter create` in favour of Very Good CLI. A good fit for a Bloc and VGV-style codebase; elsewhere it gets in the way |
| 2 | [flutter/agent-plugins](https://github.com/flutter/agent-plugins) (**G**, BSD-3), official | `dart-resolve-package-conflicts`, the FFI skills | `claude plugin marketplace add flutter/agent-plugins` then `claude plugin install dart-flutter@dart-flutter` | 25 skills, most of them produced from documentation by the repository's own generator with a model (`tool/generator/`), and aimed at new projects more than existing ones (**P**). Cherry-pick |
| 2 | Patrol, Maestro, Sentry or Firebase crash tools, DCM | native-dialog E2E; black-box flows; crash triage; unused code | see each README | add when the need is real |

Not considered: [custom_lint](https://github.com/invertase/dart_custom_lint), whose repository is archived (**G**), and golden_toolkit, which pub.dev marks as discontinued.

**What these cover least** (and the Flutter pack targets): GetX and other state-management migrations, Navigator 1.0 to go_router, null-safety on very old code, native build failures inside a Flutter project, and stored-data migrations.

## Cross-platform

| Tier | What | Take from it | Install | Cost and risk |
|---|---|---|---|---|
| 1 | [Maestro](https://github.com/mobile-dev-inc/Maestro) (**G**, Apache-2.0) | the only device tool whose output is a replayable test file | `curl -fsSL "https://get.maestro.mobile.dev" \| bash` (read it first), then `claude mcp add maestro -- maestro mcp` | 10 tools; needs Java 17; analytics on by default (`MAESTRO_CLI_NO_ANALYTICS=true`); no physical iOS devices |
| 1 | [claude-code-action](https://github.com/anthropics/claude-code-action) (**G**, MIT) | review in GitHub CI with your own skill | `/install-github-app` | GitHub only. For GitLab, use the job in `core/templates/ci/gitlab-ci.yml` |
| 1 | [ast-grep](https://github.com/ast-grep/ast-grep) (**G**, MIT) | structural search and banned-API checks for Swift, Kotlin and Dart | `brew install ast-grep` | none in context; a good enforcer for a migration's freeze rule |
| 1 | skill-creator (official) | with/without benchmark while writing a skill | `/plugin install skill-creator@claude-plugins-official` | enable only while authoring |
| 2 | [obra/superpowers](https://github.com/obra/superpowers) (**G**, MIT) | four good disciplines: systematic debugging, verification before completion, TDD, writing plans | `/plugin install superpowers@claude-plugins-official` | loads its bootstrap skill into every session, and that skill tells the agent to invoke a skill at "even a 1% chance" that one applies (`skills/using-superpowers/SKILL.md`). This toolkit's `diagnose` and `safe-change` cover the same ground for mobile without a bootstrap |
| 2 | Sentry MCP, Firebase MCP, Figma MCP, mobile-mcp | production crashes; designs; black-box device control | see each README | scope them (Sentry to a project, Firebase with `--only`); mobile-mcp sends telemetry per tool call unless disabled |
| 2 | `npx skills` | trying a skill quickly | `npx skills add <owner/repo>` | sends telemetry; pin with `owner/repo#tag`. For a team, install through a plugin marketplace pinned to a commit |
| 2 | spec-kit or OpenSpec | specs that must outlive a session | see READMEs | at most one, and only if plan mode plus a design document is not enough |
| 2 | Context7 | library docs on demand | `npx ctx7 setup` | documentation text reaches the agent as its publishers wrote it, so treat it as untrusted input (**P**) |
| 2 | [rtk](https://github.com/rtk-ai/rtk) (**T**: 0.40.0 on the build machine) | shorter shell output | see its README | open issues report swallowed exit codes and green summaries on failing runs ([#3492](https://github.com/rtk-ai/rtk/issues/3492), [#4421](https://github.com/rtk-ai/rtk/issues/4421)). If you use it, keep build and test commands out of its rewriting |

## A stricter harness: Keel (**T**)

[Keel](https://github.com/MarsXan/keel) 0.5.1, by the same author, already solves governance: approvals bound to content, a fail-closed stop gate, a tokenising shell policy, canaries, and `claude plugin eval` suites. This toolkit deliberately does not rebuild any of that. `02-architecture.md` explains how the two fit, and `core/templates/keel/` has the configuration fragments for mobile.

## Before installing anything: what `mobile doctor` usually finds

Much of the cost and risk in an agent setup is there before any new tool is added. `mobile doctor` reports most of these for any project.

| Finding | Why it matters | Suggested action |
|---|---|---|
| A `CLAUDE.md` of several hundred lines | sent with every request; long context files measurably raise cost and are followed less ([arXiv 2602.11988](https://arxiv.org/abs/2602.11988); Anthropic's own limit is 200 lines) | cut to under 150 lines of facts the code cannot tell; move procedures into skills and path-scoped rules |
| User-level agents written for other stacks | their descriptions load in every session of every project; eight such agents were measured at about 2,450 tokens | move them into the projects that use them, under `.claude/agents/` |
| Plugins for unrelated work enabled everywhere | skill listings and connector tools in mobile sessions | disable them per mobile repository with `enabledPlugins` |
| An instruction file that describes a hook which is no longer installed | instructions that are false today | remove the import, or reinstall the hook |
| Wildcard allow rules in user settings for network tools and interpreters, with no deny rules | together they allow sending any file anywhere | delete the wildcard network and interpreter rules |
| `skipDangerousModePermissionPrompt: true` | bypass mode can start without its warning | remove; use auto mode |
| The same skill installed at user and project scope | duplicate | keep the project-scope one |
| Sandbox off, no secret scanner | permission rules and hooks are not a boundary | see `03-setup-and-validation.md` |

## Vetting anything third-party before it reaches the team

Malicious and careless skills are common: one audit of 3,984 skills found a critical issue in 13.4% and confirmed 76 as malicious; scanners disagree with each other on over a third of skills ([Snyk](https://snyk.io/blog/toxicskills-malicious-ai-agent-skills-clawhub/), arXiv 2609.17274, **P**). A plugin "can execute arbitrary code on your machine" ([Claude Code docs](https://code.claude.com/docs/en/plugins/security)).

1. **Read every file**: `SKILL.md`, scripts, `hooks/hooks.json`, `.mcp.json`, `bin/`, each skill's `allowed-tools`, and the full MCP tool descriptions.
2. **Refuse**: download-and-run steps, base64 or `eval`, instructions fetched from a URL at run time, anything that asks to disable a safeguard.
3. **Pin**: a commit SHA or a tag, exact MCP package versions, marketplace auto-update off. Mirror into your own GitLab and install from there.
4. **Measure**: `claude plugin details <name>` before enabling it for everyone; `/skill-doctor` a month later.
5. **Re-review on every update.** A package can turn hostile in a later version; one MCP server did after 15 clean releases (**P**).
