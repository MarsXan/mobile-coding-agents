import io
import os
import unittest

import fixtures
from mobilekit import config as config_module
from mobilekit import detect, recon, verify


class DetectTests(unittest.TestCase):
    def test_ios_project_facts(self):
        project = fixtures.ios_project(git=False)
        self.addCleanup(project.cleanup)
        facts = detect.detect(project.root)
        self.assertEqual(facts["platforms"], ["ios"])
        ios = facts["ios"]
        self.assertEqual(ios["deploymentTargets"], ["15.0", "16.0"])
        self.assertEqual(ios["swiftVersions"], ["5.0"])
        self.assertEqual(ios["strictConcurrency"], ["minimal"])
        self.assertEqual(ios["schemes"], ["App"])
        self.assertEqual(ios["objcFiles"], 1)
        self.assertFalse(ios["synchronizedFolders"])
        self.assertIn(".swiftlint.yml", ios["lint"])
        profile = "\n".join(detect.profile_lines(facts))
        self.assertIn("minimum iOS 15.0", profile)
        self.assertIn("explicit file references", profile)

    def test_json_project_file_is_read_like_the_old_one(self):
        project = fixtures.Project(git=False)
        self.addCleanup(project.cleanup)
        project.write("App.xcodeproj/project.xcproj", '{"buildSettings": {"IPHONEOS_DEPLOYMENT_TARGET" : "18.0", "SWIFT_VERSION" : "6.0", "SWIFT_DEFAULT_ACTOR_ISOLATION" : "MainActor"}}')
        project.write("App/App.swift", "struct App {}\n")
        ios = detect.detect(project.root)["ios"]
        self.assertEqual(ios["deploymentTargets"], ["18.0"])
        self.assertEqual(ios["swiftVersions"], ["6.0"])
        self.assertEqual(ios["defaultActorIsolation"], ["MainActor"])
        self.assertIn("JSON project file", "\n".join(detect.profile_lines({"ios": ios})))

    def test_xcconfig_and_podfile_variable_supply_settings(self):
        project = fixtures.Project(git=False)
        self.addCleanup(project.cleanup)
        project.write("App.xcodeproj/project.pbxproj", "// !$*UTF8*$!\n{ objectVersion = 77; PBXFileSystemSynchronizedRootGroup }\n")
        project.write("Config/Common.xcconfig", "IPHONEOS_DEPLOYMENT_TARGET = 17.4\nSWIFT_VERSION = 5.0\nSWIFT_STRICT_CONCURRENCY[sdk=*] = complete\nSWIFT_UPCOMING_FEATURE_EXISTENTIAL_ANY = YES\n")
        project.write("Podfile", "min_ios_version = '16.0'\nplatform :ios, min_ios_version\n")
        ios = detect.detect(project.root)["ios"]
        self.assertEqual(ios["deploymentTargets"], ["16.0", "17.4"])
        self.assertEqual(ios["strictConcurrency"], ["complete"])
        self.assertEqual(ios["upcomingFeatures"], ["EXISTENTIAL_ANY"])
        self.assertTrue(ios["synchronizedFolders"])
        self.assertEqual(ios["packageManagers"], ["CocoaPods"])

    def test_swift_package_facts(self):
        project = fixtures.Project(git=False)
        self.addCleanup(project.cleanup)
        project.write("Package.swift", "// swift-tools-version: 6.0\nimport PackageDescription\nlet package = Package(name: \"Kit\", platforms: [.iOS(.v16), .macOS(.v13)], targets: [.target(name: \"Kit\")])\n")
        project.write("Sources/Kit/Kit.swift", "public struct Kit {}\n")
        facts = detect.detect(project.root)
        self.assertEqual(facts["platforms"], ["ios"])
        self.assertEqual(facts["ios"]["deploymentTargets"], ["16.0"])
        self.assertEqual(facts["ios"]["swiftToolsVersions"], ["6.0"])
        self.assertEqual(facts["ios"]["packageManagers"], ["SwiftPM"])

    def test_android_project_facts(self):
        project = fixtures.android_project(git=False)
        self.addCleanup(project.cleanup)
        facts = detect.detect(project.root)
        self.assertEqual(facts["platforms"], ["android"])
        android = facts["android"]
        self.assertEqual(android["agp"], "8.7.3")
        self.assertEqual(android["kotlin"], "2.0.21")
        self.assertEqual(android["gradle"], "8.11.1")
        self.assertEqual(android["minSdk"], [24])
        self.assertEqual(android["compileSdk"], [35])
        self.assertEqual(android["modules"], 2)
        for flag in ("compose", "kapt", "room"):
            self.assertIn(flag, android["flags"])
        self.assertIn("minSdk 24", "\n".join(detect.profile_lines(facts)))

    def test_flutter_project_owns_its_embedded_native_folders(self):
        project = fixtures.flutter_project(git=False)
        self.addCleanup(project.cleanup)
        facts = detect.detect(project.root)
        self.assertEqual(facts["platforms"], ["flutter"])
        flutter = facts["flutter"]
        self.assertEqual(flutter["dartSdk"], ">=3.4.0 <4.0.0")
        self.assertEqual(flutter["pinnedFlutter"], "3.24.3")
        self.assertEqual(flutter["state"], ["flutter_bloc"])
        self.assertEqual(flutter["routing"], ["go_router"])
        self.assertEqual(flutter["persistence"], ["drift"])
        self.assertEqual(flutter["iosDeploymentTarget"], "13.0")
        self.assertEqual(flutter["androidMinSdk"], 23)
        self.assertEqual(flutter["embedded"], ["ios", "android"])

    def test_plain_directory_has_no_platform(self):
        project = fixtures.Project(git=False)
        self.addCleanup(project.cleanup)
        project.write("README.md", "hello\n")
        project.write("package.json", "{}\n")
        facts = detect.detect(project.root)
        self.assertEqual(facts["platforms"], [])
        self.assertEqual(detect.profile_lines(facts), [])

    def test_recon_counts_patterns_and_sizes(self):
        project = fixtures.android_project(git=True)
        self.addCleanup(project.cleanup)
        project.write("app/src/main/java/com/example/Legacy.kt", "import kotlinx.coroutines.GlobalScope\n\nfun go() { GlobalScope.launch { } }\nval x = a!!\n")
        inv = recon.inventory(project.root)
        self.assertIn("Kotlin", inv["languages"])
        self.assertEqual(inv["patterns"]["GlobalScope"]["files"], 1)
        self.assertEqual(inv["patterns"]["Room entities / DAOs"]["files"], 2)
        self.assertGreaterEqual(inv["tests"]["files"], 1)
        text = recon.render(inv, project.root)
        self.assertIn("Pattern counts", text)
        self.assertIn("GlobalScope", text)


