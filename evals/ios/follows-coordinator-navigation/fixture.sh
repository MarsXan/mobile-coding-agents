#!/bin/bash
set -e
# A UIKit app that navigates through a coordinator: view controllers never create or push each other.
mkdir -p App/Coordinator App/Login App/Orders App.xcodeproj
cat > App.xcodeproj/project.pbxproj <<'EOF'
// !$*UTF8*$!
{ objectVersion = 77; objects = { A1 = { isa = PBXFileSystemSynchronizedRootGroup; path = App; }; B1 = { buildSettings = { IPHONEOS_DEPLOYMENT_TARGET = 16.0; SWIFT_VERSION = 5.0; }; }; }; }
EOF
cat > App/Coordinator/AppCoordinator.swift <<'EOF'
import UIKit

/// Owns navigation for the whole app. Screens report what happened; this class decides where to go.
final class AppCoordinator {
    private let navigation: UINavigationController
    private let orders: OrdersService

    init(navigation: UINavigationController, orders: OrdersService) {
        self.navigation = navigation
        self.orders = orders
    }

    func start() {
        let viewModel = LoginViewModel()
        viewModel.onLoggedIn = { [weak self] in self?.showOrders() }
        navigation.setViewControllers([LoginViewController(viewModel: viewModel)], animated: false)
    }

    private func showOrders() {
        let viewModel = OrdersViewModel(service: orders)
        navigation.setViewControllers([OrdersViewController(viewModel: viewModel)], animated: true)
    }
}
EOF
cat > App/Login/LoginViewModel.swift <<'EOF'
import Foundation

final class LoginViewModel {
    var onLoggedIn: (() -> Void)?

    func logIn(email: String, password: String) {
        guard !email.isEmpty, !password.isEmpty else { return }
        onLoggedIn?()
    }
}
EOF
cat > App/Login/LoginViewController.swift <<'EOF'
import UIKit

final class LoginViewController: UIViewController {
    private let viewModel: LoginViewModel

    init(viewModel: LoginViewModel) {
        self.viewModel = viewModel
        super.init(nibName: nil, bundle: nil)
    }

    required init?(coder: NSCoder) { fatalError("init(coder:) is not used") }

    @objc private func submit() {
        viewModel.logIn(email: "user@example.com", password: "secret")
    }
}
EOF
cat > App/Orders/OrdersService.swift <<'EOF'
import Foundation

struct Order {
    let id: String
    let title: String
}

protocol OrdersService {
    func loadOrders() async throws -> [Order]
}
EOF
cat > App/Orders/OrdersViewModel.swift <<'EOF'
import Foundation

final class OrdersViewModel {
    private let service: OrdersService
    private(set) var orders: [Order] = []
    var onChange: (() -> Void)?

    init(service: OrdersService) {
        self.service = service
    }

    func load() {
        Task { @MainActor in
            orders = (try? await service.loadOrders()) ?? []
            onChange?()
        }
    }
}
EOF
cat > App/Orders/OrdersViewController.swift <<'EOF'
import UIKit

final class OrdersViewController: UITableViewController {
    private let viewModel: OrdersViewModel

    init(viewModel: OrdersViewModel) {
        self.viewModel = viewModel
        super.init(style: .plain)
    }

    required init?(coder: NSCoder) { fatalError("init(coder:) is not used") }

    override func viewDidLoad() {
        super.viewDidLoad()
        tableView.register(UITableViewCell.self, forCellReuseIdentifier: "cell")
        viewModel.onChange = { [weak self] in self?.tableView.reloadData() }
        viewModel.load()
    }

    override func tableView(_ tableView: UITableView, numberOfRowsInSection section: Int) -> Int {
        viewModel.orders.count
    }

    override func tableView(_ tableView: UITableView, cellForRowAt indexPath: IndexPath) -> UITableViewCell {
        let cell = tableView.dequeueReusableCell(withIdentifier: "cell", for: indexPath)
        cell.textLabel?.text = viewModel.orders[indexPath.row].title
        return cell
    }
}
EOF
cat > App/Orders/OrderDetailViewController.swift <<'EOF'
import UIKit

final class OrderDetailViewController: UIViewController {
    private let order: Order

    init(order: Order) {
        self.order = order
        super.init(nibName: nil, bundle: nil)
    }

    required init?(coder: NSCoder) { fatalError("init(coder:) is not used") }

    override func viewDidLoad() {
        super.viewDidLoad()
        title = order.title
    }
}
EOF
git init -q -b main && git add -A && git -c user.email=eval@example.com -c user.name=eval -c commit.gpgsign=false commit -qm "initial"
