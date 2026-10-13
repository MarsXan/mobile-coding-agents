# Architecture: what to reuse, what to build, and why

## The system on one page

```
┌───────────────────────────── toolkit repository (this folder; a Claude Code plugin marketplace) ──────────────────────────────┐
│                                                                                                                               │
│  core/  mobile-core                         iOS/  mobile-ios         Android/  mobile-android     Flutter/  mobile-flutter    │
│  ├ bin/mobile        deterministic CLI      ├ skills/ios             ├ skills/android             ├ skills/flutter            │
│  ├ hooks/            5 hooks → the CLI      │   SKILL.md  router     │   SKILL.md  router         │   SKILL.md  router        │
│  ├ skills/           7 workflow skills      │   references/ ×7       │   references/ ×7           │   references/ ×7          │
│  ├ agents/           cartographer, reviewer └ hooks/  1-line pointer └ hooks/  1-line pointer     ├ hooks/  1-line pointer    │
│  │                                                                                                └ .lsp.json  Dart analyzer  │
│  ├ workflows/        migration-audit                                                                                          │
│  ├ templates/        project overlay, CI, Keel fragments                                                                      │
│  └ tests/, evals/    92 unit tests, 8 eval cases        evals/  6 cross-plugin eval cases        scripts/  check, probe       │
└───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
                 │ `mobile adopt` writes a thin overlay, never overwriting                      │ enabled per repository
                 ▼                                                                             ▼
┌─────────────────────────────────────────── application repository ───────────────────────────────────────────┐
│  AGENTS.md (yours, short)   CLAUDE.md (@AGENTS.md + 5 lines)   .mobile-coding-agents.json (verify commands)  │
│  .claude/settings.json (permission rules, enabled plugins)     .claude/rules/mobile-<platform>.md            │
│  docs/agent/CODEMAP.md (written by recon)                      CI: `mobile risk` + secret scan               │
└──────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

Four plugins rather than one, because a repository enables only what it holds: an iOS repository carries the core and the iOS pack and never sees an Android skill.

## Design rules, each with its evidence

| Rule | Evidence | What it means here |
|---|---|---|
| Always-on text is the scarcest resource | Context files "do not generally improve task success rates, while increasing inference cost by over 20%" ([arXiv 2602.11988](https://arxiv.org/abs/2602.11988)); Anthropic: keep `CLAUDE.md` under 200 lines | `AGENTS.md` template is about 35 lines and written by people. Everything else loads on demand |
| Focused beats comprehensive | Curated skills +16.6 points; two or three skills +19.0, four or more +10.1; comprehensive documentation +0.7; self-generated skills below no skills ([SkillsBench](https://arxiv.org/abs/2602.12670)) | One router skill per platform with seven short references, not thirty skills. No reference is over 100 lines. Nothing here was generated from documentation |
| A skill that is not loaded does nothing | In Vercel's evals a skill was never invoked in 56% of cases, while an always-loaded compact index reached 100% ([Vercel](https://vercel.com/blog/agents-md-outperforms-skills-in-our-agent-evals)). Measured here: core skills loaded unprompted in 1 of 5 cases on Haiku, 13 of 15 on Sonnet, 4 of 4 on Opus; platform skills in 0 of 18 on Sonnet until a session-start pointer was added | Three routes that do not depend on description matching: each platform pack prints one line at session start naming its skill; a path-scoped rule, loaded by the harness when a matching file is touched, names the reference for each task; `CLAUDE.md` carries a five-line index. Trigger cases are in the eval suite |
| What must always hold is code, not prose | "An instruction like 'never edit `.env`' in CLAUDE.md or a skill is a request, not a guarantee" (Claude Code docs) | Secrets, generated files, lockfiles, signing material and release commands are handled by hooks backed by tested code |
| A guardrail must not cost more than it saves | A prompt stops a person and a forced check stops the agent. In this toolkit's own eval runs, a stop gate that sent the agent back to verify made editing tasks 56% slower than no plugin; a one-line notice instead, 17% (`03`) | Refusals are instant and interrupt nobody. A person is asked only before something hard to undo. Nothing forces a build: unverified changes get one line at the end of the turn |
| Check state, not events | A file can be changed by `sed`, a generator or a subagent, none of which an edit hook sees | The stop notice hashes the source tree; `mobile risk` reads the diff; the lost-work guard reads the working tree. None cares how a file changed |
| Agents imitate when tests can be weakened | Agents raised screenshot thresholds and deleted assertions to pass ([Android Bench](https://developer.android.com/bench)) | The agent is told at the edit, and `mobile risk` reports new suppressions, skipped tests, looser tolerances, removed assertions and deleted tests for review. `"prompts": "strict"` turns the first three into a prompt |
| Multi-agent is expensive | Agents use about 4 times the tokens of chat, multi-agent systems about 15 times ([Anthropic](https://www.anthropic.com/engineering/multi-agent-research-system)) | Two agents, each for isolation. One workflow, read-only, for a job that is genuinely parallel |
| Speed without stability is not progress | AI adoption "improves software delivery throughput ... it still increases delivery instability"; small batches are one of the capabilities that keep the benefit ([DORA 2025](https://services.google.com/fh/files/misc/2025_state_of_ai_assisted_software_development.pdf)) | Migrations in reviewable slices; `mobile risk` warns above 400 changed lines; verification before "done" |
| Test the harness | Of the mobile skill packs surveyed, few ship evals and fewer publish results | 92 unit tests for the deterministic parts, 14 eval cases that run with and without the plugins |

## Which mechanism for which job

The question for each job is: must it happen every time, does it need judgment, and does it flood the conversation?

| Job | Mechanism | Why this one |
|---|---|---|
| Know the minimum OS, toolchain, package managers | **Script + hook**: `mobile detect` at session start (about 9 lines) | Facts, cheap to read from files, wrong when recalled |
| Run checks and show only failures | **Script**: `mobile verify` | Deterministic; a build log is thousands of lines |
| Count legacy patterns, find hotspots | **Script**: `mobile recon` | Counting is not a model's job |
| Spot schema changes without migrations, new permissions, weakened tests | **Script**: `mobile risk`, also a CI job | State-based, free, the same answer every time |
| Block generated files, lockfiles, signing material, secrets in source | **Hook** (deny) | Must hold every time, and a refusal interrupts nobody |
| Uploads, publishing, signing changes, git commands that would discard work, skipped checks | **Hook** (ask) | Needs a person, rarely happens, so the prompt is not noise |
| Edits to CI and signing configuration, new suppressions | **Hook** (a note to the agent), then `mobile risk` at review | Common enough that a prompt each time is noise; still seen by a reviewer |
| Unverified source changes at the end of a turn | **Hook** at stop: one line for the person | Costs no time: the agent is not sent back and nothing runs |
| Platform conventions while editing a file | **Path-scoped rule**, about 25 lines | Loaded by the harness, not by the model's choice |
| How to do a migration, a diagnosis, a safe refactor, a review, a design | **Skill**, loaded on demand | Procedure and judgment; needed sometimes |
| Platform depth: build failures, lifecycle, persistence, performance | **Skill reference files** | Only the one that matches the task is read |
| Mapping a large unfamiliar area | **Agent**: `cartographer` | Reading-heavy; the main conversation keeps the map, not the files |
| Reviewing a finished change | **Agent**: `reviewer` | A fresh context is not anchored on the author's reasoning |
| Assessing forty modules for a migration | **Workflow**: `migration-audit` | Truly parallel, read-only, with a verification pass on risky claims |
| Release readiness | **User-invoked skill**: `/mobile-core:release-check` | Deliberate, so it costs nothing until called |

**Deliberately not built**

- No "iOS developer", "Android developer" or "architect" persona agents. A persona adds a description to every session and a context hand-off to every task, and gives nothing a skill in the main conversation does not.
- No orchestrator, no spec-plan-build pipeline, no approval ledger. Plan mode covers the first; Keel covers the rest when you want it.
- No MCP server. The CLI does the same work with no tool schemas in context.
- No formatter-on-save hook. Reformatting a legacy file buries the real change. Lint runs on the edited lines only, and only with the project's own configuration.
- No vendored copies of other people's skills. `01-shortlist.md` says which to install beside this.

## Guardrails: layers, and what each can actually promise

| Layer | Stops | Cannot stop | Status here |
|---|---|---|---|
| Permission rules (`deny`, `ask`, `allow`) | the invocation the agent normally writes; reads of secret files | the same program invoked another way (`sh -c`, a full path). Claude Code's docs: "isn't a security boundary" | template in `core/templates/settings/` |
| Hooks in this plugin | wrapped and nested forms too (`bundle exec fastlane`, `git -C . push --force`, `sh -c 'rm -rf ~'`), by parsing the command; content of edits | a hook that fails to start: by default the action proceeds, with a visible notice. Set `onFailure: "block"` for fail-closed | 92 tests, including bypass cases |
| Auto mode classifier | irreversible and out-of-scope actions without prompts | everything: Anthropic measured 17% of overeager actions missed | recommended mode; add the entries in `03-setup-and-validation.md` |
| OS sandbox | writes outside the project and network to unlisted hosts, for every child process | `xcodebuild` and `simctl` must run outside it (tested) | settings per platform in `03` |
| CI | anything that reaches a merge request, whatever produced it | nothing local | `mobile risk` and a secret scan; the authority |
| Keel (optional) | code before an approved plan, unapproved commits and pushes, weakened tests, with fail-closed hooks | | a separate project; see below |

The plugin's hooks are a tripwire for honest mistakes. The boundary is the sandbox plus CI. Saying so plainly matters more than a longer list of patterns.

## Context budget (measured with `claude plugin details`, Claude Code 2.1.296)

| When | What loads | Tokens (estimated by the tool) |
|---|---|---|
| Every session | core descriptions (7 skills, 2 agents) | about 1,270 |
| Every session | one platform pack's description | about 230 |
| Session start | project facts, plus one line per enabled platform pack | about 10 lines |
| Touching a platform file | that platform's rule | about 25 lines |
| A skill is used | its body | 0.8k to 1.4k |
| A reference is read | one file | 33 to 95 lines |
| Hooks, CLI, workflow, tests, evals | nothing | 0 |

A single-platform repository pays about 1,500 tokens up front. For comparison, eight general-purpose user-level agents were measured at about 2,450 tokens in every project, and a 900-line `CLAUDE.md` costs many times that.

## Lifecycle coverage

| Stage | Core | Platform pack |
|---|---|---|
| Greenfield, system design | `design` skill, mobile forces, design template | architecture conventions in rules; build setup in `build.md` |
| Understanding a legacy codebase | `recon` skill, `mobile recon`, `cartographer`, code map | `legacy.md` |
| Changing legacy code, refactoring | `safe-change` skill, stop notice, lint on edited lines | `legacy.md`, `testing.md` |
| Migration and upgrades | `migrate` skill, plan template, `migration-audit` workflow, recon counts as the progress metric | `legacy.md`, `build.md` |
| Debugging | `diagnose` skill, `crash.md` | `concurrency.md`, `persistence.md` |
| Performance | `diagnose` skill, `performance.md` | `performance.md` |
| Testing | characterization tests in `safe-change`; test-integrity guards | `testing.md` |
| Review | `review` skill, `reviewer` agent, `mobile risk` | all references |
| Security, privacy, accessibility | secret and capability guards, `mobile risk` | `release.md` |
| Release | `/mobile-core:release-check`, release-command guards | `release.md` |
| Maintenance | `mobile doctor`, eval suite, `scripts/check.sh` | upgrade guidance in `build.md` |

## Portability

| Piece | Works in | Notes |
|---|---|---|
| `AGENTS.md` | Claude Code, Codex, Gemini CLI, Cursor, Copilot, Junie, Android Studio | Claude Code reads it natively when there is no `CLAUDE.md`; the template's `CLAUDE.md` imports it |
| Skills (`SKILL.md` with `name` and `description`) | every tool that supports the Agent Skills format | Frontmatter beyond the standard (`allowed-tools`, `argument-hint`, `disable-model-invocation`) is ignored elsewhere. Other tools look in `.agents/skills`; copy or link the skill folders there |
| `mobile` CLI and `mobile risk` in CI | anything with Python 3.9 | No dependency on Claude Code |
| Path-scoped rules, hooks, agents, plugin manifests, the workflow, `claude plugin eval` | Claude Code only | Other tools have equivalents with different formats and event names; none is portable |

So the knowledge and the sensors move with you. The enforcement is specific to Claude Code.

## Keel and this toolkit

They answer different questions.

| | mobile-coding-agents | Keel |
|---|---|---|
| Question | Does the agent know mobile, and are mobile-specific mistakes caught? | May the agent do this at all, and who approved it? |
| Gate style | Advisory plus tripwires; one line at stop, nothing held | Fail-closed; approvals bound to a hash of what was approved |
| Ceremony | None | Tiered: spec, plan, build, verify, review, ship |
| Stack knowledge | iOS, Android, Flutter | None by design; stack packs supply it (NestJS today) |

They compose without overlap: in a project with `.keel/config.json`, this plugin's stop notice and lint-on-edit stand down (tested), and its release, signing and device guards keep running beside Keel's shell policy. `core/templates/keel/` holds the paths, checks and banned patterns for each mobile platform, shaped to Keel 0.5.1's schema.

**Recommendation.** Use mobile-coding-agents alone for day-to-day work: it has no approval flow and holds nothing up. Keel makes the opposite trade, hard gates for a slower pace, and belongs only where one owner decides that trade is worth it. For anyone who takes that route further, the next step is real stack packs (`keel-ios`, `keel-android`, `keel-flutter`) with canaries for every checker rule; the fragments here are the starting point, and the sandbox findings in `03` are what those packs' sandbox probes need.

## Limits and assumptions

- Hooks need `python3` on the path (3.9 or later). Windows needs WSL or a `python3` alias.
- Android content was written from knowledge and the research pass. It was not built or run: the build machine has no JDK.
- The workflow script and both CI templates follow documented formats and parse, but were not run end to end. The Dart language-server wiring was exercised in a live session (document symbols returned for a real file).
- Platform facts carry dates. `release.md` files say when they were checked and where to confirm.
- Eval results in `03` are three runs per arm on one model: enough to show which way each case points, not an effect size for your team or your model.
