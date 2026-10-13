"""Detect which mobile platforms a repository holds and the facts an agent
gets wrong most often: minimum OS versions, toolchain versions, language
modes, package managers. Pure file parsing; no build tool is started.
"""

import os
import re

from . import util

_PBX_LIMIT = 30_000_000


def _version_key(text):
    return tuple(int(part) for part in re.findall(r"\d+", text)[:3])


def _uniq_sorted_versions(values):
    return sorted(set(values), key=_version_key)


def _first(pattern, text, flags=0):
    match = re.search(pattern, text, flags)
    return match.group(1) if match else None


def _yaml_section_keys(text, section):
    """Top-level keys of a two-space-indented YAML mapping section."""
    keys, inside = [], False
    for line in text.splitlines():
        if re.match(r"^%s:\s*(#.*)?$" % re.escape(section), line):
            inside = True
            continue
        if inside:
            if line and not line[0].isspace() and not line.startswith("#"):
                break
            match = re.match(r"^  ([A-Za-z0-9_]+):", line)
            if match:
                keys.append(match.group(1))
    return keys


def _collect(root):
    found = {
        "pubspec": [], "xcodeproj": [], "xcworkspace": [], "package_swift": [],
        "podfile": [], "settings_gradle": [], "build_gradle": [], "manifest": [],
        "xcconfig": [], "counts": {}, "names": set(),
    }
    counts = found["counts"]
    for rel, is_dir in util.walk(root, max_depth=14):
        name = rel.rsplit(os.sep, 1)[-1]
        if is_dir:
            if name.endswith(".xcodeproj"):
                found["xcodeproj"].append(rel)
            elif name.endswith(".xcworkspace"):
                found["xcworkspace"].append(rel)
            continue
        ext = os.path.splitext(name)[1]
        counts[ext] = counts.get(ext, 0) + 1
        if name == "pubspec.yaml":
            found["pubspec"].append(rel)
        elif name == "Package.swift":
            found["package_swift"].append(rel)
        elif name == "Podfile":
            found["podfile"].append(rel)
        elif name in ("settings.gradle", "settings.gradle.kts"):
            found["settings_gradle"].append(rel)
        elif name in ("build.gradle", "build.gradle.kts"):
            found["build_gradle"].append(rel)
        elif name == "AndroidManifest.xml":
            found["manifest"].append(rel)
        elif ext == ".xcconfig":
            found["xcconfig"].append(rel)
        if os.sep not in rel:
            found["names"].add(name)
    return found


def _under(path, roots):
    for base in roots:
        if base == "" or path == base or path.startswith(base + os.sep):
            return True
    return False


