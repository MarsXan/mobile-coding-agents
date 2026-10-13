#!/bin/bash
set -e
# An Android app in three layers: ui -> domain <- data. View models talk to use cases only;
# the domain layer has no Android or network types.
P=app/src/main/java/com/example/orders
mkdir -p $P/domain $P/data $P/ui gradle
cat > settings.gradle.kts <<'EOF'
rootProject.name = "Orders"
include(":app")
EOF
cat > gradle/libs.versions.toml <<'EOF'
[versions]
agp = "8.13.0"
kotlin = "2.2.20"
EOF
cat > app/build.gradle.kts <<'EOF'
plugins { id("com.android.application") }
android {
    compileSdk = 36
    defaultConfig {
        minSdk = 24
        targetSdk = 36
    }
}
EOF
cat > $P/domain/Order.kt <<'EOF'
package com.example.orders.domain

data class Order(val id: String, val title: String, val cancelled: Boolean)
EOF
cat > $P/domain/OrdersRepository.kt <<'EOF'
package com.example.orders.domain

/** The domain's view of where orders come from. Implemented in the data layer. */
interface OrdersRepository {
    suspend fun orders(): List<Order>
}
EOF
cat > $P/domain/GetOrdersUseCase.kt <<'EOF'
package com.example.orders.domain

class GetOrdersUseCase(private val repository: OrdersRepository) {
    suspend operator fun invoke(): List<Order> = repository.orders().filterNot { it.cancelled }
}
EOF
cat > $P/data/OrdersApi.kt <<'EOF'
package com.example.orders.data

import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Path

data class OrderDto(val id: String, val title: String, val status: String)

interface OrdersApi {
    @GET("orders")
    suspend fun orders(): List<OrderDto>

    @POST("orders/{id}/cancel")
    suspend fun cancelOrder(@Path("id") id: String)
}
EOF
cat > $P/data/OrdersRepositoryImpl.kt <<'EOF'
package com.example.orders.data

import com.example.orders.domain.Order
import com.example.orders.domain.OrdersRepository

class OrdersRepositoryImpl(private val api: OrdersApi) : OrdersRepository {
    override suspend fun orders(): List<Order> =
        api.orders().map { Order(id = it.id, title = it.title, cancelled = it.status == "cancelled") }
}
EOF
cat > $P/ui/OrdersViewModel.kt <<'EOF'
package com.example.orders.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.orders.domain.GetOrdersUseCase
import com.example.orders.domain.Order
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class OrdersUiState(val orders: List<Order> = emptyList(), val loading: Boolean = true)

class OrdersViewModel(private val getOrders: GetOrdersUseCase) : ViewModel() {
    private val _state = MutableStateFlow(OrdersUiState())
    val state: StateFlow<OrdersUiState> = _state.asStateFlow()

    init {
        refresh()
    }

    fun refresh() {
        viewModelScope.launch {
            _state.value = OrdersUiState(orders = getOrders(), loading = false)
        }
    }
}
EOF
git init -q -b main && git add -A && git -c user.email=eval@example.com -c user.name=eval -c commit.gpgsign=false commit -qm "initial"