class FingerprintTests(unittest.TestCase):
    def setUp(self):
        self.project = fixtures.ios_project(git=True)
        self.addCleanup(self.project.cleanup)

    def fp(self):
        return verify.source_fingerprint(self.project.root)

    def test_staging_and_committing_do_not_change_it(self):
        clean = self.fp()
        self.project.write("App/Model.swift", "struct Model { let id: String }\n")
        edited = self.fp()
        self.assertNotEqual(clean, edited)
        self.project.git("add", "-A")
        self.assertEqual(self.fp(), edited)
        self.project.commit("edit")
        self.assertEqual(self.fp(), edited)

    def test_only_source_files_count(self):
        clean = self.fp()
        self.project.write("README.md", "docs\n")
        self.project.write("notes/todo.txt", "x\n")
        self.assertEqual(self.fp(), clean)
        self.project.write("App/New.swift", "struct New {}\n")
        self.assertNotEqual(self.fp(), clean)

    def test_deleting_and_reverting(self):
        clean = self.fp()
        original = self.project.read("App/Model.swift")
        self.project.remove("App/Model.swift")
        self.assertNotEqual(self.fp(), clean)
        self.project.write("App/Model.swift", original)
        self.assertEqual(self.fp(), clean)

    def test_non_git_directory_falls_back_to_walking(self):
        project = fixtures.ios_project(git=False)
        self.addCleanup(project.cleanup)
        first = verify.source_fingerprint(project.root)
        self.assertTrue(first.startswith("walk:"))
        project.write("App/New.swift", "struct New {}\n")
        self.assertNotEqual(verify.source_fingerprint(project.root), first)