def _ios_facts(root, found, native_projects, native_packages, native_podfiles, native_xcconfigs=()):
    facts = {
        "projects": native_projects[:6], "workspaces": [], "packages": native_packages[:6],
        "deploymentTargets": [], "swiftVersions": [], "strictConcurrency": [],
        "defaultActorIsolation": [], "packageManagers": [], "schemes": [],
        "objcFiles": 0, "synchronizedFolders": False, "lint": [],
    }
    targets, swift_versions, strict, isolation, approachable, upcoming = [], [], [], [], [], []
    spm_in_project = False

    def read_settings(text, assign):
        """Pull the build settings that change what advice is correct."""
        key = lambda name: r"(?m)^\s*%s(?:\[[^\]]*\])?\s*=\s*" % name if assign == "xcconfig" else r"%s = " % name
        end = r"\s*$" if assign == "xcconfig" else ";"
        targets.extend(re.findall(key("IPHONEOS_DEPLOYMENT_TARGET") + r"([\d.]+)" + ("" if assign == "xcconfig" else end), text))
        swift_versions.extend(re.findall(key("SWIFT_VERSION") + r"([\d.]+)", text))
        strict.extend(re.findall(key("SWIFT_STRICT_CONCURRENCY") + r"(\w+)", text))
        isolation.extend(re.findall(key("SWIFT_DEFAULT_ACTOR_ISOLATION") + r"(\w+)", text))
        approachable.extend(re.findall(key("SWIFT_APPROACHABLE_CONCURRENCY") + r"(\w+)", text))
        upcoming.extend(re.findall(r"SWIFT_UPCOMING_FEATURE_(\w+)\s*=\s*YES", text))

    for project in native_projects[:6]:
        text = util.read_text(os.path.join(root, project, "project.pbxproj"), limit=_PBX_LIMIT)
        if not text:
            # Xcode 27 can store the project as JSON (`*.xcproj` inside the bundle).
            try:
                names = sorted(n for n in os.listdir(os.path.join(root, project)) if n.endswith(".xcproj"))
            except OSError:
                names = []
            if names:
                facts["jsonProjectFile"] = True
                text = util.read_text(os.path.join(root, project, names[0]), limit=_PBX_LIMIT)
                # Same keys, JSON punctuation: normalise `"KEY" : "value"` to `KEY = value;`.
                text = re.sub(r'"([A-Z][A-Z0-9_]+)"\s*:\s*"([^"\n]*)"', r"\1 = \2;", text)
        read_settings(text, "pbxproj")
        if "XCRemoteSwiftPackageReference" in text or "XCLocalSwiftPackageReference" in text:
            spm_in_project = True
        if "PBXFileSystemSynchronizedRootGroup" in text:
            facts["synchronizedFolders"] = True
        scheme_dir = os.path.join(root, project, "xcshareddata", "xcschemes")
        if os.path.isdir(scheme_dir):
            facts["schemes"] += [n[:-9] for n in sorted(os.listdir(scheme_dir)) if n.endswith(".xcscheme")]
    for xcconfig in native_xcconfigs[:40]:
        read_settings(util.read_text(os.path.join(root, xcconfig), limit=200_000), "xcconfig")
    for workspace in found["xcworkspace"]:
        if ".xcodeproj" + os.sep in workspace + os.sep and workspace.endswith("project.xcworkspace"):
            continue
        if _under(workspace, [p for p in native_projects]):
            continue
        facts["workspaces"].append(workspace)
        scheme_dir = os.path.join(root, workspace, "xcshareddata", "xcschemes")
        if os.path.isdir(scheme_dir):
            facts["schemes"] += [n[:-9] for n in sorted(os.listdir(scheme_dir)) if n.endswith(".xcscheme")]
    facts["workspaces"] = facts["workspaces"][:6]
    tools_versions = []
    for package in native_packages[:6]:
        text = util.read_text(os.path.join(root, package))
        tools = _first(r"swift-tools-version:\s*([\d.]+)", text)
        if tools:
            tools_versions.append(tools)
        for major, minor in re.findall(r"\.iOS\(\s*\.v(\d+)(?:_(\d+))?\s*\)", text):
            targets.append("%s.%s" % (major, minor or "0"))
        targets += re.findall(r"\.iOS\(\s*\"([\d.]+)\"\s*\)", text)
        swift_versions += re.findall(r"swiftLanguage(?:Modes|Versions):\s*\[\s*\.v(\d+)", text)
    for podfile in native_podfiles[:3]:
        text = util.read_text(os.path.join(root, podfile))
        target = _first(r"platform\s+:ios\s*,\s*['\"]([\d.]+)['\"]", text)
        if not target:
            variable = _first(r"platform\s+:ios\s*,\s*([A-Za-z_]\w*)", text)
            if variable:
                target = _first(r"(?m)^\s*%s\s*=\s*['\"]([\d.]+)['\"]" % re.escape(variable), text)
        if target:
            targets.append(target)
    managers = []
    if native_packages or spm_in_project:
        managers.append("SwiftPM")
    if native_podfiles:
        managers.append("CocoaPods")
    if "Cartfile" in found["names"]:
        managers.append("Carthage")
    facts["packageManagers"] = managers
    facts["deploymentTargets"] = _uniq_sorted_versions(targets)
    facts["swiftVersions"] = _uniq_sorted_versions(swift_versions)
    facts["swiftToolsVersions"] = _uniq_sorted_versions(tools_versions)
    facts["strictConcurrency"] = sorted(set(strict))
    facts["defaultActorIsolation"] = sorted(set(isolation))
    facts["approachableConcurrency"] = sorted(set(approachable))
    facts["upcomingFeatures"] = sorted(set(upcoming))
    facts["schemes"] = sorted(set(facts["schemes"]))[:12]
    facts["objcFiles"] = found["counts"].get(".m", 0) + found["counts"].get(".mm", 0)
    facts["swiftFiles"] = found["counts"].get(".swift", 0)
    for name in (".swiftlint.yml", ".swiftformat", ".swift-format"):
        if name in found["names"]:
            facts["lint"].append(name)
    if "project.yml" in found["names"]:
        facts["generator"] = "XcodeGen"
    elif "Project.swift" in found["names"]:
        facts["generator"] = "Tuist"
    return facts


