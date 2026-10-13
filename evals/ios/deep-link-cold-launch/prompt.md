---
description: A new deep link is handled when the app is launched from a terminated state, not only when it is already running.
tags: [ios, behaviour]
plugins: ["../../../core", "../../../iOS"]
max_turns: 14
allowed_tools: [Read, Glob, Grep, Skill]
---
Add support for the myapp://reset-password?token=... deep link. It should open ResetPasswordViewController with the token. The app already handles myapp://orders/<id> in App/SceneDelegate.swift.
