# <Title>

Status: draft | in review | accepted | superseded by <link> · Author: <name> · Date: <date>

## Problem

<What the user or the team cannot do today, and the constraint that makes it hard. Out of scope: ...>

## Forces

<The three to six mobile-specific forces that decide this design, each as one line with its consequence.>

## Options

### A. <name>
How it works: <one paragraph>
Costs: <to build, to run>
Makes easy / makes hard: <...>
Failure and rollback: <...>

### B. <name>
<same shape>

### C. Do less
<the smallest thing that solves the problem>

## Decision

<The recommendation and the main reason. What evidence would change it.>

Hard to reverse once shipped: <stored formats, contract shapes, identifiers, deep links, minimum OS, SDK lock-in>.

## Design

- Boundaries: <modules, dependency direction, public interfaces>
- Data: <models, storage, schema version, migration; server contract and versioning>
- State and concurrency: <owner of state, where it survives, threading, cancellation>
- Failure behaviour: <offline, timeout, partial failure, retry, conflict>
- Security and privacy: <what lives on the server, token storage, input validation, declarations>
- Accessibility and localisation: <...>

## Rollout

<Flag, stages, kill switch, health metrics and thresholds, rollback.>

## Test strategy

<Unit, integration, UI, device matrix, migration tests.>

## Build order

| # | Slice | Ships behind flag | Depends on |
|---|---|---|---|
| 1 | | | |

## Open questions

- <question> (who can answer it)