def _android_facts(root, found, native_settings, native_builds):
    facts = {
        "gradle": None, "agp": None, "kotlin": None, "composeBom": None,
        "compileSdk": [], "minSdk": [], "targetSdk": [], "modules": 0,
        "flags": [], "lint": [], "javaFiles": 0, "kotlinFiles": 0,
    }
    base = os.path.dirname(native_settings[0]) if native_settings else ""
    wrapper = util.read_text(os.path.join(root, base, "gradle", "wrapper", "gradle-wrapper.properties"))
    facts["gradle"] = _first(r"gradle-([\d.]+)-", wrapper)
    catalog = util.read_text(os.path.join(root, base, "gradle", "libs.versions.toml"))
    if catalog:
        facts["versionCatalog"] = True
        facts["agp"] = _first(r"(?mi)^\s*(?:agp|android[-_]?gradle[-_]?plugin|androidGradlePlugin)\s*=\s*\"([\d.\w-]+)\"", catalog)
        facts["kotlin"] = _first(r"(?mi)^\s*kotlin\s*=\s*\"([\d.\w-]+)\"", catalog)
        facts["composeBom"] = _first(r"(?mi)^\s*(?:compose[-_]?bom|composeBom)\s*=\s*\"([\d.\w-]+)\"", catalog)
    flags = set()
    compile_sdk, min_sdk, target_sdk = [], [], []
    sources = [catalog]
    for build in native_builds[:200]:
        sources.append(util.read_text(os.path.join(root, build), limit=400_000))
    for text in sources:
        if not text:
            continue
        compile_sdk += re.findall(r"compileSdk(?:Version)?\s*[=( ]\s*(\d{2})\b", text)
        min_sdk += re.findall(r"minSdk(?:Version)?\s*[=( ]\s*(\d{2})\b", text)
        target_sdk += re.findall(r"targetSdk(?:Version)?\s*[=( ]\s*(\d{2})\b", text)
        compile_sdk += re.findall(r"(?mi)^\s*compile[-_]?sdk\s*=\s*\"(\d{2})\"", text)
        min_sdk += re.findall(r"(?mi)^\s*min[-_]?sdk\s*=\s*\"(\d{2})\"", text)
        target_sdk += re.findall(r"(?mi)^\s*target[-_]?sdk\s*=\s*\"(\d{2})\"", text)
        if not facts["agp"]:
            facts["agp"] = _first(r"com\.android\.tools\.build:gradle:([\d.\w-]+)", text) or _first(
                r"id\s*\(?\s*[\"']com\.android\.(?:application|library)[\"']\s*\)?\s*version\s*[\"']([\d.\w-]+)[\"']", text)
        if not facts["kotlin"]:
            facts["kotlin"] = _first(r"org\.jetbrains\.kotlin[\w.:-]*[\"']\s*\)?\s*version\s*[\"']([\d.\w-]+)[\"']", text) or _first(
                r"kotlin_version\s*=\s*[\"']([\d.\w-]+)[\"']", text)
        if re.search(r"\bkapt\b", text):
            flags.add("kapt")
        if re.search(r"\bksp\b|com\.google\.devtools\.ksp", text):
            flags.add("ksp")
        if re.search(r"compose\s*(?:=\s*)?true|kotlin\.plugin\.compose|androidx\.compose", text):
            flags.add("compose")
        if "productFlavors" in text:
            flags.add("flavors")
        if re.search(r"viewBinding\s*(?:=\s*)?true|viewBinding\s*\{", text):
            flags.add("viewBinding")
        if re.search(r"dataBinding\s*(?:=\s*)?true|dataBinding\s*\{", text):
            flags.add("dataBinding")
        if "dagger.hilt" in text or "hilt-android" in text:
            flags.add("hilt")
        if "androidx.room" in text:
            flags.add("room")
        if "io.reactivex" in text:
            flags.add("rxjava")
        if "kotlin.multiplatform" in text or 'kotlin("multiplatform")' in text:
            flags.add("kmp")
    modules = 0
    for settings in native_settings[:2]:
        text = util.read_text(os.path.join(root, settings))
        modules += len(re.findall(r"[\"']:[\w:.-]+[\"']", text))
    facts["modules"] = modules
    facts["compileSdk"] = sorted(set(int(v) for v in compile_sdk))
    facts["minSdk"] = sorted(set(int(v) for v in min_sdk))
    facts["targetSdk"] = sorted(set(int(v) for v in target_sdk))
    facts["flags"] = sorted(flags)
    facts["javaFiles"] = found["counts"].get(".java", 0)
    facts["kotlinFiles"] = found["counts"].get(".kt", 0)
    for rel in ("detekt.yml", "config/detekt/detekt.yml", "detekt-config.yml", ".editorconfig", "lint.xml"):
        if os.path.isfile(os.path.join(root, base, rel)):
            facts["lint"].append(rel)
    return facts


