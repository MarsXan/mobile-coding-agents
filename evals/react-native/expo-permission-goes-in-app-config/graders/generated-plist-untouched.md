---
type: regex
target: { source: file, path: ios/Scanner/Info.plist }
pattern: 'NSCameraUsageDescription'
match: not_contains
weight: 2
---
