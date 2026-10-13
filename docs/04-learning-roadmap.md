# Learning roadmap: from using an agent to leading a team that does

This is for a mobile engineer who already uses a coding agent every day and is about to lead a team that does. What a team lead needs on top of daily use is narrower than "learn everything": be able to say **why** each piece of the setup exists, **measure** whether it works, and **teach** it to people on platforms you know less well than your own.

Each stage has an outcome, exercises on your own code, and a test for moving on. The order is by payoff. Weeks are a guide for evenings-and-margins effort, not a schedule.

## Stage 0: Fix the ground you stand on (one evening)

**Outcome.** Your own environment is no longer costing you tokens and safety for nothing.

- Run `core/bin/mobile doctor --root <your project>` and act on the warnings. Typical ones: a `CLAUDE.md` of several hundred lines, user-level agents written for other stacks, broad allow rules, instructions for a hook that is no longer installed.
- In a session, run `/context` before and after. Write the two numbers down.
- Run `/usage` and `/skill-doctor` once so you know what they show.

**Move on when** you can say how many tokens a new session in your project spends before your first word, and what each chunk is.

## Stage 1: Operate deliberately (weeks 1 and 2)

**Outcome.** You can run the loop of explore, plan, change, verify without thinking about the tool, and you know what fills the context window.

