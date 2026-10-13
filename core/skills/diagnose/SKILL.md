---
name: diagnose
description: Finds the cause of a runtime problem in a mobile app before any code is changed. Covers crashes, wrong behaviour, hangs and ANRs, jank, slow launch, memory growth, battery drain, network failures, flaky tests and app-size growth. Establishes a reproduction or a measurement first, then a narrow fix with proof. Use when given a crash log or stack trace, a bug report, a failing or flaky test, or a complaint that an iOS, Android or Flutter app is slow, heavy or unstable.
---

# Diagnose before fixing

A fix without a reproduced cause is a guess that ships. The order is fixed: evidence, cause, fix, proof.

## 1. Capture the evidence exactly

- The full error: complete stack trace, exception type and message, device, OS version, app version and build, how often, since when. Ask for what is missing instead of assuming it.
- Symbolicate before reading a crash. An unsymbolicated or obfuscated trace points at nothing. See [references/crash.md](references/crash.md) for dSYM, R8 mapping and Flutter symbol files, and for what the common termination codes mean.
- "Since when" is the strongest clue. The commits between the last good and the first bad build bound the search; `git bisect` finds the commit when the problem reproduces.

## 2. Reproduce or measure

- **Bug or crash.** The smallest deterministic reproduction, ideally a failing automated test. If it only happens on some devices, OS versions, locales or app states, name the condition.
- **Speed, memory, battery, size.** A number from a tool, on a release-like build, on a real device. Debug builds and simulators mislead. See [references/performance.md](references/performance.md) for which number and which tool.
- **Flaky test.** Run it repeatedly alone and in suite order to learn whether it depends on order, time or concurrency before touching it.
- **Cannot reproduce?** Say so. Add targeted logging, a signpost or a crash breadcrumb to catch it next time. Do not ship a guess and call it a fix.

## 3. Find the cause

- One hypothesis at a time, each with a prediction that can fail. Test it with the cheapest experiment (a log line, a breakpoint, a unit test, a trace) before reading more code.
- Read the code along the stack trace once, top down. After that, let evidence choose where to look. Do not rewrite code while exploring.
- Separate the trigger (what the user did), the fault (the wrong line) and the root cause (why the fault was possible: an unhandled state, a lifecycle assumption, a race, a platform limit). Fix the fault. Report the root cause.
- The usual suspects on mobile: lifecycle and state restoration, work on the main thread, races and re-entrancy, retain cycles and leaks, OS-version differences, permission and background-execution limits, low memory, locale and time zone, poor networks, stale caches, old data that was never migrated. The platform skill's `concurrency.md`, `persistence.md` and `performance.md` say what each looks like in that platform's terms.

## 4. Fix narrowly and prove it

- The failing test or the measurement from step 2 is the acceptance check: it fails before the fix and passes after. Keep it as a regression test.
- Fix the cause at its source. Not a catch-and-ignore, not a retry, not a delay, not a nil or null check that hides a broken invariant, not a hop to the main thread that masks a race.
- For performance, measure the same scenario the same way again and report before and after. If the number did not move, the change comes out, however plausible it looked.
- Search for the same mistake elsewhere and list the other occurrences. Fix them only if asked.
- Run `mobile verify --level test`. Report: symptom, cause with `file:line`, fix, proof, remaining risk, and what would have caught it earlier.

## Never

- Call a crash fixed because the code looks right now.
- Optimise without a baseline, or report a gain measured on a debug build.
- Quiet a flaky test with a retry, a sleep or a skip.
