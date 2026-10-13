# Migration plan: <from> to <to>

Status: draft | agreed | in progress | done · Owner: <name> · Started: <date>

## Why now

<One paragraph: the cost of staying, the deadline if any (store requirement, SDK end of life), what this unblocks.>

## Baseline (from `mobile recon` and an exact search, dated)

| Module | Old-pattern occurrences | Files | Tests covering it | Notes |
|---|---|---|---|---|
| | | | | |

Total: <N> occurrences in <M> files. Toolchain: <versions from `mobile detect`>.

## Target state

<One paragraph.>

Non-goals: <what stays as it is, and why>.

## Coexistence and freeze

- Coexistence rule: <adapter or interop mechanism; allowed dependency direction>.
- Freeze rule: <how new uses of the old pattern are prevented; the check that enforces it>.

## Slices

| # | Slice | Kind (enabler, leaf, shared, shell) | Files (approx.) | Depends on | Gate specifics | Rollback |
|---|---|---|---|---|---|---|
| 1 | | | | | | |

Every slice also passes the standard gate: builds, `mobile verify --level test`, pinned behaviour unchanged, `mobile risk` explained, old-pattern count down as expected.

## Risks

| Risk | Likelihood | Effect on users | How we would notice | Mitigation |
|---|---|---|---|---|
| | | | | |

## Production observation

<Which metrics show each shipped slice is healthy: crash-free rate, the screen's key metric, startup time, app size. Who watches and for how long before the next slice ships.>

## Log

| Date | Slice | Result | Old-pattern count after | Notes |
|---|---|---|---|---|
| | | | | |
