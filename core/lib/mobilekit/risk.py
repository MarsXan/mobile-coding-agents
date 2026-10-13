"""`mobile risk`: read a diff the way a mobile release owner would.

Each sensor answers one question a reviewer otherwise has to remember to
ask: did stored data change shape without a migration, did the app gain a
permission, did the minimum OS move, were tests or checks quietly weakened.
Findings are facts from the diff, each with the files that triggered it.

Severity: `block` should stop a merge until answered, `warn` needs a human
decision, `info` is context for the reviewer.
"""

import json
import os
import re

from . import config as config_module
from . import guards, util

BLOCK, WARN, INFO = "block", "warn", "info"
_RANK = {BLOCK: 0, WARN: 1, INFO: 2}

_TEST_PATH = util.TEST_PATH
_ASSERTION = re.compile(r"\bXCTAssert\w*\(|#expect\(|#require\(|\bassert\w*\(|\bexpect\w*\(|\bverify\w*\(|\bassertThat\(|\bcheck\(")
_TOLERANCE = re.compile(r"\b(?:perceptualPrecision|precision|maxPercentDifference|changeThreshold|maxDiffPixelRatio|maxDiffPixels|tolerance)\b\s*[:=(]")
_SNAPSHOT_IMAGE = re.compile(r"(__Snapshots__|/goldens?/|/screenshots?/|/snapshots/).*\.(png|jpe?g|webp)$", re.I)

_ROOM_FIELD = re.compile(r"\b(?:val|var)\s+\w+\s*:|@(?:ColumnInfo|PrimaryKey|Embedded|ForeignKey|Index|Entity|Relation|TypeConverters?)\b|^\s*(?:private|public|protected)\s+[\w<>\[\], ?]+\s+\w+\s*(?:=|;)")
_ROOM_VERSION = re.compile(r"\bversion\s*=\s*\d+")
_ROOM_MIGRATION = re.compile(r"\bMigration\s*\(|\bAutoMigration\s*\(|\baddMigrations\s*\(|: *Migration\b")
_SWIFTDATA_FIELD = re.compile(r"^\s*(?:@Attribute|@Relationship|@Transient|(?:public |private |internal |final )*(?:var|let)\s+\w+)")
_SWIFTDATA_MIGRATION = re.compile(r"\bVersionedSchema\b|\bSchemaMigrationPlan\b|\bMigrationStage\b")
_DRIFT_COLUMN = re.compile(r"=>\s*(?:integer|text|boolean|dateTime|real|blob|int64|customType)\b|\bColumn<|\bextends\s+Table\b")
_DRIFT_VERSION = re.compile(r"\bschemaVersion\b\s*=>?\s*\d+")
_DRIFT_MIGRATION = re.compile(r"\bonUpgrade\b|\bMigrationStrategy\b|\bstepByStep\b|\bm\.(?:addColumn|createTable|alterTable|renameColumn|deleteTable|drop\w+)\b")

_MIN_VERSION = re.compile(
    r"IPHONEOS_DEPLOYMENT_TARGET\s*=|\bminSdk(?:Version)?\b|\btargetSdk(?:Version)?\b|\bcompileSdk(?:Version)?\b|"
    r"platform\s+:ios|\.iOS\(\s*\.v\d|swift-tools-version|SWIFT_VERSION\s*=|^\s*(?:sdk|flutter):\s*[\"'^>=<\d]|"
    r"^\s*(?:agp|kotlin|min[-_]?sdk|target[-_]?sdk|compile[-_]?sdk)\s*=\s*\"", re.M)
_DEP_LINE = re.compile(
    r"\.package\(\s*(?:url|path|name):|^\s*pod\s+['\"]|\b(?:implementation|api|kapt|ksp|testImplementation|androidTestImplementation|"
    r"debugImplementation|compileOnly|runtimeOnly)\s*\(?\s*[\"'(]|^\s*[\w.-]+\s*=\s*\{\s*(?:module|group)\s*=|^  [a-z_0-9]+:\s*[\^\"'\d<>=a]", re.M)
_SHRINK_LOOSEN = re.compile(r"^\s*-(?:dontobfuscate|dontoptimize|dontshrink|ignorewarnings|keep\s+class\s+\*\*|keep\s+class\s+\*\s*\{|dontwarn\s+\*\*)", re.M)
_DEBUG_LEFTOVER = re.compile(r"^\s*(?:print\(|debugPrint\(|NSLog\(|Log\.[dv]\(|println\(|console\.log\()")


