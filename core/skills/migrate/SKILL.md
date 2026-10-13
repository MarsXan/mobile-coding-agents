---
name: migrate
description: Plans and carries out an incremental migration or major upgrade in a mobile codebase so the app stays shippable after every step. Covers UIKit to SwiftUI, callbacks or Combine to async/await, Swift 6 language mode, CocoaPods to SwiftPM, Views to Compose, RxJava or LiveData to coroutines and Flow, kapt to KSP, AGP and Gradle upgrades, Flutter state-management and navigation changes, and SDK or dependency upgrades. Use when asked to migrate, upgrade, convert, modernise or replace a framework, pattern, language version or build tool.
argument-hint: "<from> to <to> [scope]"
---

# Migrate incrementally

A migration is finished when the old thing is gone and nothing regressed. The plan is what makes that possible; the edits are the easy part.

## 1. Inventory: facts, not estimates

- `mobile recon` counts the old and the new pattern and names the files that hold the most. Add an exact search for the specific API being replaced.
- Record the baseline in the plan: N occurrences in M files, per module. That number reaching zero is the progress metric.
- Read the official migration guide for the versions **this project uses** before proposing steps. A version-specific guide overrides memory. The platform skill's `legacy.md` and `build.md` list the traps of the common migrations.

## 2. Decide the end state and how old and new coexist

- The target state in one paragraph, and the non-goals: what stays as it is.
- **Coexistence rule.** How old and new live side by side until the end (hosting controllers, `ComposeView` and `AndroidView`, adapter types, a bridging protocol) and which way dependencies may point. New code may reach old code through the adapter. Old code never grows.
- **Freeze rule.** From now on, no new uses of the old pattern. Enforce it mechanically where possible: a lint rule, a banned-API check in CI, or the `mobile recon` count not rising.

## 3. Slice

Each slice is independently shippable and reversible.

1. **Enablers first.** Tool and version prerequisites, the adapter layer, test seams, missing characterization tests (`mobile-core:safe-change`).
2. **Leaves before trunks.** Modules nothing depends on, simple screens and pure logic first; shared components next; the app shell and navigation last.
3. **One risk per slice.** A migration slice never also changes behaviour, bumps a dependency or redesigns a screen.
4. **Reviewable size.** One slice fits one pull request, under roughly 400 changed lines. A purely mechanical rename may be larger if it is only mechanical.
5. **Vertical over horizontal.** One feature fully migrated is testable end to end; one layer migrated everywhere is not.

## 4. Gate every slice

Write these into the plan. A slice is done only when all hold:

- It builds, `mobile verify --level test` passes, and no suppression was added.
- The behaviour pinned before the slice still passes: characterization tests, snapshots or goldens, the UI test of the migrated flow.
- `mobile risk` shows no unexplained signal.
- The checks migrations usually break, from the platform skill: lifecycle and state restoration, accessibility of the migrated screen, list and startup performance, binary size.
- The old-pattern count dropped by the expected amount.

## 5. Write the plan, then execute one slice at a time

Write `docs/agent/migrations/<name>.md` from [references/plan-template.md](references/plan-template.md) and get agreement before large-scale edits. Then, per slice: implement, verify, run `mobile risk`, summarise, stop for review. Do not stack the next slice on an unreviewed one unless told to.

Across many modules, the read-only assessment can run in parallel: `/mobile-core:migration-audit` examines every module and proposes the order. Execution stays sequential.

## Traps

- **Big-bang branch.** A long-lived migration branch rots. Merge slices to the main line under the coexistence rule.
- **Translating syntax instead of behaviour.** Frameworks differ in threading, lifecycle, error and cancellation semantics. A Combine publisher is not an `AsyncSequence`; `observeOn(mainThread())` is not `flowOn(Dispatchers.Main)`; a view controller's lifecycle is not a SwiftUI view's. Test the difference.
- **Skipping versions.** Upgrade build tools and SDKs one major version at a time, clearing deprecations and getting a clean build at each stop.
- **Upgrade plus migration in one step.** A dependency bump that also changes an API is two slices.
- **Deleting the old path early.** Keep it until the new one has shipped and been observed in production, then delete it in its own slice.
