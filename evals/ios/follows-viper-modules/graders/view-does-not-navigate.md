---
type: regex
target: { source: file, path: App/Modules/Orders/OrdersViewController.swift }
pattern: 'pushViewController|present\(|OrderDetail\w*\('
match: not_contains
weight: 2
---
