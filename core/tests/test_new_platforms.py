import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

import fixtures
from mobilekit import config as config_module
from mobilekit import detect, guards, recon, verify


class ReactNativeTests(unittest.TestCase):
    def test_a_react_native_app_owns_its_native_folders(self):
        project = fixtures.react_native_project()
        self.addCleanup(project.cleanup)
        facts = detect.detect(project.root)
        self.assertEqual(facts["platforms"], ["react-native"], "ios/ and android/ belong to the app, as in Flutter")
        rn = facts["react-native"]
        self.assertEqual((rn["reactNative"], rn["packageManager"], rn["typescript"], rn["newArchitecture"]), ("0.81.4", "yarn", True, True))
        self.assertEqual(rn["state"], ["zustand"])
        self.assertEqual(rn["navigation"], ["@react-navigation/native"])
        self.assertEqual((rn["iosDeploymentTarget"], rn["androidMinSdk"]), ("15.1", 24))
        self.assertNotIn("expo", rn)
        line = "\n".join(detect.profile_lines(facts))
        for expected in ("react-native 0.81.4", "New Architecture on", "TypeScript", "package manager yarn", "embedded Android minSdk 24"):
            self.assertIn(expected, line)
        facts["react-native"]["reactNative"] = "^0.87.1"
        self.assertIn("New Architecture (the only one since 0.82)", "\n".join(detect.profile_lines(facts)))

    def test_expo_generated_native_folders_are_named_as_such(self):
        project = fixtures.react_native_project(expo=True)
        self.addCleanup(project.cleanup)
        rn = detect.detect(project.root)["react-native"]
        self.assertTrue(rn["generatedNative"])
        self.assertEqual(rn["navigation"], ["expo-router", "@react-navigation/native"])
        self.assertIn("never hand-edit", "\n".join(detect.profile_lines({"platforms": ["react-native"], "react-native": rn})))

    def test_a_native_app_with_a_tooling_package_json_is_not_react_native(self):
        project = fixtures.ios_project()
        self.addCleanup(project.cleanup)
        project.write("package.json", json.dumps({"devDependencies": {"danger": "^12.0.0"}}))
        self.assertEqual(detect.detect(project.root)["platforms"], ["ios"])

    def test_react_native_embedded_in_a_native_app(self):
        project = fixtures.ios_project()
        self.addCleanup(project.cleanup)
        project.write("js/package.json", json.dumps({"dependencies": {"react-native": "0.81.4"}}))
        self.assertEqual(detect.detect(project.root)["platforms"], ["ios", "react-native"])

    def test_default_verify_plan_uses_the_projects_scripts_and_package_manager(self):
        project = fixtures.react_native_project()
        self.addCleanup(project.cleanup)
        facts, config = detect.detect(project.root), config_module.load(project.root)
        quick, problems = verify.plan(project.root, config, facts, "quick")
        self.assertEqual((problems, [s.display() for s in quick]), ([], ["yarn run typecheck"]))
        project.write("src/screens/New.tsx", "export const a = 1;\n")
        quick, _ = verify.plan(project.root, config, facts, "quick")
        self.assertEqual([s.display() for s in quick], ["yarn run typecheck", "yarn eslint src/screens/New.tsx"])
        test, _ = verify.plan(project.root, config, facts, "test")
        self.assertEqual([s.display() for s in test], ["yarn jest --ci"])
        full, _ = verify.plan(project.root, config, facts, "full")
        self.assertEqual([s.display() for s in full], ["yarn run typecheck", "yarn run lint", "yarn jest --ci"])

    def test_javascript_counts_as_source_only_in_a_react_native_project(self):
        rn = fixtures.react_native_project()
        self.addCleanup(rn.cleanup)
        before = verify.source_fingerprint(rn.root, ["react-native"])
        rn.write("App.tsx", "export default function App() {\n  return 1;\n}\n")
        self.assertNotEqual(verify.source_fingerprint(rn.root, ["react-native"]), before)
        ios = fixtures.ios_project()
        self.addCleanup(ios.cleanup)
        before = verify.source_fingerprint(ios.root, ["ios"])
        ios.write("scripts/tool.js", "console.log(1);\n")
        self.assertEqual(verify.source_fingerprint(ios.root, ["ios"]), before, "a build script is not app source")

    def test_recon_counts_javascript_patterns_and_tests(self):
        project = fixtures.react_native_project()
        self.addCleanup(project.cleanup)
        inv = recon.inventory(project.root)
        self.assertEqual(inv["languages"]["TypeScript (TSX)"]["files"], 3)
        self.assertEqual(inv["patterns"]["class components"]["count"], 1)
        self.assertIn("old native-module access (NativeModules, UIManager, findNodeHandle, setNativeProps)", inv["patterns"])
        self.assertEqual(inv["patterns"]["Jest test cases"]["count"], 1)
        self.assertEqual(inv["tests"]["files"], 1)
        self.assertNotIn("node_modules", recon.render(inv, project.root))

    def test_typescript_eslint_and_jest_failures_are_extracted(self):
        log = "\n".join([
            "src/App.tsx(12,5): error TS2322: Type 'string' is not assignable to type 'number'.",
            "/work/app/src/screens/Home.tsx",
            "  3:10  error  'unused' is defined but never used  @typescript-eslint/no-unused-vars",
            "  9:1   warning  Unexpected console statement  no-console",
            "FAIL __tests__/App.test.tsx",
            "  ● App › renders the title",
            "  ● Console",
        ])
        found = verify.extract_diagnostics(log, "/work/app")
        self.assertIn("src/App.tsx(12,5): Type 'string' is not assignable to type 'number'. (TS2322)", found)
        self.assertIn("src/screens/Home.tsx:3:10: 'unused' is defined but never used (@typescript-eslint/no-unused-vars)", found)
        self.assertIn("FAIL __tests__/App.test.tsx", found)
        self.assertIn("App › renders the title", found)
        self.assertEqual(len(found), 4, found)


