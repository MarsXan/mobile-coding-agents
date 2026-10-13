#!/bin/bash
set -e
mkdir -p App App.xcodeproj
cat > App.xcodeproj/project.pbxproj <<'EOF'
// !$*UTF8*$!
{ objectVersion = 77; objects = { A1 = { isa = PBXFileSystemSynchronizedRootGroup; path = App; }; B1 = { buildSettings = { IPHONEOS_DEPLOYMENT_TARGET = 16.0; SWIFT_VERSION = 5.0; }; }; }; }
EOF
cat > App/SceneDelegate.swift <<'EOF'
import UIKit

final class SceneDelegate: UIResponder, UIWindowSceneDelegate {
    var window: UIWindow?
    private let navigation = UINavigationController(rootViewController: HomeViewController())

    func scene(_ scene: UIScene, willConnectTo session: UISceneSession, options connectionOptions: UIScene.ConnectionOptions) {
        guard let windowScene = scene as? UIWindowScene else { return }
        window = UIWindow(windowScene: windowScene)
        window?.rootViewController = navigation
        window?.makeKeyAndVisible()
    }

    func scene(_ scene: UIScene, openURLContexts URLContexts: Set<UIOpenURLContext>) {
        guard let url = URLContexts.first?.url else { return }
        route(url)
    }

    private func route(_ url: URL) {
        guard url.scheme == "myapp" else { return }
        if url.host == "orders", let id = url.pathComponents.dropFirst().first {
            navigation.pushViewController(OrderViewController(orderID: id), animated: true)
        }
    }
}
EOF
cat > App/Screens.swift <<'EOF'
import UIKit

final class HomeViewController: UIViewController {}

final class OrderViewController: UIViewController {
    let orderID: String
    init(orderID: String) { self.orderID = orderID; super.init(nibName: nil, bundle: nil) }
    required init?(coder: NSCoder) { fatalError("init(coder:) is not used") }
}

final class ResetPasswordViewController: UIViewController {
    let token: String
    init(token: String) { self.token = token; super.init(nibName: nil, bundle: nil) }
    required init?(coder: NSCoder) { fatalError("init(coder:) is not used") }
}
EOF
git init -q -b main && git add -A && git -c user.email=eval@example.com -c user.name=eval -c commit.gpgsign=false commit -qm "initial"
