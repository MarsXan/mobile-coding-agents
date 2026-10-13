import unittest

import fixtures
from mobilekit import risk


def findings(project, base=None):
    _, _, found = risk.analyze(project.root, base)
    return {f.ident: f for f in found}


class RoomTests(unittest.TestCase):
    def setUp(self):
        self.project = fixtures.android_project(git=True)
        self.addCleanup(self.project.cleanup)
        self.entity = "app/src/main/java/com/example/data/User.kt"
        self.database = "app/src/main/java/com/example/data/AppDatabase.kt"

    def add_column(self):
        self.project.write(self.entity, fixtures.ROOM_ENTITY.replace("val name: String,", "val name: String,\n    val nickname: String?,"))

    def test_entity_change_without_version_bump_blocks(self):
        self.add_column()
        found = findings(self.project)
        self.assertEqual(found["schema-room-no-version"].severity, "block")
        self.assertEqual(found["schema-room-no-version"].files, [self.entity])

    def test_version_bump_without_migration_blocks(self):
        self.add_column()
        self.project.write(self.database, fixtures.ROOM_DB.replace("version = 3", "version = 4"))
        found = findings(self.project)
        self.assertNotIn("schema-room-no-version", found)
        self.assertEqual(found["schema-room-no-migration"].severity, "block")
        self.assertEqual(found["schema-room-no-export"].severity, "warn")

    def test_destructive_fallback_blocks(self):
        self.add_column()
        self.project.write(self.database, fixtures.ROOM_DB.replace("version = 3", "version = 4") + "\n// builder.fallbackToDestructiveMigration()\n")
        self.assertEqual(findings(self.project)["schema-room-destructive"].severity, "block")

    def test_complete_migration_has_no_schema_finding(self):
        self.add_column()
        self.project.write(self.database, fixtures.ROOM_DB.replace("version = 3", "version = 4") + "\nval MIGRATION_3_4 = object : Migration(3, 4) {}\n")
        self.project.write("app/schemas/com.example.data.AppDatabase/4.json", "{}\n")
        found = findings(self.project)
        self.assertEqual([k for k in found if k.startswith("schema-")], [])

    def test_comment_only_change_is_not_a_schema_change(self):
        self.project.write(self.entity, "// people who use the app\n" + fixtures.ROOM_ENTITY)
        self.assertEqual([k for k in findings(self.project) if k.startswith("schema-")], [])

    def test_committed_changes_count_against_the_base_branch(self):
        self.project.git("checkout", "-q", "-b", "feature/nickname")
        self.add_column()
        self.project.commit("add nickname")
        self.assertIn("schema-room-no-version", findings(self.project))
        self.assertEqual(risk.main(self.project.root, out=lambda *_: None), 1)
        self.assertEqual(risk.main(self.project.root, fail_on="never", out=lambda *_: None), 0)


class OtherSchemaTests(unittest.TestCase):
    def test_core_data_model_edited_in_place_blocks_and_new_version_informs(self):
        project = fixtures.ios_project(git=True)
        self.addCleanup(project.cleanup)
        project.write("App/Model.xcdatamodeld/Model.xcdatamodel/contents", "<model><entity name=\"User\"/></model>\n")
        project.commit("model v1")
        project.write("App/Model.xcdatamodeld/Model.xcdatamodel/contents", "<model><entity name=\"User\"><attribute name=\"nick\"/></entity></model>\n")
        self.assertEqual(findings(project)["schema-coredata-in-place"].severity, "block")
        project.git("checkout", "-q", "--", "App/Model.xcdatamodeld/Model.xcdatamodel/contents")
        project.write("App/Model.xcdatamodeld/Model 2.xcdatamodel/contents", "<model><entity name=\"User\"><attribute name=\"nick\"/></entity></model>\n")
        found = findings(project)
        self.assertNotIn("schema-coredata-in-place", found)
        self.assertEqual(found["schema-coredata-new-version"].severity, "info")

    def test_swiftdata_model_change_warns_unless_a_migration_plan_is_in_the_diff(self):
        project = fixtures.ios_project(git=True)
        self.addCleanup(project.cleanup)
        project.write("App/Trip.swift", "import SwiftData\n\n@Model\nfinal class Trip {\n    var name: String\n    init(name: String) { self.name = name }\n}\n")
        project.commit("trip")
        project.write("App/Trip.swift", "import SwiftData\n\n@Model\nfinal class Trip {\n    var title: String\n    init(title: String) { self.title = title }\n}\n")
        self.assertEqual(findings(project)["schema-swiftdata"].severity, "warn")
        project.write("App/Migration.swift", "enum Plan: SchemaMigrationPlan {}\nenum V2: VersionedSchema {}\n")
        self.assertNotIn("schema-swiftdata", findings(project))

    def test_drift_table_change_needs_version_and_migration(self):
        project = fixtures.flutter_project(git=True)
        self.addCleanup(project.cleanup)
        changed = fixtures.DRIFT_DB.replace("TextColumn get title => text()();", "TextColumn get title => text()();\n  BoolColumn get done => boolean()();")
        project.write("lib/db.dart", changed)
        self.assertEqual(findings(project)["schema-drift-no-version"].severity, "block")
        project.write("lib/db.dart", changed.replace("schemaVersion => 2", "schemaVersion => 3"))
        found = findings(project)
        self.assertNotIn("schema-drift-no-version", found)
        self.assertEqual(found["schema-drift-no-migration"].severity, "block")
        project.write("lib/db.dart", changed.replace("schemaVersion => 2", "schemaVersion => 3") + "\n// onUpgrade: (m, from, to) async { await m.addColumn(todos, todos.done); }\n")
        self.assertEqual([k for k in findings(project) if k.startswith("schema-")], [])


