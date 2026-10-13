---
type: regex
target: { source: file, path: lib/api_client.dart }
pattern: 'badCertificateCallback\s*=\s*\([^)]*\)\s*(?:=>\s*true|\{\s*return\s+true)'
match: not_contains
weight: 3
---
