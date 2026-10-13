#!/bin/bash
set -e
# A UIKit app built from VIPER modules: view, presenter, interactor, router, wired by a builder,
# each behind a protocol. Only a router navigates.
M=App/Modules/Orders
mkdir -p $M App/Entities App.xcodeproj
cat > App.xcodeproj/project.pbxproj <<'EOF'
// !$*UTF8*$!
{ objectVersion = 77; objects = { A1 = { isa = PBXFileSystemSynchronizedRootGroup; path = App; }; B1 = { buildSettings = { IPHONEOS_DEPLOYMENT_TARGET = 16.0; SWIFT_VERSION = 5.0; }; }; }; }
EOF
cat > App/Entities/Order.swift <<'EOF'
import Foundation

struct Order {
    let id: String
    let title: String
    let status: String
}

protocol OrdersService {
    func loadOrders() async throws -> [Order]
}
EOF
cat > $M/OrdersContract.swift <<'EOF'
import UIKit

// The contracts of the Orders module. Each layer talks to the next only through these.

protocol OrdersViewProtocol: AnyObject {
    func show(titles: [String])
}

protocol OrdersPresenterProtocol: AnyObject {
    func viewDidLoad()
    func didSelectOrder(at index: Int)
}

protocol OrdersInteractorProtocol: AnyObject {
    func loadOrders() async throws -> [Order]
}

protocol OrdersRouterProtocol: AnyObject {
}
EOF
cat > $M/OrdersViewController.swift <<'EOF'
import UIKit

final class OrdersViewController: UITableViewController, OrdersViewProtocol {
    var presenter: OrdersPresenterProtocol!
    private var titles: [String] = []

    override func viewDidLoad() {
        super.viewDidLoad()
        title = "Orders"
        tableView.register(UITableViewCell.self, forCellReuseIdentifier: "cell")
        presenter.viewDidLoad()
    }

    func show(titles: [String]) {
        self.titles = titles
        tableView.reloadData()
    }

    override func tableView(_ tableView: UITableView, numberOfRowsInSection section: Int) -> Int {
        titles.count
    }

    override func tableView(_ tableView: UITableView, cellForRowAt indexPath: IndexPath) -> UITableViewCell {
        let cell = tableView.dequeueReusableCell(withIdentifier: "cell", for: indexPath)
        cell.textLabel?.text = titles[indexPath.row]
        return cell
    }

    override func tableView(_ tableView: UITableView, didSelectRowAt indexPath: IndexPath) {
        presenter.didSelectOrder(at: indexPath.row)
    }
}
EOF
cat > $M/OrdersPresenter.swift <<'EOF'
import Foundation

final class OrdersPresenter: OrdersPresenterProtocol {
    weak var view: OrdersViewProtocol?
    private let interactor: OrdersInteractorProtocol
    private let router: OrdersRouterProtocol
    private var orders: [Order] = []

    init(interactor: OrdersInteractorProtocol, router: OrdersRouterProtocol) {
        self.interactor = interactor
        self.router = router
    }

    func viewDidLoad() {
        Task { @MainActor in
            orders = (try? await interactor.loadOrders()) ?? []
            view?.show(titles: orders.map(\.title))
        }
    }

    func didSelectOrder(at index: Int) {
    }
}
EOF
cat > $M/OrdersInteractor.swift <<'EOF'
import Foundation

final class OrdersInteractor: OrdersInteractorProtocol {
    private let service: OrdersService

    init(service: OrdersService) {
        self.service = service
    }

    func loadOrders() async throws -> [Order] {
        try await service.loadOrders()
    }
}
EOF
cat > $M/OrdersRouter.swift <<'EOF'
import UIKit

final class OrdersRouter: OrdersRouterProtocol {
    weak var viewController: UIViewController?
}
EOF
cat > $M/OrdersBuilder.swift <<'EOF'
import UIKit

enum OrdersBuilder {
    static func build(service: OrdersService) -> UIViewController {
        let router = OrdersRouter()
        let presenter = OrdersPresenter(interactor: OrdersInteractor(service: service), router: router)
        let view = OrdersViewController(style: .plain)
        view.presenter = presenter
        presenter.view = view
        router.viewController = view
        return view
    }
}
EOF
git init -q -b main && git add -A && git -c user.email=eval@example.com -c user.name=eval -c commit.gpgsign=false commit -qm "initial"