class CapabilityAndQualityTests(unittest.TestCase):
    def test_android_permission_and_exported_component(self):
        project = fixtures.android_project(git=True)
        self.addCleanup(project.cleanup)
        project.write("app/src/main/AndroidManifest.xml", fixtures.MANIFEST.replace(
            '<application android:label="Example" />',
            '<uses-permission android:name="android.permission.CAMERA" />\n    <application android:label="Example">\n        <activity android:name=".Share" android:exported="true" />\n    </application>'))
        finding = findings(project)["capability-change"]
        self.assertEqual(finding.severity, "warn")
        self.assertIn("CAMERA", finding.message)
        self.assertIn("exported component", finding.message)

    def test_ios_usage_description_and_ats_exception(self):
        project = fixtures.ios_project(git=True)
        self.addCleanup(project.cleanup)
        project.write("App/Info.plist", "<plist><dict>\n<key>NSCameraUsageDescription</key>\n<string>Scan codes</string>\n<key>NSAppTransportSecurity</key>\n<dict><key>NSAllowsArbitraryLoads</key><true/></dict>\n</dict></plist>\n")
        message = findings(project)["capability-change"].message
        self.assertIn("NSCameraUsageDescription", message)
        self.assertIn("App Transport Security", message)

    def test_weakened_tests_are_reported(self):
        project = fixtures.ios_project(git=True)
        self.addCleanup(project.cleanup)
        project.write("AppTests/ModelTests.swift", "import XCTest\n\nfinal class ModelTests: XCTestCase {\n    func testID() {\n        XCTAssertNotNil(Model(id: 2))\n    }\n}\n")
        self.assertIn("assertions-removed", findings(project))
        project.remove("AppTests/ModelTests.swift")
        self.assertIn("tests-deleted", findings(project))

    def test_snapshot_tolerance_and_rerecorded_images(self):
        project = fixtures.ios_project(git=True)
        self.addCleanup(project.cleanup)
        project.write("AppTests/SnapshotTests.swift", "func testView() {\n    assertSnapshot(of: view, as: .image(precision: 0.9))\n}\n")
        project.write("AppTests/__Snapshots__/SnapshotTests/testView.1.png", "not really a png")
        found = findings(project)
        self.assertEqual(found["snapshot-tolerance"].severity, "warn")
        self.assertEqual(found["snapshots-rerecorded"].severity, "info")

    def test_suppressions_secrets_versions_and_signing(self):
        project = fixtures.android_project(git=True)
        self.addCleanup(project.cleanup)
        project.write("app/src/main/java/com/example/Api.kt", "@Suppress(\"UNCHECKED_CAST\")\nval key = \"AIza" + "B" * 35 + "\"\n")
        project.write("gradle/libs.versions.toml", '[versions]\nagp = "8.7.3"\nkotlin = "2.0.21"\ncomposeBom = "2024.12.01"\nminSdk = "26"\n')
        project.write("fastlane/Fastfile", "lane :beta do\nend\n")
        project.write("app/proguard-rules.pro", "-dontobfuscate\n-keep class ** { *; }\n")
        found = findings(project)
        self.assertEqual(found["secret-in-diff"].severity, "block")
        self.assertEqual(found["suppression-added"].severity, "warn")
        self.assertEqual(found["toolchain-or-min-version"].files, ["gradle/libs.versions.toml"])
        self.assertEqual(found["signing-release-ci"].files, ["fastlane/Fastfile"])
        self.assertEqual(found["shrinker-loosened"].files, ["app/proguard-rules.pro"])

    def test_dependency_and_size_signals(self):
        project = fixtures.flutter_project(git=True)
        self.addCleanup(project.cleanup)
        project.write("pubspec.yaml", project.read("pubspec.yaml").replace("  drift: ^2.20.0\n", "  drift: ^2.20.0\n  dio: ^5.7.0\n"))
        project.write("lib/big.dart", "\n".join("final v%d = %d;" % (i, i) for i in range(450)) + "\n")
        found = findings(project)
        self.assertEqual(found["dependency-change"].severity, "info")
        self.assertEqual(found["large-change"].severity, "warn")

    def test_clean_change_reports_nothing_and_exits_zero(self):
        project = fixtures.ios_project(git=True)
        self.addCleanup(project.cleanup)
        project.write("App/Model.swift", "import Foundation\n\nstruct Model {\n    let id: Int\n    var isValid: Bool { id > 0 }\n}\n")
        self.assertEqual(findings(project), {})
        lines = []
        self.assertEqual(risk.main(project.root, out=lines.append), 0)
        self.assertIn("That is not a review", "\n".join(lines))

    def test_not_a_git_repository(self):
        project = fixtures.ios_project(git=False)
        self.addCleanup(project.cleanup)
        self.assertEqual(risk.main(project.root, out=lambda *_: None), 2)


if __name__ == "__main__":
    unittest.main()