def _flutter_facts(root, flutter_roots):
    main = flutter_roots[0]
    text = util.read_text(os.path.join(root, main, "pubspec.yaml"))
    deps = _yaml_section_keys(text, "dependencies")
    dev_deps = _yaml_section_keys(text, "dev_dependencies")
    all_deps = set(deps) | set(dev_deps)
    env = {}
    inside = False
    for line in text.splitlines():
        if re.match(r"^environment:\s*$", line):
            inside = True
            continue
        if inside:
            if line and not line[0].isspace():
                break
            match = re.match(r"^\s+(sdk|flutter):\s*[\"']?([^\"'#]+?)[\"']?\s*(#.*)?$", line)
            if match:
                env[match.group(1)] = match.group(2).strip()

    def pick(*names):
        return [n for n in names if n in all_deps]

    facts = {
        "root": main or ".",
        "name": _first(r"(?m)^name:\s*(\S+)", text),
        "dartSdk": env.get("sdk"), "flutterSdk": env.get("flutter"),
        "packages": len(flutter_roots),
        "state": pick("flutter_riverpod", "hooks_riverpod", "riverpod", "flutter_bloc", "bloc", "provider", "get", "mobx", "flutter_redux", "signals"),
        "routing": pick("go_router", "auto_route", "beamer"),
        "persistence": pick("drift", "sqflite", "hive", "hive_ce", "isar", "objectbox", "floor", "shared_preferences", "flutter_secure_storage"),
        "codegen": pick("build_runner", "freezed", "json_serializable", "pigeon"),
        "lints": pick("flutter_lints", "very_good_analysis", "lints", "custom_lint"),
        "testing": pick("patrol", "integration_test", "golden_toolkit", "alchemist", "mocktail", "mockito", "bloc_test"),
        "embedded": [d for d in ("ios", "android", "web", "macos", "windows", "linux") if os.path.isdir(os.path.join(root, main, d))],
    }
    fvmrc = util.read_json(os.path.join(root, main, ".fvmrc"), default=None)
    if isinstance(fvmrc, dict) and fvmrc.get("flutter"):
        facts["pinnedFlutter"] = str(fvmrc["flutter"])
    else:
        legacy = util.read_json(os.path.join(root, main, ".fvm", "fvm_config.json"), default=None)
        if isinstance(legacy, dict) and legacy.get("flutterSdkVersion"):
            facts["pinnedFlutter"] = str(legacy["flutterSdkVersion"])
    if os.path.isfile(os.path.join(root, "melos.yaml")) or re.search(r"(?m)^workspace:\s*$", text):
        facts["workspace"] = True
    if os.path.isfile(os.path.join(root, main, "analysis_options.yaml")):
        facts["analysisOptions"] = True
    android_build = util.read_text(os.path.join(root, main, "android", "app", "build.gradle.kts")) or util.read_text(
        os.path.join(root, main, "android", "app", "build.gradle"))
    min_sdk = _first(r"minSdk(?:Version)?\s*[=( ]\s*(\d{2})\b", android_build)
    if min_sdk:
        facts["androidMinSdk"] = int(min_sdk)
    podfile = util.read_text(os.path.join(root, main, "ios", "Podfile"))
    ios_target = _first(r"platform\s+:ios\s*,\s*['\"]([\d.]+)['\"]", podfile)
    if not ios_target:
        pbx = util.read_text(os.path.join(root, main, "ios", "Runner.xcodeproj", "project.pbxproj"), limit=_PBX_LIMIT)
        found_targets = _uniq_sorted_versions(re.findall(r"IPHONEOS_DEPLOYMENT_TARGET = ([\d.]+);", pbx))
        ios_target = found_targets[0] if found_targets else None
    if ios_target:
        facts["iosDeploymentTarget"] = ios_target
    return facts


