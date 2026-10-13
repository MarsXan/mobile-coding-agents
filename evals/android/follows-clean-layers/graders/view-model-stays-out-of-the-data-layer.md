---
type: regex
target: { source: file, path: app/src/main/java/com/example/orders/ui/OrdersViewModel.kt }
pattern: 'OrdersApi|OrdersRepository'
match: not_contains
weight: 2
---
