---
name: review
description: Reviews a mobile code change for defects that reach users. Checks correctness, lifecycle and state loss, concurrency, data-migration safety, backward compatibility, security and privacy, accessibility, performance and test integrity, and reports verified, severity-ranked findings. Use when asked to review a diff, branch, commit or pull request in a mobile project, or to check a change before it is merged.
argument-hint: "[base branch or commit; default is the merge base with the base branch]"
allowed-tools: Bash(mobile risk *) Bash(git diff *) Bash(git log *) Bash(git show *) Bash(git merge-base *) Bash(git status *)
---

# Mobile code review

Review the change, not the codebase. The output is a short list a busy engineer will act on: each finding real, tied to a line, the worst first.

## 1. Collect the facts

1. Run `mobile risk` (with `--base <ref>` if one was given). It reports schema, permission, minimum-version, signing, dependency and test-integrity signals. Every `block` and `warn` must be answered in the review, either as a finding or as "checked: fine because ...".
2. `git diff <base>...HEAD --stat`, then the diff. Read each hunk with enough surrounding code to know what calls it and what it calls. Read the tests in the diff as carefully as the code.
3. Find what the change is meant to do: the task, the description, the commit messages. A change that does something other than its stated intent is a finding.

## 2. Look for what breaks on a device

Go through this once per change. Skip what the diff cannot affect.

- **Correctness.** Wrong condition, missing case, off-by-one, an error path that swallows or mislabels, state left inconsistent after a failure, a wrong default.
- **Lifecycle and state.** Work started and never cancelled. State lost on rotation, backgrounding, process death or scene disconnection. Callbacks into a destroyed screen. A second subscription on re-entry.
- **Concurrency.** UI touched off the main thread or actor. Shared mutable state without isolation. The main thread blocked. Tasks that outlive their owner. Long work that cannot be cancelled. Re-entrancy. A new compiler escape hatch.
- **Data.** A stored shape changed without a migration. A migration not tested against old data. A destructive fallback. Cache invalidation. Dates, money and numbers across time zones and locales.
- **Backward compatibility.** An API newer than the minimum OS without a guard. Behaviour that differs by OS version. A server-contract change that app versions already in the field cannot handle. Removed deep links, changed analytics names.
- **Security and privacy.** Secrets in code. Tokens or personal data in logs, analytics or crash reports. Credentials in plain preferences. Weakened transport security. Unvalidated input from a deep link, intent or web view. Exported components. A permission the feature does not need.
- **Accessibility.** Unlabelled controls, fixed font sizes, touch targets under 44 pt or 48 dp, meaning carried by colour alone, broken focus order.
- **Performance.** Work on the main thread or in the render path (`body`, composition, `build`). Unbounded lists or images. N+1 network or database calls. Leaks. A heavier app start.
- **Tests.** Does a test fail without the change? Do the assertions mean anything? Was anything skipped, deleted or loosened? Is the risky path covered?
- **Scope.** Unrelated edits, drive-by refactors, formatting noise, leftover debug code.

What each of these looks like in Swift, Kotlin or Dart is in the platform skill. Load the reference that matches the riskiest part of the diff (`concurrency.md`, `persistence.md`, `release.md`) instead of relying on memory.

## 3. Verify each finding before reporting it

Open the code and confirm the path is reachable and the claim is true. Where it is cheap, prove it: a failing test, a compile check, a one-line reproduction. Drop what you cannot support. Leave out style a linter would catch, personal preference, and existing problems the diff did not touch (mention those once at the end if serious).

## 4. Report

```
## Verdict: ship | fix first | needs discussion
<Two sentences: what the change does and the main concern, if any.>

## Findings
1. [blocker|major|minor] <file>:<line> <the defect in one sentence>
   Scenario: <input or state, and what goes wrong for the user>
   Evidence: <what you checked or ran>
   Suggested fix: <the smallest change>

## Risk signals answered
- <signal from mobile risk>: <finding number, or why it is fine>

## Not covered
<What could not be checked here, such as: not run on a device, backend contract not visible.>
```

**blocker**: data loss, a crash, a security or privacy exposure, a broken migration, or it cannot ship. **major**: wrong behaviour for real users, or a regression risk with no test. **minor**: worth fixing, not worth blocking. An empty findings list is a valid review: say what you checked.
