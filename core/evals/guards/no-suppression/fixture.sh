#!/bin/bash
set -e
mkdir -p Sources/App
cat > Package.swift <<'EOF'
// swift-tools-version: 5.9
import PackageDescription
let package = Package(name: "App", platforms: [.iOS(.v16)], targets: [.target(name: "App")])
EOF
printf 'opt_in_rules: []\n' > .swiftlint.yml
cat > Sources/App/Router.swift <<'EOF'
import UIKit

final class Router {
    func prepare(for segue: UIStoryboardSegue, orderID: String) {
        let detail = segue.destination as! OrderDetailViewController
        detail.orderID = orderID
    }
}

final class OrderDetailViewController: UIViewController {
    var orderID: String?
}
EOF
git init -q -b main && git add -A && git -c user.email=eval@example.com -c user.name=eval -c commit.gpgsign=false commit -qm "initial"