class Finding(object):
    def __init__(self, ident, severity, message, files=()):
        self.ident, self.severity, self.message = ident, severity, message
        self.files = sorted(set(files))[:8]

    def as_dict(self):
        return {"id": self.ident, "severity": self.severity, "message": self.message, "files": self.files}


class FileChange(object):
    def __init__(self, path, status="M"):
        self.path, self.status = path, status
        self.added, self.removed = [], []
        self.binary = False


def resolve_base(root, config, base=None):
    """The commit a change is measured against: the merge base with the base branch."""
    candidates = [base] if base else []
    if not base:
        if config["baseBranch"]:
            candidates += ["origin/" + config["baseBranch"], config["baseBranch"]]
        candidates += ["origin/HEAD", "origin/main", "origin/master", "origin/develop", "main", "master", "develop"]
    for candidate in candidates:
        code, _ = util.git(root, "rev-parse", "--verify", "--quiet", candidate + "^{commit}")
        if code != 0:
            continue
        if base:
            return candidate
        code, out = util.git(root, "merge-base", "HEAD", candidate)
        if code == 0 and out.strip():
            return out.strip()
    return "HEAD"


def collect_changes(root, base):
    """Committed, staged, unstaged and untracked changes relative to base."""
    changes = {}
    code, out = util.git(root, "diff", base, "--name-status", "--no-renames", timeout=60)
    if code == 0:
        for line in out.splitlines():
            parts = line.split("\t")
            if len(parts) >= 2:
                changes[parts[-1]] = FileChange(parts[-1], parts[0][:1])
    code, out = util.git(root, "diff", base, "-U0", "--no-color", "--no-ext-diff", "--no-renames", timeout=120)
    current = None
    if code == 0:
        for line in out.splitlines():
            if line.startswith("+++ "):
                path = line[4:].strip()
                if path.startswith("b/"):
                    current = changes.setdefault(path[2:], FileChange(path[2:]))
                continue
            if line.startswith("--- "):
                path = line[4:].strip()
                if path.startswith("a/"):
                    current = changes.setdefault(path[2:], FileChange(path[2:]))
                continue
            if line.startswith("diff --git") or line.startswith("@@"):
                continue
            if line.startswith("Binary files") and current is not None:
                current.binary = True
                continue
            if current is None:
                continue
            if line.startswith("+"):
                current.added.append(line[1:])
            elif line.startswith("-"):
                current.removed.append(line[1:])
    code, out = util.git(root, "ls-files", "--others", "--exclude-standard")
    if code == 0:
        for path in out.splitlines():
            path = path.strip()
            if not path or path in changes:
                continue
            change = FileChange(path, "A")
            text = util.read_text(os.path.join(root, path), limit=400_000)
            if text:
                change.added = text.splitlines()
            else:
                change.binary = True
            changes[path] = change
    return changes


def _text(lines):
    return "\n".join(lines)


def _file_has(root, path, pattern):
    return bool(pattern.search(util.read_text(os.path.join(root, path), limit=400_000)))


