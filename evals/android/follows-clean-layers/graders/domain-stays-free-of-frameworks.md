---
type: regex
target: { source: file, path: app/src/main/java/com/example/orders/domain/OrdersRepository.kt }
pattern: 'retrofit|import android'
match: not_contains
---
