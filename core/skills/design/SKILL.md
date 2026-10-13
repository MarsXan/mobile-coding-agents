---
name: design
description: Designs a mobile feature, subsystem or architecture change before code is written, as a short decision document with options, trade-offs, rollout and build order. Covers offline and sync, state and navigation architecture, modularisation, API contracts and versioning, persistence, background work, push, deep links and feature flags. Use when asked to design, architect or evaluate an approach for an iOS, Android or Flutter app, or when a requested change is too large or too uncertain to start coding.
argument-hint: "<what to design>"
---

# Design before building

Produce a decision document, not a description of an answer already chosen. A reader should be able to disagree with it precisely.

## 1. Frame

- The problem in the user's terms, the constraint that makes it hard, and what is out of scope.
- The forces that are specific to mobile and usually decide the design. Go through [references/mobile-forces.md](references/mobile-forces.md) and keep only the ones that apply.
- The existing architecture, from the code map and the code. Fit the design to it unless changing it is the point, and say which.

## 2. Options

At least two real options, each with: how it works in a paragraph, what it costs to build and to run, what it makes easy later and what it makes hard, how it fails, and how it is rolled back after release. Include "do less": the smallest thing that solves the problem.

## 3. Decide

Recommend one and say what evidence would change the recommendation. Call out the decisions that are hard to reverse once shipped: stored data formats, API contract shapes, identifiers, deep-link URLs, the minimum OS version, a third-party SDK that becomes load-bearing.

## 4. Make it buildable

- **Boundaries.** Modules and layers, the direction of dependencies, the public interface of each new piece.
- **Data.** Models, storage, schema version and migration path. The server contract, its versioning, and how app versions already installed keep working.
- **State and concurrency.** Who owns each piece of state and where it survives (memory, saved state, disk). Which thread, actor, dispatcher or isolate does what. How work is cancelled.
- **Failure.** Offline, timeouts, partial failure, retries with idempotency, conflict resolution.
- **Rollout.** Feature flag, staged rollout, kill switch, the metrics that say it works, rollback without a store release where possible.
- **Tests.** What is unit-tested, what needs integration or UI tests, what must be checked on real devices.
- **Build order.** Slices that each ship behind the flag, enablers first.

## 5. Write it down

Use [references/design-doc-template.md](references/design-doc-template.md). Write to `docs/agent/designs/<name>.md`, or to the project's ADR directory if it has one. Two pages beat ten. End with the open questions for the team, and do not start implementing until the ones that change the design are answered.
