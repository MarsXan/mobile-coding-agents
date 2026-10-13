---
name: safe-change
description: Changes existing mobile code without changing behaviour that was not asked for. Pins current behaviour with characterization tests before refactoring, keeps structural and behavioural changes apart, and verifies after each step. Use when refactoring, fixing a bug in code that has no tests, touching legacy or unfamiliar code, or when asked to clean up, simplify, rename, extract or restructure existing code.
---

# Safe change

The code in front of you runs on users' devices today. Its current behaviour, including behaviour that looks like a bug, is the specification until someone decides otherwise.

## Before editing

1. **State the change in one sentence and classify it.** *Structural*: behaviour stays identical. *Behavioural*: something observable changes. Never both in one step. If the task needs both, do the structural step first and verify it alone.
2. **Find what depends on it.** Callers (language server or search), subclasses and overrides, tests, and the references a rename will not catch: Objective-C selectors and `@objc` names, storyboards and XIBs, manifest entries, reflection, dependency-injection registrations, platform channels, serialized names (JSON keys, database columns, preference keys), deep links, analytics event names, remote-config keys.
3. **Check the safety net.** Run the existing tests for the area. Note which behaviours they pin and which they do not.

## Pin behaviour that has no test

Write characterization tests before changing untested code.

- Assert what the code **does now**, not what it should do. If the output looks wrong, pin it anyway and report it. Do not fix it inside a refactor.
- Cover the branches you are about to touch, the boundaries (empty, nil or null, zero, negative, very long, non-ASCII, other time zones and locales for dates and money) and the error paths.
- For UI, prefer a snapshot or golden test of the affected screen states over assertions about the view tree.
- Where the code cannot be tested as written (hidden dependencies, singletons, static calls), create a **seam** with the smallest change that preserves behaviour: extract a method, or pass the dependency in with a default argument equal to the old value. Build, then write the test.
- Run the new tests against the unchanged code and see them pass. A characterization test that never passed on the old code pins nothing.

## Change in small steps

- One step, one reason, one verification. Rename, move, extract, inline: each on its own.
- Keep the diff minimal. Do not reformat, reorder imports, rename nearby things or modernise untouched code. Unrelated improvements go in a list for the user, not in the diff.
- Preserve public signatures, serialized names and threading behaviour unless changing them is the task. If other modules call a signature that must change, keep the old one as a deprecated forwarding shim for a release.
- After each step, build and run the pinned tests. If a characterization test fails after a structural step, the step changed behaviour: revert the step. Do not edit the test.

## When behaviour must change

- Change the test first so it states the new behaviour, watch it fail for the right reason, then change the code.
- A risky behaviour change in a shipped app goes behind a flag with the old path intact, so rollback does not need a store release.
- Name the user-visible effect and any stored-data effect in the summary.

## Finish

Run `mobile verify --level test` and `mobile risk`. Report what changed, what was pinned and by which tests, what was deliberately left alone, and anything that looks like an existing bug.

## Never

- Edit, weaken, skip or delete a test to make a refactor pass.
- Delete code as unused on search evidence alone; check the dynamic references listed above.
- Mix formatting changes into a file with a long history.
