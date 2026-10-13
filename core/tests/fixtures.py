"""Throwaway project trees for the tests. Nothing here touches a real repository."""

import os
import shutil
import subprocess
import sys
import tempfile

LIB = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
BIN = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "bin", "mobile"))
if LIB not in sys.path:
    sys.path.insert(0, LIB)

PBXPROJ = """// !$*UTF8*$!
{
	objectVersion = 56;
	objects = {
		A1 /* Debug */ = {
			buildSettings = {
				IPHONEOS_DEPLOYMENT_TARGET = 15.0;
				SWIFT_VERSION = 5.0;
				SWIFT_STRICT_CONCURRENCY = minimal;
			};
		};
		A2 /* Release */ = {
			buildSettings = {
				IPHONEOS_DEPLOYMENT_TARGET = 16.0;
				SWIFT_VERSION = 5.0;
			};
		};
	};
}
"""

SCHEME = '<?xml version="1.0" encoding="UTF-8"?>\n<Scheme version="1.7"></Scheme>\n'

ROOM_ENTITY = """package com.example.data

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "users")
data class User(
    @PrimaryKey val id: Long,
    val name: String,
)
"""

ROOM_DB = """package com.example.data

import androidx.room.Database
import androidx.room.RoomDatabase

@Database(entities = [User::class], version = 3, exportSchema = true)
abstract class AppDatabase : RoomDatabase()
"""

MANIFEST = """<manifest xmlns:android="http://schemas.android.com/apk/res/android">
    <uses-permission android:name="android.permission.INTERNET" />
    <application android:label="Example" />
</manifest>
"""

DRIFT_DB = """import 'package:drift/drift.dart';

class Todos extends Table {
  IntColumn get id => integer().autoIncrement()();
  TextColumn get title => text()();
}

@DriftDatabase(tables: [Todos])
class AppDatabase extends _$AppDatabase {
  AppDatabase(super.e);

  @override
  int get schemaVersion => 2;
}
"""


class Project(object):
    """A temporary directory with helpers to write files and drive git."""

    def __init__(self, git=True):
        self.root = os.path.realpath(tempfile.mkdtemp(prefix="mobile-coding-agents-test-"))
        if git:
            self.git("init", "-q", "-b", "main")
            self.git("config", "user.email", "test@example.com")
            self.git("config", "user.name", "Test")
            self.git("config", "commit.gpgsign", "false")

    def write(self, rel, content=""):
        path = os.path.join(self.root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(content)
        return path

    def read(self, rel):
        with open(os.path.join(self.root, rel), "r", encoding="utf-8") as handle:
            return handle.read()

    def exists(self, rel):
        return os.path.exists(os.path.join(self.root, rel))

    def remove(self, rel):
        os.remove(os.path.join(self.root, rel))

    def git(self, *args):
        proc = subprocess.run(["git", "-C", self.root] + list(args), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        if proc.returncode != 0:
            raise AssertionError("git %s failed: %s" % (" ".join(args), proc.stdout.decode()))
        return proc.stdout.decode()

    def commit(self, message="commit"):
        self.git("add", "-A")
        self.git("commit", "-q", "-m", message, "--allow-empty")

    def cleanup(self):
        shutil.rmtree(self.root, ignore_errors=True)


def ios_project(git=True):
    project = Project(git=git)
    project.write("App.xcodeproj/project.pbxproj", PBXPROJ)
    project.write("App.xcodeproj/xcshareddata/xcschemes/App.xcscheme", SCHEME)
    project.write("App/Model.swift", "import Foundation\n\nstruct Model {\n    let id: Int\n}\n")
    project.write("App/Legacy.m", "@implementation Legacy\n@end\n")
    project.write("App/Info.plist", "<plist><dict>\n</dict></plist>\n")
    project.write("AppTests/ModelTests.swift", "import XCTest\n\nfinal class ModelTests: XCTestCase {\n    func testID() {\n        XCTAssertEqual(Model(id: 1).id, 1)\n        XCTAssertNotNil(Model(id: 2))\n    }\n}\n")
    project.write(".swiftlint.yml", "disabled_rules: []\n")
    if git:
        project.commit("initial")
    return project


def android_project(git=True):
    project = Project(git=git)
    project.write("settings.gradle.kts", 'rootProject.name = "Example"\ninclude(":app", ":core:data")\n')
    project.write("build.gradle.kts", "plugins {\n    alias(libs.plugins.android.application) apply false\n}\n")
    project.write("gradle/libs.versions.toml", '[versions]\nagp = "8.7.3"\nkotlin = "2.0.21"\ncomposeBom = "2024.12.01"\nminSdk = "24"\n')
    project.write("gradle/wrapper/gradle-wrapper.properties", "distributionUrl=https\\://services.gradle.org/distributions/gradle-8.11.1-bin.zip\n")
    project.write("gradlew", "#!/bin/sh\nexit 0\n")
    project.write("app/build.gradle.kts", 'plugins { id("com.android.application") }\nandroid {\n    compileSdk = 35\n    defaultConfig {\n        minSdk = 24\n        targetSdk = 35\n    }\n    buildFeatures { compose = true }\n}\ndependencies {\n    kapt(libs.room.compiler)\n    implementation(libs.androidx.room.runtime)\n}\n')
    project.write("app/src/main/AndroidManifest.xml", MANIFEST)
    project.write("app/src/main/java/com/example/data/User.kt", ROOM_ENTITY)
    project.write("app/src/main/java/com/example/data/AppDatabase.kt", ROOM_DB)
    project.write("app/src/test/java/com/example/UserTest.kt", "class UserTest {\n    fun name() {\n        assertEquals(\"a\", User(1, \"a\").name)\n        assertTrue(true)\n    }\n}\n")
    if git:
        project.commit("initial")
    return project


def flutter_project(git=True):
    project = Project(git=git)
    project.write("pubspec.yaml", "name: example\nenvironment:\n  sdk: \">=3.4.0 <4.0.0\"\n  flutter: \">=3.22.0\"\ndependencies:\n  flutter:\n    sdk: flutter\n  flutter_bloc: ^8.1.0\n  go_router: ^14.0.0\n  drift: ^2.20.0\ndev_dependencies:\n  build_runner: ^2.4.0\n  flutter_lints: ^4.0.0\n")
    project.write(".fvmrc", '{"flutter": "3.24.3"}\n')
    project.write("lib/main.dart", "import 'package:flutter/material.dart';\n\nvoid main() => runApp(const SizedBox());\n")
    project.write("lib/db.dart", DRIFT_DB)
    project.write("lib/model.g.dart", "// GENERATED CODE - DO NOT MODIFY BY HAND\n")
    project.write("ios/Runner.xcodeproj/project.pbxproj", PBXPROJ)
    project.write("ios/Podfile", "platform :ios, '13.0'\n")
    project.write("android/app/build.gradle", "android {\n    defaultConfig {\n        minSdkVersion 23\n    }\n}\n")
    project.write("test/widget_test.dart", "void main() {\n  expect(1, 1);\n}\n")
    if git:
        project.commit("initial")
    return project
