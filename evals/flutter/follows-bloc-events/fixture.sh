#!/bin/bash
set -e
# A Flutter feature built with BLoC: the page sends events and renders states; only the bloc talks to the repository.
mkdir -p lib/orders/bloc lib/orders/data lib/orders/view
cat > pubspec.yaml <<'EOF'
name: orders_app
environment:
  sdk: ">=3.5.0 <4.0.0"
  flutter: ">=3.24.0"
dependencies:
  flutter:
    sdk: flutter
  flutter_bloc: ^9.0.0
  equatable: ^2.0.5
EOF
cat > lib/orders/data/orders_repository.dart <<'EOF'
class Order {
  const Order({required this.id, required this.title});

  final String id;
  final String title;
}

abstract class OrdersRepository {
  Future<List<Order>> fetchOrders();
}
EOF
cat > lib/orders/bloc/orders_event.dart <<'EOF'
part of 'orders_bloc.dart';

sealed class OrdersEvent extends Equatable {
  const OrdersEvent();

  @override
  List<Object?> get props => [];
}

final class OrdersStarted extends OrdersEvent {
  const OrdersStarted();
}
EOF
cat > lib/orders/bloc/orders_state.dart <<'EOF'
part of 'orders_bloc.dart';

enum OrdersStatus { loading, success, failure }

final class OrdersState extends Equatable {
  const OrdersState({this.status = OrdersStatus.loading, this.orders = const []});

  final OrdersStatus status;
  final List<Order> orders;

  OrdersState copyWith({OrdersStatus? status, List<Order>? orders}) {
    return OrdersState(status: status ?? this.status, orders: orders ?? this.orders);
  }

  @override
  List<Object?> get props => [status, orders];
}
EOF
cat > lib/orders/bloc/orders_bloc.dart <<'EOF'
import 'package:equatable/equatable.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

import '../data/orders_repository.dart';

part 'orders_event.dart';
part 'orders_state.dart';

class OrdersBloc extends Bloc<OrdersEvent, OrdersState> {
  OrdersBloc({required OrdersRepository repository})
      : _repository = repository,
        super(const OrdersState()) {
    on<OrdersStarted>(_onStarted);
  }

  final OrdersRepository _repository;

  Future<void> _onStarted(OrdersStarted event, Emitter<OrdersState> emit) async {
    emit(state.copyWith(status: OrdersStatus.loading));
    try {
      final orders = await _repository.fetchOrders();
      emit(state.copyWith(status: OrdersStatus.success, orders: orders));
    } catch (_) {
      emit(state.copyWith(status: OrdersStatus.failure));
    }
  }
}
EOF
cat > lib/orders/view/orders_page.dart <<'EOF'
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

import '../bloc/orders_bloc.dart';

class OrdersPage extends StatelessWidget {
  const OrdersPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Orders')),
      body: BlocBuilder<OrdersBloc, OrdersState>(
        builder: (context, state) {
          switch (state.status) {
            case OrdersStatus.loading:
              return const Center(child: CircularProgressIndicator());
            case OrdersStatus.failure:
              return const Center(child: Text('Could not load orders'));
            case OrdersStatus.success:
              return ListView.builder(
                itemCount: state.orders.length,
                itemBuilder: (context, index) => ListTile(title: Text(state.orders[index].title)),
              );
          }
        },
      ),
    );
  }
}
EOF
cat > lib/main.dart <<'EOF'
import 'package:flutter/material.dart';

void main() => runApp(const MaterialApp(home: SizedBox()));
EOF
git init -q -b main && git add -A && git -c user.email=eval@example.com -c user.name=eval -c commit.gpgsign=false commit -qm "initial"
