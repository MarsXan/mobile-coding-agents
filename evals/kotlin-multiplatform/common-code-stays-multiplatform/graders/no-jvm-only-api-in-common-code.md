---
type: regex
target: { source: file, path: shared/src/commonMain/kotlin/com/example/shared/Money.kt }
pattern: 'String\.format|\.format\(|import java|java\.'
match: not_contains
weight: 3
---