Read:
- [Claude Code best practices](https://code.claude.com/docs/en/best-practices)
- [How Claude Code works](https://code.claude.com/docs/en/how-claude-code-works) and [the context window](https://code.claude.com/docs/en/context-window)
- [Extend Claude Code](https://code.claude.com/docs/en/features-overview): the table of which feature to use when is the map for everything after this.

Do, in the project you know best:
1. Adopt the toolkit (`03-setup-and-validation.md`). Rewrite `AGENTS.md` by hand: ten lines of facts the code cannot tell an agent.
2. `/mobile-core:recon` on one feature area. Read the code map it writes and correct it. The corrections show you what an agent gets wrong about your codebase.
3. One real ticket through `mobile-core:safe-change` on a legacy screen: characterization test first, then the change. Notice where it wanted to do more than you asked.
4. Use plan mode for one change and skip it for a similar one. Compare the diffs.
5. Run `core/bin/mobile detect` and read the architecture line. It is counted from file names, so check it against what you know: a folder of `*Presenter` files that nobody extends any more still counts. Then give the agent one small task in a coordinator or VIPER feature and see whether the new code stays inside the pattern.

**Move on when** you can predict, before pressing return, whether a prompt will need a plan, a subagent, or neither.

## Stage 2: Constrain (weeks 3 and 4)

**Outcome.** You can explain every layer of guardrail, what it guarantees and what it does not, and you have seen each one fire.

Read:
- [Permissions](https://code.claude.com/docs/en/permissions), especially "What a Bash rule doesn't match"
- [Permission modes](https://code.claude.com/docs/en/permission-modes) and [how auto mode decides](https://www.anthropic.com/engineering/claude-code-auto-mode)
- [Sandboxing](https://code.claude.com/docs/en/sandboxing), including its limitations section
- [Hooks reference](https://code.claude.com/docs/en/hooks): exit codes, and why a failing hook lets the action through by default

Do:
1. Read `core/lib/mobilekit/guards.py` and `core/tests/test_guards.py`. The tests are the specification. Add one rule your team needs (a project-specific release script, a directory nobody may edit) **test first**.
2. Trigger each guard on purpose in a scratch branch: paste a fake key, edit a `.g.dart` or `Package.resolved`, run `git reset --hard` with an uncommitted change, add a lint suppression and find it in `mobile risk`.
3. Run `scripts/sandbox-probe.sh` for your project's real build command. `03` reports that `xcodebuild` cannot be sandboxed; see it yourself, then decide your team's sandbox policy.
4. Compare with a fail-closed harness such as [Keel](https://github.com/MarsXan/keel): what does that model buy, and what does it cost in friction?

**Move on when** a teammate asks "can the agent delete my keychain or push to main?" and you can answer precisely, layer by layer, without saying "it shouldn't".

## Stage 3: Encode knowledge and measure it (weeks 5 to 7)

**Outcome.** You can turn a repeated correction into the cheapest mechanism that fixes it, and prove with a number that it did.

Read:
- [Skills](https://code.claude.com/docs/en/skills) and [skill authoring best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices): evaluations before documentation
- [Test plugins with evals](https://code.claude.com/docs/en/plugin-evals) and [measure plugin cost](https://code.claude.com/docs/en/plugins/measure)
- [SkillsBench](https://arxiv.org/abs/2602.12670) and the [context-files study](https://arxiv.org/abs/2602.11988): two papers that should change how much you write
- [twostraws/SwiftUI-Agent-Skill](https://github.com/twostraws/SwiftUI-Agent-Skill): read it as a writing sample. One imperative line per rule, the wrong API named beside its replacement

Do:
1. Keep a list for two weeks: every time you correct the agent in your project. Sort each entry: a fact (goes in `AGENTS.md`), a file-type convention (a path-scoped rule), a procedure (a skill), or a must-always (a hook or a lint rule).
2. Take the top procedure. Write the **eval case first** (`claude plugin eval init --bare <name>`), watch it fail without the skill, then write the smallest skill that makes it pass. Run it with and without (`--ablation with-without`, three runs).
3. Run the toolkit's suites on your daily model and read the report. Find a case where the delta is zero and decide: delete the skill text that case covers, or write a harder case.
4. Shorten one skill description and re-run its trigger case. Find the point where it stops loading.

**Move on when** you have deleted something you wrote because the number said it did nothing.

## Stage 4: Delegate (weeks 8 and 9)

**Outcome.** You know when a second context earns its cost, and you can run a large job in parallel without losing control of it.

Read:
- [Subagents](https://code.claude.com/docs/en/sub-agents): "choose between subagents and main conversation"
- [Dynamic workflows](https://code.claude.com/docs/en/workflows)
- [Worktrees](https://code.claude.com/docs/en/worktrees)
- Anthropic's [multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system) for the cost side: about 15 times the tokens of chat

Do:
1. Have `mobile-core:reviewer` review a change you made with the agent. Compare its findings with what the authoring session said about its own work.
2. Run `/mobile-core:migration-audit` for a migration your project still carries (`mobile recon` counts what remains). Check its plan against what you know. Look at `/usage` afterwards and decide whether it was worth it.
3. Do one migration slice by hand with `mobile-core:migrate`, and watch the old-pattern count in `mobile recon` drop.
4. Write down three jobs where a subagent would be waste.

**Move on when** you can estimate the cost of a fan-out before launching it and be roughly right.

## Stage 5: The other two platforms (weeks 6 to 12, alongside the rest)

**Outcome.** You can review agent-written Android and Flutter code for the failure modes that matter, even where you would not write that code fastest yourself.

- Install the toolchains you do not have yet. `mobile doctor` tells you what is missing.
- For each platform, read that pack's `SKILL.md` list of "mistakes to expect", then its `legacy.md` and `persistence.md`. Those two files carry most of the production risk. Read `architecture.md` next: it tells you which pattern a file name belongs to and where new behaviour goes in each.
- Build one small feature per platform with the pack enabled: a screen with state that must survive rotation, a stored model with one migration, a list with real data. Then break it on purpose (kill the process, rotate, switch to dark theme and a large font) and see what the agent missed.
- Run the Android and Flutter eval cases on your model. They were written on a machine with no Android toolchain, so they check the files an agent writes, not a build: extend them to run yours.
- Read one benchmark result page critically: [Android Bench](https://developer.android.com/bench). Note what kind of task still fails; that is where your review attention goes.
- For depth, add one specialist skill per platform from `01-shortlist.md` and measure it the same way you measured your own.
- If the team also ships React Native or Kotlin Multiplatform, do the same with those packs. Start with `legacy.md` and `native.md` for React Native, and with `shared-code.md` and `swift-api.md` for Kotlin Multiplatform. Neither pack was built or run on the machine this toolkit was written on, so treat their notes as a dated reference and add an eval case for each real incident.

**Move on when** you can read an Android or Flutter merge request written by an agent and name the two things most likely to be wrong before opening the diff.

## Stage 6: Roll out to a team (weeks 10 to 14)

**Outcome.** The setup is the team's, not yours: versioned, reviewed, measured.

Read:
- [Create and host a marketplace](https://code.claude.com/docs/en/plugins/create-marketplace), [manage plugins for your organisation](https://code.claude.com/docs/en/plugins/org), [managed settings](https://code.claude.com/docs/en/managed-settings)
- Claude Code in [GitLab CI](https://code.claude.com/docs/en/gitlab-ci-cd) or [GitHub Actions](https://code.claude.com/docs/en/github-actions)
- [DORA 2025](https://services.google.com/fh/files/misc/2025_state_of_ai_assisted_software_development.pdf): the seven capabilities that decide whether AI helps a team or destabilises it
- [Plugin security](https://code.claude.com/docs/en/plugins/security)

Do:
1. Fork or mirror this repository into your team's git host and pin a tag. Adopt it in one repository with `--marketplace <git url>` and commit the overlay through a normal merge request so the team reads it.
2. Add the two deterministic CI jobs first (`mobile risk`, secret scan). Add the model-based review job only after the team trusts the deterministic ones.
3. Write the team's rules for third-party skills and MCP servers from the vetting checklist in `01-shortlist.md`. Decide who may add one.
4. Pick four numbers and record them before the rollout: median merge-request size, share of merge requests needing rework after review, CI failure rate on the main branch, cost per merged request from `/usage`. Look again after four weeks.
5. Start a weekly fifteen minutes: what did the agent get wrong this week, and which mechanism should have caught it. A repeated mistake becomes a check, not another paragraph in `AGENTS.md`.
6. Decide whether a fail-closed harness such as Keel has a place: nowhere, in the repositories with the highest stakes, or everywhere.

**Move on when** a new team member is productive with the setup in a day and can explain why `AGENTS.md` is short.

## Stage 7: Keep it honest (ongoing)

- Re-run the eval suites when the model or Claude Code changes. A result from another model is a different result.
- Once a month: `/skill-doctor`, `claude plugin details`, and remove what is not used. A harness only grows unless someone prunes it.
- Re-check the dated facts in the `release.md` files every quarter. Store requirements move every year.
- Watch for instruction creep. If `AGENTS.md` passes 150 lines, something in it wants to be a rule, a skill or a check.

## What expert looks like

- You reach for the cheapest mechanism that works: a fact, then a rule, then a skill, then a hook, then an agent.
- You distrust any claim about an agent setup, including your own, that comes without a with-and-without number.
- You can tell a teammate which layer would stop a given mistake, and which would not.
- Your setup gets smaller over time as often as it gets bigger.
- You read agent-written code on a platform you know less well by its failure modes, not line by line.

## Habits to avoid

- Installing a large skill pack because it is popular, then never measuring it.
- Asking the agent to write its own instructions and committing the result unread. Generated context files and self-generated skills both tested at or below having none.
- Bypass-permissions mode to stop the prompts, instead of allow rules for routine commands and auto mode for the rest.
- Treating a passing build as verification, or a hook as a security boundary.
- One long session for a week of work. Context is not memory: write the code map, the plan and the migration log to files and start fresh.
