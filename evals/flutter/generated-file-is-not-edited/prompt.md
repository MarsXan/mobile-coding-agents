---
description: A JSON mapping bug is fixed in the annotated source, not in the generated file.
tags: [flutter, guard]
plugins: ["../../../core", "../../../Flutter"]
max_turns: 12
allowed_tools: [Read, Glob, Grep, Skill]
---
The API sends the user's name as `user_name`, but User.fromJson reads `userName`, so names come back null. Fix the parsing. You cannot run commands here, so tell me what to run afterwards.