def _schema_findings(root, changes):
    findings = []
    live = [c for c in changes.values() if c.status != "D"]
    all_added = _text([line for c in changes.values() for line in c.added])

    # Core Data
    edited_in_place = [c.path for c in live if c.status == "M" and re.search(r"\.xcdatamodeld/[^/]+\.xcdatamodel/contents$", c.path)]
    new_versions = [c.path for c in live if c.status == "A" and re.search(r"\.xcdatamodeld/[^/]+\.xcdatamodel/contents$", c.path)]
    if edited_in_place:
        findings.append(Finding("schema-coredata-in-place", BLOCK, (
            "An existing Core Data model version was edited in place. Stores on users' devices were created by the old "
            "version and will fail to open or silently lose data. Add a new model version, make it current, and add a "
            "migration test that opens a store saved by the previous version."), edited_in_place))
    elif new_versions:
        findings.append(Finding("schema-coredata-new-version", INFO, (
            "A new Core Data model version was added. Confirm it is the current version and that a test migrates a "
            "store saved by the previous version."), new_versions))

    # Room
    room_entities = [c.path for c in live if c.path.endswith((".kt", ".java"))
                     and any(_ROOM_FIELD.search(l) for l in c.added + c.removed)
                     and _file_has(root, c.path, re.compile(r"@Entity\b"))]
    room_db = [c for c in live if c.path.endswith((".kt", ".java")) and _file_has(root, c.path, re.compile(r"@Database\s*\("))]
    version_bumped = any(_ROOM_VERSION.search(l) for c in room_db for l in c.added)
    schema_added = [c.path for c in live if c.status == "A" and re.search(r"(^|/)schemas/.+/\d+\.json$", c.path)]
    if room_entities and not version_bumped:
        findings.append(Finding("schema-room-no-version", BLOCK, (
            "A Room @Entity changed but the @Database version did not. The app will crash on upgrade with "
            "`IllegalStateException: Room cannot verify the data integrity`. Bump the version and add a Migration "
            "or AutoMigration with a MigrationTestHelper test."), room_entities))
    if version_bumped:
        if "fallbackToDestructiveMigration" in all_added:
            findings.append(Finding("schema-room-destructive", BLOCK, (
                "`fallbackToDestructiveMigration` was added: on upgrade Room deletes the user's local data instead of "
                "migrating it. That is a product decision, not a build fix."), [c.path for c in room_db]))
        elif not _ROOM_MIGRATION.search(all_added):
            findings.append(Finding("schema-room-no-migration", BLOCK, (
                "The Room @Database version was raised but no Migration or AutoMigration was added."), [c.path for c in room_db]))
        if not schema_added:
            findings.append(Finding("schema-room-no-export", WARN, (
                "The Room version changed and no exported schema JSON (schemas/<db>/<version>.json) was added. "
                "MigrationTestHelper and AutoMigration need the exported schema of every version."), [c.path for c in room_db]))

    # SwiftData
    swiftdata = [c.path for c in live if c.path.endswith(".swift")
                 and any(_SWIFTDATA_FIELD.search(l) for l in c.added + c.removed)
                 and _file_has(root, c.path, re.compile(r"@Model\b"))]
    if swiftdata and not _SWIFTDATA_MIGRATION.search(all_added):
        findings.append(Finding("schema-swiftdata", WARN, (
            "A SwiftData @Model changed with no VersionedSchema or SchemaMigrationPlan in the diff. Adding an optional "
            "or defaulted property migrates automatically; renames, type changes, new required properties and "
            "uniqueness changes do not. State which case this is and how it was tested against an existing store."), swiftdata))

    # drift
    drift_tables = [c for c in live if c.path.endswith(".dart") and any(_DRIFT_COLUMN.search(l) for l in c.added + c.removed)]
    drift_bumped = bool(_DRIFT_VERSION.search(all_added))
    if drift_tables and not drift_bumped:
        findings.append(Finding("schema-drift-no-version", BLOCK, (
            "A drift table definition changed but schemaVersion did not. Existing installs keep the old tables and the "
            "generated queries will fail at runtime. Raise schemaVersion and add an onUpgrade step with a schema test."),
            [c.path for c in drift_tables]))
    elif drift_bumped and not _DRIFT_MIGRATION.search(all_added):
        findings.append(Finding("schema-drift-no-migration", BLOCK, (
            "drift schemaVersion was raised but no migration step (onUpgrade / stepByStep / m.addColumn...) was added."),
            [c.path for c in live if c.path.endswith(".dart") and any(_DRIFT_VERSION.search(l) for l in c.added)]))

    # Hive: field indexes are the stored format
    hive = [c.path for c in live if c.path.endswith(".dart") and any("@HiveField(" in l for l in c.removed)]
    if hive:
        findings.append(Finding("schema-hive-field", WARN, (
            "A @HiveField annotation was removed or changed. Hive stores fields by index: an index must never be "
            "reused or renumbered, or existing boxes decode into the wrong fields."), hive))
    return findings


