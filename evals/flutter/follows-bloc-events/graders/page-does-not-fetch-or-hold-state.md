---
type: regex
target: { source: file, path: lib/orders/view/orders_page.dart }
pattern: 'OrdersRepository|fetchOrders|setState'
match: not_contains
weight: 2
---