class ReactNativeGuardTests(unittest.TestCase):
    def setUp(self):
        self.project = fixtures.react_native_project(expo=True)
        self.addCleanup(self.project.cleanup)
        self.config = config_module.load(self.project.root)

    def edit(self, rel, new="x", old=""):
        return guards.check_edit("Edit", {"file_path": self.project.root + "/" + rel, "old_string": old, "new_string": new}, self.config, self.project.root)

    def test_generated_native_folder_is_refused_with_the_right_route(self):
        self.project.write("ios/Example/Info.plist", "<plist/>\n")
        verdict = self.edit("ios/Example/Info.plist")
        self.assertEqual(verdict.decision, "deny")
        self.assertIn("app.json", verdict.reason)
        self.assertIsNone(self.edit("app.json").decision)

    def test_a_project_that_patches_its_generated_folder_gets_a_note_instead(self):
        self.project.write("cng-patches/ios+Example+Info.plist.patch", "diff\n")
        self.project.write("ios/Example/Info.plist", "<plist/>\n")
        verdict = self.edit("ios/Example/Info.plist")
        self.assertIsNone(verdict.decision)
        self.assertIn("patch-project", verdict.context[0][1])

    def test_native_folder_kept_in_git_is_ordinary_source(self):
        bare = fixtures.react_native_project()
        self.addCleanup(bare.cleanup)
        verdict = guards.check_edit("Edit", {"file_path": bare.root + "/android/app/build.gradle", "old_string": "a", "new_string": "b"},
                                    config_module.load(bare.root), bare.root)
        self.assertIsNone(verdict.decision)

    def test_lockfiles_and_node_modules(self):
        for rel in ("yarn.lock", "package-lock.json", "pnpm-lock.yaml", "bun.lock"):
            self.assertEqual(self.edit(rel).decision, "deny", rel)
        verdict = self.edit("node_modules/left-pad/index.js")
        self.assertIsNone(verdict.decision)
        self.assertEqual([ident for ident, _ in verdict.context], ["node_modules"])
        self.assertIn("patch", verdict.context[0][1])

    def test_shipping_javascript_or_a_build_asks_and_routine_commands_do_not(self):
        def decide(command):
            return guards.check_bash(command, self.config, self.project.root).decision
        for command in ("npx eas update --branch production", "eas submit -p ios", "yarn eas build -p ios --auto-submit",
                        "npx --yes eas-cli@latest update", "pnpm dlx eas-cli submit", "npm publish", "yarn npm publish",
                        "appcenter codepush release-react -a owner/app", "npx hot-updater deploy"):
            self.assertEqual(decide(command), "ask", command)
        for command in ("eas build --platform ios", "npx expo start", "npx expo prebuild --clean", "npm install", "yarn test",
                        "npx tsc --noEmit", "npm run lint", "npm publish --dry-run", "eas update:list", "npx expo install expo-camera"):
            self.assertIsNone(decide(command), command)