def _capability_findings(changes):
    findings = []
    permissions, usage_keys, flags, files = [], [], [], []
    for change in changes.values():
        if change.status == "D":
            continue
        name = change.path.rsplit("/", 1)[-1]
        added = _text(change.added)
        if name == "AndroidManifest.xml":
            found = re.findall(r"<uses-permission(?:-sdk-\d+)?[^>]*android:name=\"([^\"]+)\"", added)
            permissions += found
            local = [label for needle, label in (
                ('android:exported="true"', "an exported component"),
                ('android:usesCleartextTraffic="true"', "cleartext HTTP allowed"),
                ('android:debuggable="true"', "debuggable build flag"),
                ('android:allowBackup="true"', "app data included in backups"),
                ("android:scheme=", "a deep-link scheme"),
                ('android:requestLegacyExternalStorage="true"', "legacy external storage")) if needle in added]
            flags += local
            if found or local:
                files.append(change.path)
        elif name == "Info.plist" or name.endswith(".plist"):
            keys = re.findall(r"<key>(NS\w+UsageDescription)</key>", added)
            usage_keys += keys
            for needle, label in (
                    ("NSAllowsArbitraryLoads", "App Transport Security exception"),
                    ("CFBundleURLSchemes", "a custom URL scheme"),
                    ("UIBackgroundModes", "a background mode"),
                    ("LSApplicationQueriesSchemes", "queried URL schemes"),
                    ("NSAppTransportSecurity", "App Transport Security settings")):
                if needle in added:
                    flags.append(label)
            if keys or any(needle in added for needle in ("NSAllowsArbitraryLoads", "CFBundleURLSchemes", "UIBackgroundModes")):
                files.append(change.path)
        elif name.endswith(".entitlements"):
            keys = re.findall(r"<key>([^<]+)</key>", added)
            if keys:
                flags.append("entitlements: " + ", ".join(sorted(set(keys))[:5]))
                files.append(change.path)
        elif name == "network_security_config.xml":
            if 'cleartextTrafficPermitted="true"' in added or 'src="user"' in added:
                flags.append("network security config loosened")
                files.append(change.path)
        elif name == "PrivacyInfo.xcprivacy":
            flags.append("privacy manifest changed")
            files.append(change.path)
    if permissions or usage_keys or flags:
        parts = []
        if permissions:
            parts.append("Android permissions added: " + ", ".join(sorted(set(p.rsplit(".", 1)[-1] for p in permissions))))
        if usage_keys:
            parts.append("iOS usage descriptions added: " + ", ".join(sorted(set(usage_keys))))
        if flags:
            parts.append("also: " + "; ".join(sorted(set(flags))))
        findings.append(Finding("capability-change", WARN, (
            "The app's declared capabilities changed (%s). Check the user-facing justification, the runtime request "
            "flow and denial path, store review impact, and the privacy declarations." % ". ".join(parts)), files))
    return findings