class DiagnosticsTests(unittest.TestCase):
    ROOT = "/Users/dev/app"

    def extract(self, text, **kwargs):
        return verify.extract_diagnostics(text, self.ROOT, **kwargs)

    def test_swift_and_clang(self):
        log = "\n".join([
            "CompileSwift normal arm64 /Users/dev/app/App/Model.swift",
            "/Users/dev/app/App/Model.swift:12:9: error: cannot find 'foo' in scope",
            "/Users/dev/app/App/Model.swift:12:9: error: cannot find 'foo' in scope",
            "/Users/dev/app/App/Old.m:3:1: warning: unused variable 'x'",
            "** BUILD FAILED **",
        ])
        found = self.extract(log)
        self.assertEqual(found[0], "App/Model.swift:12:9: cannot find 'foo' in scope")
        self.assertEqual(found.count(found[0]), 1)
        self.assertIn("** BUILD FAILED **", found)
        self.assertFalse(any("unused variable" in line for line in found))
        self.assertTrue(any("unused variable" in line for line in self.extract(log, include_warnings=True)))

    def test_xctest_failure(self):
        found = self.extract("/Users/dev/app/AppTests/ModelTests.swift:9: error: -[AppTests.ModelTests testID] : XCTAssertEqual failed: (\"1\") is not equal to (\"2\")")
        self.assertEqual(len(found), 1)
        self.assertTrue(found[0].startswith("AppTests/ModelTests.swift:9:"))

    def test_kotlin_and_gradle(self):
        log = "\n".join([
            "> Task :app:compileDebugKotlin FAILED",
            "e: file:///Users/dev/app/app/src/main/java/A.kt:7:13 Unresolved reference: bar",
            "FAILURE: Build failed with an exception.",
            "* What went wrong:",
            "Execution failed for task ':app:compileDebugKotlin'.",
            "> Compilation error. See log for more details",
            "",
            "UserTest > name FAILED",
        ])
        found = self.extract(log)
        self.assertIn("app/src/main/java/A.kt:7:13: Unresolved reference: bar", found)
        self.assertIn("> Task :app:compileDebugKotlin FAILED", found)
        self.assertIn("UserTest > name FAILED", found)
        self.assertTrue(any(line.startswith("Gradle: Execution failed") for line in found))

    def test_dart_analyze_and_flutter_test(self):
        log = "\n".join([
            "Analyzing example...",
            "  error • Undefined name 'foo' • lib/main.dart:5:3 • undefined_identifier",
            "   info • Unused import • lib/a.dart:1:8 • unused_import",
            "00:02 +3 -1: counter increments [E]",
            "  Expected: <2>",
            "    Actual: <1>",
            "",
            "00:02 +3 -1: Some tests failed.",
        ])
        found = self.extract(log)
        self.assertIn("lib/main.dart:5:3: Undefined name 'foo' (undefined_identifier)", found)
        self.assertTrue(any("counter increments [E] | Expected: <2> Actual: <1>" in line for line in found))
        self.assertFalse(any("Unused import" in line for line in found))

    def test_unknown_output_falls_back_to_the_tail(self):
        found = self.extract("line one\nline two\nsomething odd happened\n")
        self.assertEqual(found[-1], "something odd happened")

    def test_long_output_is_capped(self):
        log = "\n".join("/Users/dev/app/A.swift:%d:1: error: e%d" % (i, i) for i in range(100))
        found = self.extract(log, limit=10)
        self.assertEqual(len(found), 11)
        self.assertIn("90 more", found[-1])