class KotlinMultiplatformTests(unittest.TestCase):
    def test_shared_code_is_detected_beside_both_apps(self):
        project = fixtures.kmp_project()
        self.addCleanup(project.cleanup)
        facts = detect.detect(project.root)
        self.assertEqual(facts["platforms"], ["ios", "android", "kotlin-multiplatform"])
        kmp = facts["kotlin-multiplatform"]
        self.assertEqual(kmp["modules"], ["shared"])
        self.assertEqual(kmp["targets"], ["androidTarget", "iosArm64", "iosSimulatorArm64"])
        self.assertEqual(kmp["composeMultiplatform"], "1.9.0")
        self.assertEqual(kmp["iosFramework"], ["direct integration (Xcode build phase)"])
        self.assertEqual(kmp["uses"], ["ktor"])
        lines = detect.profile_lines(facts)
        self.assertEqual(len(lines), 3)
        self.assertIn("shared modules: shared", lines[2])
        self.assertEqual(facts["notes"], [])

    def test_default_verify_plan_compiles_one_apple_target_and_runs_all_tests(self):
        project = fixtures.kmp_project()
        self.addCleanup(project.cleanup)
        facts, config = detect.detect(project.root), config_module.load(project.root)
        quick, problems = verify.plan(project.root, config, facts, "quick", ["kotlin-multiplatform"])
        self.assertEqual((problems, [s.display() for s in quick]), ([], ["./gradlew --console=plain -q compileKotlinIosSimulatorArm64"]))
        test, _ = verify.plan(project.root, config, facts, "test", ["kotlin-multiplatform"])
        self.assertEqual([s.display() for s in test], ["./gradlew --console=plain -q allTests"])

    def test_recon_counts_source_sets_and_expect_actual(self):
        project = fixtures.kmp_project()
        self.addCleanup(project.cleanup)
        inv = recon.inventory(project.root)
        self.assertEqual(inv["sourceSets"], {"commonMain": 1, "androidMain": 1, "iosMain": 1, "commonTest": 1})
        self.assertEqual(inv["patterns"]["expect declarations (multiplatform)"]["count"], 1)
        self.assertEqual(inv["patterns"]["actual declarations (multiplatform)"]["count"], 2)
        self.assertIn("Kotlin files per source set", recon.render(inv, project.root))
        self.assertEqual(inv["tests"]["files"], 1, "commonTest is test code")


class CommonCodeGuardTests(unittest.TestCase):
    """Common Kotlin code is compiled for every target, so a one-platform API there breaks another target's build."""

    def setUp(self):
        self.project = fixtures.kmp_project(git=False)
        self.addCleanup(self.project.cleanup)
        self.config = config_module.load(self.project.root)

    def edit(self, rel, new, old=""):
        return guards.check_edit("Edit", {"file_path": self.project.root + "/" + rel, "old_string": old, "new_string": new}, self.config, self.project.root)

    def test_one_platform_api_in_common_code_is_refused_with_the_route(self):
        for text in ("import java.time.Instant\nfun now() = Instant.now().toString()\n",
                     "fun id() = java.util.UUID.randomUUID().toString()\n",
                     "import android.content.Context\n",
                     "import platform.Foundation.NSDate\n"):
            verdict = self.edit("shared/src/commonMain/kotlin/A.kt", text)
            self.assertEqual(verdict.decision, "deny", text)
            self.assertIn("expect", verdict.reason)

    def test_java_lang_calls_need_no_import_and_are_refused_too(self):
        for text in ("fun now() = System.currentTimeMillis()\n", "fun price(c: Long) = String.format(\"%.2f\", c / 100.0)\n",
                     "fun pause() = Thread.sleep(10)\n", "fun r(x: Double) = Math.round(x)\n"):
            verdict = self.edit("shared/src/commonMain/kotlin/A.kt", text)
            self.assertEqual(verdict.decision, "deny", text)
            self.assertIn("java.lang", verdict.reason)
        commented = "// do not use System.currentTimeMillis() here\nfun now() = kotlin.time.Clock.System.now()\n"
        self.assertIsNone(self.edit("shared/src/commonMain/kotlin/A.kt", commented).decision, "a comment is not a call")

    def test_percent_format_on_a_literal_gets_a_note(self):
        verdict = self.edit("shared/src/commonMain/kotlin/A.kt", 'fun price(c: Long) = "%.2f".format(c / 100.0)\n')
        self.assertIsNone(verdict.decision)
        self.assertEqual([ident for ident, _ in verdict.context], ["common-percent-format"])
        self.assertEqual(self.edit("shared/src/androidMain/kotlin/A.kt", 'val a = "%.2f".format(1.0)\n').context, [])

    def test_multiplatform_apis_and_platform_source_sets_pass(self):
        for rel, text in (
                ("shared/src/commonMain/kotlin/A.kt", "import kotlin.uuid.Uuid\nimport kotlin.jvm.JvmInline\nimport androidx.compose.runtime.Composable\n"),
                ("shared/src/androidMain/kotlin/A.kt", "import java.time.Instant\nimport android.content.Context\n"),
                ("shared/src/iosMain/kotlin/A.kt", "import platform.Foundation.NSDate\n")):
            self.assertIsNone(self.edit(rel, text).decision, rel)

    def test_an_api_that_was_already_there_is_not_new(self):
        kept = "import java.util.UUID\n"
        self.assertIsNone(self.edit("shared/src/commonMain/kotlin/A.kt", kept + "val a = 1\n", old=kept).decision)

    def test_a_module_whose_targets_all_have_the_api_is_left_alone(self):
        self.project.write("jvmonly/build.gradle.kts", "kotlin {\n    jvm()\n    androidTarget()\n}\n")
        self.assertIsNone(self.edit("jvmonly/src/commonMain/kotlin/A.kt", "import java.util.UUID\n").decision)

    def test_unknown_targets_get_a_note_not_a_refusal(self):
        verdict = self.edit("other/src/commonMain/kotlin/A.kt", "import java.util.UUID\n")
        self.assertIsNone(verdict.decision)
        self.assertEqual(len(verdict.context), 1)


