---
name: recon
description: Maps an unfamiliar or legacy mobile codebase before it is changed. Covers modules, entry points, navigation, data flow, persistence, tests and risk hotspots, and writes a cited code map. Use when starting work in a repository or area not yet read in this session, when asked how an app is structured, or before planning a refactor or migration.
argument-hint: "[area or module to map; empty for the whole repository]"
allowed-tools: Bash(mobile recon *) Bash(mobile detect *)
---

# Recon: understand before changing

Goal: a code map a newcomer could act on, at the lowest reading cost. Facts come from tools first, reading second, inference last. Every claim in the map cites a file.

## 1. Count before reading

Run `mobile recon` (and `mobile detect` if the session did not start with project facts). It reports sizes, pattern counts, the largest files and the files that are both large and frequently changed. Do not search for what it already counted.

## 2. Read only the load-bearing files

In this order, stopping when the question is answered:

1. **Build definition.** Xcode project and schemes, `Package.swift`; `settings.gradle*` and module `build.gradle*`; `pubspec.yaml`. Targets, modules, dependencies, configurations and flavors.
2. **Entry points.** `@main`, `AppDelegate`, `SceneDelegate`; the `Application` class, launcher activity and `AndroidManifest.xml`; `main.dart`.
3. **Composition root.** Where dependencies are created and wired: DI container, service locator, provider tree.
4. **Navigation.** Coordinator, router or navigation graph: how a screen is reached.
5. **One vertical slice** end to end for the area in question: UI, state holder, domain logic, network, persistence.
6. **Persistence definitions** and their migration history.
7. **The tests for that slice.** What is covered and how: unit, snapshot, UI.

In a large repository, delegate the reading to the `mobile-core:cartographer` agent, one per independent area, and keep only the maps it returns.

## 3. Write the map

Write or update the code map (`docs/agent/CODEMAP.md` unless `.mobile-coding-agents.json` sets `codemap`). Keep it under 150 lines: it is read at the start of future work.

- **Shape.** Platforms, modules or targets, and what each owns. One line each.
- **How it runs.** Entry point, composition root, navigation, each with `file:line`.
- **Data.** Network layer, stores, where models are mapped, current schema versions.
- **Conventions in use.** Architecture pattern per area and its exceptions, state management, concurrency style, dependency injection. One representative file per convention. `mobile recon` counts the markers (view models, coordinators, presenters, reducers, use cases, repositories, dependency-injection imports): name the pattern from those counts and a file you read, not from folder names.
- **Tests.** Which kinds exist, how to run them, what is not covered.
- **Risk register.** Hotspots from `mobile recon`, untested critical paths, legacy islands and whether they are intentional, anything surprising.
- **Open questions** for the team.

Mark each statement *verified* (you read it, with the file) or *inferred*. Never present an inference as a fact.

## Rules

- Change no code during recon.
- Old is not wrong. Record what the code does and what depends on it.
- If a recent map exists, read it, verify the part you are about to touch, and update only what changed.
