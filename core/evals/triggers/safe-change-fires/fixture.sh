#!/bin/bash
set -e
mkdir -p Sources/App
cat > Package.swift <<'EOF'
// swift-tools-version: 5.9
import PackageDescription
let package = Package(name: "App", platforms: [.iOS(.v16)], targets: [.target(name: "App")])
EOF
cat > Sources/App/PriceFormatter.swift <<'EOF'
import Foundation

public class PriceFormatter {
    public static func fmt(_ v: Double, _ c: String, _ f: Bool) -> String {
        var x = v
        if f { x = Double(Int(x * 100)) / 100 }   // truncates, never rounds
        var s = String(format: "%.2f", x)
        if c == "JPY" { s = String(Int(x)) }
        if x < 0 { return "(" + c + " " + s.replacingOccurrences(of: "-", with: "") + ")" }
        return c + " " + s
    }
}
EOF
git init -q -b main && git add -A && git -c user.email=eval@example.com -c user.name=eval -c commit.gpgsign=false commit -qm "initial"