class NewStackRiskTests(unittest.TestCase):
    def idents(self, project):
        from mobilekit import risk
        return {f.ident: f for f in risk.analyze(project.root)[2]}

    def test_sqldelight_schema_change_without_a_migration_warns(self):
        project = fixtures.kmp_project()
        self.addCleanup(project.cleanup)
        project.write("shared/src/commonMain/sqldelight/db/Task.sq", "CREATE TABLE task (\n  id INTEGER NOT NULL PRIMARY KEY\n);\n")
        project.commit("schema")
        project.write("shared/src/commonMain/sqldelight/db/Task.sq", "CREATE TABLE task (\n  id INTEGER NOT NULL PRIMARY KEY,\n  done INTEGER NOT NULL DEFAULT 0\n);\n")
        self.assertIn("schema-sqldelight-no-migration", self.idents(project))
        project.write("shared/src/commonMain/sqldelight/migrations/1.sqm", "ALTER TABLE task ADD COLUMN done INTEGER NOT NULL DEFAULT 0;\n")
        self.assertNotIn("schema-sqldelight-no-migration", self.idents(project))

    def test_expo_app_config_and_package_json_signals(self):
        project = fixtures.react_native_project(expo=True)
        self.addCleanup(project.cleanup)
        project.write("app.json", '{"expo": {"name": "Example", "newArchEnabled": true,\n "ios": {"infoPlist": {"NSCameraUsageDescription": "Scan codes"}},\n "android": {"permissions": ["android.permission.CAMERA"]}}}\n')
        package = json.loads(project.read("package.json"))
        package["dependencies"]["react-native"] = "0.82.0"
        package["dependencies"]["expo-camera"] = "~17.0.0"
        package["scripts"]["lint"] = "eslint . --max-warnings 0"
        project.write("package.json", json.dumps(package, indent=2))
        found = self.idents(project)
        self.assertIn("NSCameraUsageDescription", found["capability-change"].message)
        self.assertIn("CAMERA", found["capability-change"].message)
        self.assertEqual(found["toolchain-or-min-version"].files, ["package.json"])
        self.assertEqual(found["dependency-change"].files, ["package.json"])

    def test_a_script_edit_alone_is_not_a_dependency_change(self):
        project = fixtures.react_native_project()
        self.addCleanup(project.cleanup)
        package = json.loads(project.read("package.json"))
        package["scripts"]["lint"] = "eslint . --max-warnings 0"
        project.write("package.json", json.dumps(package, indent=2))
        self.assertEqual(self.idents(project), {})


