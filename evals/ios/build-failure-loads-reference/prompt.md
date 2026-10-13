---
description: A build failure loads the iOS skill and its build reference.
tags: [ios, trigger]
plugins: ["../../../core", "../../../iOS"]
max_turns: 8
allowed_tools: [Read, Glob, Grep, Skill]
---
After pulling main, the app no longer builds: "No such module 'Alamofire'" in NetworkClient.swift. We use CocoaPods. What is wrong and what should I do?
