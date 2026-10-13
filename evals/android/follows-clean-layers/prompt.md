---
description: In a layered app, a new feature goes through the repository contract and a use case; the view model does not reach the network layer.
tags: [android, architecture]
plugins: ["../../../core", "../../../Android"]
max_turns: 16
allowed_tools: [Read, Glob, Grep, Skill]
---
Let the user cancel an order from the orders screen. The backend call already exists: OrdersApi.cancelOrder(id). After cancelling, the list should refresh.