class AdoptNewPlatformTests(unittest.TestCase):
    def adopt(self, project):
        from mobilekit import adopt
        lines = []
        code = adopt.main(project.root, marketplace="acme/mobile-coding-agents", out=lines.append)
        self.assertEqual(code, 0, "\n".join(lines))
        return json.loads(project.read(".claude/settings.json"))

    def test_kotlin_multiplatform_project_gets_all_three_packs(self):
        project = fixtures.kmp_project()
        self.addCleanup(project.cleanup)
        settings = self.adopt(project)
        self.assertEqual(sorted(settings["enabledPlugins"]), [
            "mobile-android@mobile-coding-agents", "mobile-core@mobile-coding-agents",
            "mobile-ios@mobile-coding-agents", "mobile-kotlin-multiplatform@mobile-coding-agents"])
        self.assertIn("mobile-kotlin-multiplatform:kotlin-multiplatform", project.read(".claude/rules/mobile-kotlin-multiplatform.md"))
        claude = project.read("CLAUDE.md")
        self.assertIn("`mobile-kotlin-multiplatform:kotlin-multiplatform`", claude)
        self.assertNotIn("mobile-flutter", claude, "only the skills for the platforms that are here")
        self.assertNotIn("{{", claude)

    def test_react_native_project_gets_its_pack_and_only_shipping_asks(self):
        project = fixtures.react_native_project(expo=True)
        self.addCleanup(project.cleanup)
        settings = self.adopt(project)
        self.assertEqual(sorted(settings["enabledPlugins"]), ["mobile-core@mobile-coding-agents", "mobile-react-native@mobile-coding-agents"])
        self.assertIn("mobile-react-native:react-native", project.read(".claude/rules/mobile-react-native.md"))
        asks = settings["permissions"]["ask"]
        self.assertIn("Bash(eas update *)", asks)
        self.assertFalse([rule for rule in asks if "test" in rule or "lint" in rule or "install" in rule], "routine commands never ask")
        self.assertIn("React Native application.", project.read("AGENTS.md"))


class ArchitectureFactTests(unittest.TestCase):
    """The pattern a codebase uses is told at session start, from file names alone."""

    def test_coordinators_put_the_navigation_rule_in_the_session_facts(self):
        project = fixtures.ios_project()
        self.addCleanup(project.cleanup)
        project.write("App/Coordinator/AppCoordinator.swift", "final class AppCoordinator {}\n")
        project.write("App/Orders/OrdersViewModel.swift", "final class OrdersViewModel {}\n")
        project.write("AppTests/OrdersViewModelTests.swift", "final class OrdersViewModelTests {}\n")
        facts = detect.detect(project.root)
        self.assertEqual(facts["architecture"], {"coordinators": 1, "view models": 1}, "test files are not counted")
        line = [l for l in detect.profile_lines(facts) if l.startswith("- Architecture")][0]
        self.assertIn("1 coordinator, 1 view model", line)
        self.assertIn("screens do not create or push each other", line)

    def test_other_markers_are_listed_without_a_navigation_rule(self):
        project = fixtures.flutter_project()
        self.addCleanup(project.cleanup)
        project.write("lib/orders/bloc/orders_bloc.dart", "class OrdersBloc {}\n")
        project.write("lib/orders/data/orders_repository.dart", "class OrdersRepository {}\n")
        line = [l for l in detect.profile_lines(detect.detect(project.root)) if l.startswith("- Architecture")][0]
        self.assertIn("1 bloc or cubit", line)
        self.assertNotIn("Navigation belongs", line)

    def test_a_project_with_no_markers_gets_no_line(self):
        project = fixtures.ios_project()
        self.addCleanup(project.cleanup)
        self.assertFalse([l for l in detect.profile_lines(detect.detect(project.root)) if l.startswith("- Architecture")])


class ArchitectureCountTests(unittest.TestCase):
    def test_recon_counts_the_markers_that_name_an_architecture(self):
        project = fixtures.ios_project()
        self.addCleanup(project.cleanup)
        project.write("App/Orders/OrdersCoordinator.swift", "import Swinject\nfinal class OrdersCoordinator {}\nprotocol Coordinator {}\n")
        project.write("App/Orders/OrdersViewModel.swift", "final class OrdersViewModel {}\nstruct LoadOrdersUseCase {}\nprotocol OrdersRepository {}\n")
        project.write("App/Cart/CartFeature.swift", "@Reducer\nstruct CartFeature {}\n")
        project.write("App/Legacy/ProfilePresenter.swift", "final class ProfilePresenter {}\nfinal class ProfileInteractor {}\n")
        patterns = recon.inventory(project.root)["patterns"]
        for label, count in (("coordinators", 2), ("view models", 1), ("use cases", 1), ("repositories", 1), ("TCA reducers", 1),
                             ("VIPER parts (presenter, interactor, wireframe)", 2), ("dependency-injection library imports", 1)):
            self.assertEqual(patterns[label]["count"], count, label)


if __name__ == "__main__":
    unittest.main()
