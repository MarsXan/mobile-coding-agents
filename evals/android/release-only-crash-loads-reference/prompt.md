---
description: A release-only crash loads the Android skill and its build reference, and the answer does not disable shrinking.
tags: [android, trigger]
plugins: ["../../../core", "../../../Android"]
max_turns: 8
allowed_tools: [Read, Glob, Grep, Skill]
---
Our release build crashes on launch with java.lang.ClassNotFoundException: com.example.api.OrderDto, but the debug build is fine. What is going on and how do I fix it?