def detect(root):
    """Return a dictionary of platform facts for the repository at root."""
    found = _collect(root)
    flutter_roots = []
    for rel in sorted(found["pubspec"], key=lambda p: (p.count(os.sep), p)):
        text = util.read_text(os.path.join(root, rel))
        if re.search(r"(?m)^\s+sdk:\s*flutter\s*$", text) or re.search(r"(?m)^\s+flutter:\s*$", text):
            flutter_roots.append(os.path.dirname(rel))
    native_projects = [p for p in found["xcodeproj"] if not _under(p, flutter_roots)]
    native_packages = [p for p in found["package_swift"] if not _under(p, flutter_roots)]
    native_podfiles = [p for p in found["podfile"] if not _under(p, flutter_roots)]
    native_settings = [p for p in found["settings_gradle"] if not _under(p, flutter_roots)]
    native_builds = [p for p in found["build_gradle"] if not _under(p, flutter_roots)]
    native_manifests = [p for p in found["manifest"] if not _under(p, flutter_roots)]

    result = {"root": root, "platforms": [], "notes": []}
    if native_projects or native_packages or native_podfiles:
        result["platforms"].append("ios")
        native_xcconfigs = [p for p in found["xcconfig"] if not _under(p, flutter_roots)]
        result["ios"] = _ios_facts(root, found, native_projects, native_packages, native_podfiles, native_xcconfigs)
    is_android = False
    if native_settings or native_builds:
        blob = "".join(util.read_text(os.path.join(root, p), limit=200_000) for p in (native_builds + native_settings)[:40])
        blob += util.read_text(os.path.join(root, os.path.dirname(native_settings[0]) if native_settings else "", "gradle", "libs.versions.toml"))
        is_android = "com.android" in blob or bool(native_manifests)
    if is_android:
        result["platforms"].append("android")
        result["android"] = _android_facts(root, found, native_settings, native_builds)
        if "kmp" in result["android"]["flags"]:
            result["notes"].append("Kotlin Multiplatform detected: shared code has constraints the Android skill does not cover.")
    if flutter_roots:
        result["platforms"].append("flutter")
        result["flutter"] = _flutter_facts(root, flutter_roots)
    return result


def _join(values, empty="unknown"):
    values = [str(v) for v in values if v not in (None, "", [])]
    return ", ".join(values) if values else empty