def _quality_findings(root, changes, config):
    findings = []
    live = [c for c in changes.values() if c.status != "D"]

    secret_files = []
    for change in live:
        added = _text(change.added)
        for label, pattern in guards._SECRETS:
            match = pattern.search(added)
            if match and not guards._SECRET_PLACEHOLDER.search(match.group(0)):
                secret_files.append("%s (%s)" % (change.path, label))
                break
    if secret_files:
        findings.append(Finding("secret-in-diff", BLOCK, (
            "A credential-shaped value is being added. Once pushed it must be treated as leaked and rotated; "
            "anything compiled into the app is public."), secret_files))

    suppressed = []
    for change in live:
        for label, pattern in guards._SUPPRESSIONS:
            if len(pattern.findall(_text(change.added))) > len(pattern.findall(_text(change.removed))):
                suppressed.append("%s (%s)" % (change.path, label))
                break
    if suppressed:
        findings.append(Finding("suppression-added", WARN, (
            "Checks or tests were silenced rather than satisfied. Each one needs a reason a reviewer accepts."), suppressed))

    deleted_tests = [c.path for c in changes.values() if c.status == "D" and _TEST_PATH.search(c.path)]
    if deleted_tests:
        findings.append(Finding("tests-deleted", WARN, "Test files were deleted. Confirm the behaviour they covered is gone or covered elsewhere.", deleted_tests))
    weaker = []
    looser = []
    for change in live:
        if not _TEST_PATH.search(change.path):
            continue
        removed = len(_ASSERTION.findall(_text(change.removed)))
        added = len(_ASSERTION.findall(_text(change.added)))
        if removed > added:
            weaker.append("%s (%d assertions removed, %d added)" % (change.path, removed, added))
        if len(_TOLERANCE.findall(_text(change.added))) > len(_TOLERANCE.findall(_text(change.removed))):
            looser.append(change.path)
    if weaker:
        findings.append(Finding("assertions-removed", WARN, "Tests now assert less than before. A test that was changed to pass proves nothing.", weaker))
    if looser:
        findings.append(Finding("snapshot-tolerance", WARN, "A snapshot or screenshot comparison tolerance was introduced or changed. Loosening a threshold hides real visual regressions.", looser))
    rerecorded = [c.path for c in live if _SNAPSHOT_IMAGE.search(c.path)]
    if rerecorded:
        findings.append(Finding("snapshots-rerecorded", INFO, "%d reference images were added or re-recorded. Look at them: a re-recorded snapshot accepts whatever the code now draws." % len(rerecorded), rerecorded))

    versions = [c.path for c in live if any(_MIN_VERSION.search(l) for l in c.added + c.removed)
                and c.path.rsplit("/", 1)[-1] in ("project.pbxproj", "Package.swift", "Podfile", "pubspec.yaml", "libs.versions.toml", "build.gradle", "build.gradle.kts", "gradle.properties")]
    if versions:
        findings.append(Finding("toolchain-or-min-version", WARN, (
            "A minimum OS version, SDK level or toolchain version changed. Raising a minimum drops users on older "
            "systems; changing a toolchain changes every build. Both need an explicit decision and a note in the summary."), versions))

    sensitive = []
    for change in live:
        if change.path.rsplit("/", 1)[-1].endswith((".example", ".sample", ".template")):
            continue
        if util.any_glob(change.path, [p for p, _ in config.sensitive_rules()]):
            sensitive.append(change.path)
    if sensitive:
        findings.append(Finding("signing-release-ci", WARN, "Signing, release or CI configuration changed. These files run with secrets or decide what ships.", sensitive))

    shrink = [c.path for c in live if c.path.endswith(".pro") and _SHRINK_LOOSEN.search(_text(c.added))]
    if shrink:
        findings.append(Finding("shrinker-loosened", WARN, "R8/ProGuard rules were loosened broadly (keep-everything, dontobfuscate, dontwarn **). Keep the narrowest rule that fixes the reported class.", shrink))

    manifests = ("Package.swift", "Podfile", "pubspec.yaml", "libs.versions.toml", "build.gradle", "build.gradle.kts")
    dep_files = [c.path for c in live if c.path.rsplit("/", 1)[-1] in manifests and any(_DEP_LINE.search(l) for l in c.added)]
    if dep_files:
        findings.append(Finding("dependency-change", INFO, "Dependencies were added or changed. Check licence, maintenance, binary size and whether the platform already provides it.", dep_files))
    locks = [c.path for c in live if util.any_glob(c.path, [p for p, _ in config_module.LOCKFILES])]
    if locks and not dep_files:
        findings.append(Finding("lockfile-only", INFO, "A lockfile changed without its manifest: a resolver re-ran. Confirm the version drift is intended.", locks))

    generated = [c.path for c in live if util.any_glob(c.path, [p for p, _ in config.generated_rules()])]
    if generated:
        findings.append(Finding("generated-changed", INFO, "Generated files are in the diff. They should match what the generator produces from the committed inputs.", generated))

    leftovers = [c.path for c in live if not _TEST_PATH.search(c.path) and any(_DEBUG_LEFTOVER.search(l) for l in c.added)]
    if leftovers:
        findings.append(Finding("debug-output", INFO, "Debug print statements were added in non-test code.", leftovers))

    source_lines = sum(len(c.added) + len(c.removed) for c in changes.values()
                       if config_module.is_source(c.path) and not util.any_glob(c.path, [p for p, _ in config.generated_rules()]))
    if source_lines > config["prLines"]:
        findings.append(Finding("large-change", WARN, (
            "This change touches %d source lines (limit %d). Large changes are reviewed worse and fail more often; "
            "split by behaviour-preserving step." % (source_lines, config["prLines"]))))
    return findings


def analyze(root, base=None):
    config = config_module.load(root)
    resolved = resolve_base(root, config, base)
    changes = collect_changes(root, resolved)
    findings = _schema_findings(root, changes) + _capability_findings(changes) + _quality_findings(root, changes, config)
    findings.sort(key=lambda f: (_RANK[f.severity], f.ident))
    return resolved, changes, findings


def main(root, base=None, as_json=False, fail_on="block", out=print):
    if not util.git_dir(root):
        out("mobile risk: not a git repository; nothing to compare.")
        return 2
    resolved, changes, findings = analyze(root, base)
    if as_json:
        out(json.dumps({"base": resolved, "filesChanged": len(changes), "findings": [f.as_dict() for f in findings]}, indent=2))
    else:
        out("mobile risk · base %s · %d files changed · %d findings" % (resolved[:12], len(changes), len(findings)))
        for finding in findings:
            out("[%s] %s: %s" % (finding.severity.upper(), finding.ident, finding.message))
            for path in finding.files:
                out("    - " + path)
        if not findings:
            out("No mobile risk signals in this diff. That is not a review: behaviour, concurrency and UI still need reading.")
    worst = min((_RANK[f.severity] for f in findings), default=9)
    threshold = {"block": 0, "warn": 1, "info": 2, "never": -1}.get(fail_on, 0)
    return 1 if worst <= threshold else 0
