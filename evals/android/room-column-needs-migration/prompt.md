---
description: Adding a column to a Room entity also bumps the database version and adds a migration.
tags: [android, behaviour]
plugins: ["../../../core", "../../../Android"]
max_turns: 16
allowed_tools: [Read, Glob, Grep, Skill]
---
Add an optional `nickname` field to the User entity so we can show it on the profile screen.