def profile_lines(facts):
    """A compact, factual profile for the session-start context (<= 9 lines)."""
    lines = []
    ios = facts.get("ios")
    if ios:
        parts = []
        if ios["deploymentTargets"]:
            lowest = ios["deploymentTargets"][0]
            spread = "" if len(ios["deploymentTargets"]) == 1 else " (targets range up to %s)" % ios["deploymentTargets"][-1]
            parts.append("minimum iOS %s%s" % (lowest, spread))
        else:
            parts.append("minimum iOS not found in project files")
        if ios["swiftVersions"]:
            parts.append("Swift language mode %s" % _join(ios["swiftVersions"]))
        if ios.get("swiftToolsVersions"):
            parts.append("swift-tools-version %s" % _join(ios["swiftToolsVersions"]))
        if ios["strictConcurrency"]:
            parts.append("strict concurrency %s" % _join(ios["strictConcurrency"]))
        if ios["defaultActorIsolation"]:
            parts.append("default actor isolation %s" % _join(ios["defaultActorIsolation"]))
        if ios.get("approachableConcurrency"):
            parts.append("approachable concurrency %s" % _join(ios["approachableConcurrency"]))
        if ios.get("upcomingFeatures"):
            parts.append("upcoming features on: %s" % _join(ios["upcomingFeatures"][:6]))
        if ios["packageManagers"]:
            parts.append(_join(ios["packageManagers"]))
        if ios["objcFiles"]:
            parts.append("%d Objective-C files beside %d Swift" % (ios["objcFiles"], ios.get("swiftFiles", 0)))
        if ios.get("jsonProjectFile"):
            parts.append("JSON project file (.xcproj)")
        elif ios["projects"] and not ios["synchronizedFolders"]:
            parts.append("explicit file references in project.pbxproj (new files must be added to the target)")
        if ios["schemes"]:
            parts.append("shared schemes: %s" % _join(ios["schemes"][:5]))
        lines.append("- iOS: " + "; ".join(parts))
    android = facts.get("android")
    if android:
        parts = []
        parts.append("minSdk %s" % (_join(android["minSdk"][:1]) if android["minSdk"] else "not found"))
        if android["compileSdk"]:
            parts.append("compileSdk %s" % android["compileSdk"][-1])
        if android["targetSdk"]:
            parts.append("targetSdk %s" % android["targetSdk"][-1])
        if android["agp"]:
            parts.append("AGP %s" % android["agp"])
        if android["kotlin"]:
            parts.append("Kotlin %s" % android["kotlin"])
        if android["gradle"]:
            parts.append("Gradle %s" % android["gradle"])
        if android["composeBom"]:
            parts.append("Compose BOM %s" % android["composeBom"])
        if android["flags"]:
            parts.append("uses %s" % _join(android["flags"]))
        if android["javaFiles"]:
            parts.append("%d Java files beside %d Kotlin" % (android["javaFiles"], android["kotlinFiles"]))
        if android["modules"]:
            parts.append("%d Gradle modules" % android["modules"])
        lines.append("- Android: " + "; ".join(parts))
    flutter = facts.get("flutter")
    if flutter:
        parts = []
        parts.append("Dart SDK constraint %s" % (flutter.get("dartSdk") or "not set"))
        if flutter.get("pinnedFlutter"):
            parts.append("Flutter pinned to %s (fvm)" % flutter["pinnedFlutter"])
        elif flutter.get("flutterSdk"):
            parts.append("Flutter constraint %s" % flutter["flutterSdk"])
        if flutter["state"]:
            parts.append("state: %s" % _join(flutter["state"]))
        if flutter["routing"]:
            parts.append("routing: %s" % _join(flutter["routing"]))
        if flutter["persistence"]:
            parts.append("persistence: %s" % _join(flutter["persistence"]))
        if flutter["codegen"]:
            parts.append("codegen: %s" % _join(flutter["codegen"]))
        if flutter.get("iosDeploymentTarget"):
            parts.append("embedded iOS minimum %s" % flutter["iosDeploymentTarget"])
        if flutter.get("androidMinSdk"):
            parts.append("embedded Android minSdk %s" % flutter["androidMinSdk"])
        if flutter.get("packages", 1) > 1:
            parts.append("%d Dart packages" % flutter["packages"])
        lines.append("- Flutter: " + "; ".join(parts))
    for note in facts.get("notes", []):
        lines.append("- Note: " + note)
    return lines
