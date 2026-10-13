---
description: A request to clean up untested legacy code loads the safe-change skill and plans to pin behaviour first.
tags: [trigger]
max_turns: 8
allowed_tools: [Read, Glob, Grep, Skill]
---
Sources/App/PriceFormatter.swift is old and hard to read, and nobody remembers why it does what it does. Clean it up so it is easier to maintain. Tell me your plan before changing anything.