class VerifyRunTests(unittest.TestCase):
    def run_verify(self, project, **kwargs):
        lines = []
        code = verify.main(project.root, out=lines.append, **kwargs)
        return code, "\n".join(lines)

    def test_configured_command_pass_records_the_state(self):
        project = fixtures.ios_project(git=True)
        self.addCleanup(project.cleanup)
        project.write(".mobile-coding-agents.json", '{"verify": {"ios": {"quick": "true"}}}')
        code, text = self.run_verify(project, level="quick")
        self.assertEqual(code, 0, text)
        self.assertIn("RESULT: PASS", text)
        self.assertEqual(verify.read_stamp(project.root)["fingerprint"], verify.source_fingerprint(project.root))

    def test_failure_prints_diagnostics_and_does_not_record(self):
        project = fixtures.ios_project(git=True)
        self.addCleanup(project.cleanup)
        script = "echo \"$PWD/App/Model.swift:3:5: error: boom\"; exit 65"
        project.write(".mobile-coding-agents.json", '{"verify": {"ios": {"quick": ["true", %s]}}}' % __import__("json").dumps(script))
        code, text = self.run_verify(project, level="quick")
        self.assertEqual(code, 1, text)
        self.assertIn("[ok]   ios-quick-1", text)
        self.assertIn("[FAIL] ios-quick-2 (exit 65", text)
        self.assertIn("App/Model.swift:3:5: boom", text)
        self.assertIn("full log:", text)
        self.assertEqual(verify.read_stamp(project.root), {})

    def test_dry_run_shows_default_plan_for_a_swift_package(self):
        project = fixtures.Project(git=True)
        self.addCleanup(project.cleanup)
        project.write("Package.swift", "// swift-tools-version: 6.0\nlet package = Package(name: \"Kit\", platforms: [.iOS(.v16)])\n")
        project.commit("init")
        code, text = self.run_verify(project, level="full", dry_run=True)
        self.assertEqual(code, 0, text)
        self.assertIn("swift build", text)
        self.assertIn("swift test", text)

    def test_inside_a_sandbox_swiftpm_drops_its_own_and_xcodebuild_is_refused(self):
        from mobilekit import util
        package = fixtures.Project(git=True)
        self.addCleanup(package.cleanup)
        package.write("Package.swift", "// swift-tools-version: 6.0\nlet package = Package(name: \"Kit\", platforms: [.iOS(.v16)])\n")
        package.commit("init")
        app = fixtures.ios_project(git=True)
        self.addCleanup(app.cleanup)
        previous = util._SEATBELT
        self.addCleanup(setattr, util, "_SEATBELT", previous)
        util._SEATBELT = True
        _, text = self.run_verify(package, level="full", dry_run=True)
        self.assertIn("swift build --disable-sandbox", text)
        self.assertIn("swift test --disable-sandbox", text)
        code, text = self.run_verify(app, level="quick")
        self.assertEqual(code, 2, text)
        self.assertIn("sandbox.excludedCommands", text)
        util._SEATBELT = False
        _, text = self.run_verify(package, level="quick", dry_run=True)
        self.assertNotIn("--disable-sandbox", text)

    def test_flavors_need_configuration_instead_of_a_guess(self):
        project = fixtures.android_project(git=True)
        self.addCleanup(project.cleanup)
        project.write("app/build.gradle.kts", project.read("app/build.gradle.kts") + "\nandroid { productFlavors { create(\"staging\") } }\n")
        code, text = self.run_verify(project, level="quick")
        self.assertEqual(code, 2, text)
        self.assertIn("product flavors", text)
        self.assertIn("CANNOT VERIFY", text)

    def test_android_and_flutter_default_plans(self):
        android = fixtures.android_project(git=True)
        self.addCleanup(android.cleanup)
        _, text = self.run_verify(android, level="test", dry_run=True)
        self.assertIn("./gradlew --console=plain -q testDebugUnitTest", text)
        flutter = fixtures.flutter_project(git=True)
        self.addCleanup(flutter.cleanup)
        _, text = self.run_verify(flutter, level="quick", dry_run=True)
        self.assertIn("flutter analyze", text)

    def test_config_problems_are_reported(self):
        project = fixtures.ios_project(git=False)
        self.addCleanup(project.cleanup)
        project.write(".mobile-coding-agents.json", '{"verifyGate": "sometimes", "prompts": "many", "nope": 1, "prLines": "many"}')
        config = config_module.load(project.root)
        self.assertEqual(config["verifyGate"], "notice")
        self.assertEqual(config["prompts"], "few")
        self.assertEqual(len(config.problems), 4)

    def test_defaults_do_not_hold_the_agent_or_stop_a_person_for_routine_work(self):
        project = fixtures.ios_project(git=False)
        self.addCleanup(project.cleanup)
        config = config_module.load(project.root)
        self.assertEqual((config["verifyGate"], config["prompts"]), ("notice", "few"))
        self.assertTrue(config.asks("publish") and config.asks("lost-work"))
        self.assertFalse(config.asks("device-data") or config.asks("install") or config.asks("suppressions"))


if __name__ == "__main__":
    unittest.main()
