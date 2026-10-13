"""Project configuration: `.mobile-coding-agents.json` merged over built-in defaults.

Every list in the file extends the default list; scalars replace. A project
with no file gets the defaults, so the toolkit works before it is configured.
"""

import os

from . import util

CONFIG_NAME = ".mobile-coding-agents.json"

# Files an agent must never hand-edit: they are produced by a tool. The hint
# says how to change them properly.
GENERATED = [
    ("Pods/**", "CocoaPods output. Change the Podfile and run `pod install`."),
    ("Carthage/Build/**", "Carthage output. Change the Cartfile and run `carthage bootstrap`."),
    ("**/DerivedData/**", "Xcode build output."),
    ("**/.build/**", "SwiftPM build output."),
    ("**/.dart_tool/**", "Dart tool output. Run `flutter pub get`."),
    ("**/.gradle/**", "Gradle cache."),
    ("**/build/generated/**", "Gradle generated sources. Change the generator input and rebuild."),
    ("**/build/intermediates/**", "Gradle build output."),
    ("**/*.g.dart", "build_runner output. Change the annotated source and run `dart run build_runner build --delete-conflicting-outputs`."),
    ("**/*.freezed.dart", "freezed output. Change the annotated class and run build_runner."),
    ("**/*.gr.dart", "auto_route output. Change the router definition and run build_runner."),
    ("**/*.mocks.dart", "mockito output. Change the @GenerateMocks annotation and run build_runner."),
    ("**/*.pb.dart", "protoc output. Change the .proto file and regenerate."),
    ("**/*.pb.swift", "protoc output. Change the .proto file and regenerate."),
    ("**/*.generated.swift", "Generated Swift (Sourcery/SwiftGen). Change the template or input and regenerate."),
    ("**/GeneratedPluginRegistrant.*", "Flutter tool output."),
    ("**/gradle/wrapper/gradle-wrapper.jar", "Binary wrapper. Run `./gradlew wrapper --gradle-version <v>`."),
]

# Lockfiles change through their resolver, never by hand.
LOCKFILES = [
    ("**/Package.resolved", "Change Package.swift or the Xcode package reference, then resolve (`swift package resolve` or `xcodebuild -resolvePackageDependencies`)."),
    ("**/Podfile.lock", "Change the Podfile and run `pod install` (or `pod update <Pod>`)."),
    ("**/pubspec.lock", "Change pubspec.yaml and run `flutter pub get` (or `flutter pub upgrade <pkg>`)."),
    ("**/gradle.lockfile", "Change the dependency declaration and run `./gradlew dependencies --write-locks`."),
    ("**/Cartfile.resolved", "Change the Cartfile and run `carthage update`."),
    ("**/Gemfile.lock", "Change the Gemfile and run `bundle install`."),
    ("**/package-lock.json", "Change package.json and run `npm install`."),
    ("**/yarn.lock", "Change package.json and run `yarn install`."),
    ("**/pnpm-lock.yaml", "Change package.json and run `pnpm install`."),
    ("**/bun.lock", "Change package.json and run `bun install`."),
    ("**/bun.lockb", "Change package.json and run `bun install`."),
]

# Signing material is made by its own tool (keytool, Keychain Access, the
# developer portal). Writing over one by hand destroys it, so it is refused.
SIGNING_MATERIAL = [
    ("**/*.jks", "Android signing keystore."),
    ("**/*.keystore", "Android signing keystore."),
    ("**/*.p12", "Signing certificate."),
    ("**/*.p8", "App Store Connect / APNs private key."),
    ("**/*.mobileprovision", "Provisioning profile."),
    ("**/*.provisionprofile", "Provisioning profile."),
]

# Credentials, release and CI configuration. Editing one is allowed: the agent
# is told what the file is and `mobile risk` reports the change for review.
# With `"prompts": "strict"` the edit needs a person's yes instead.
SENSITIVE = [
    ("**/key.properties", "Android signing credentials."),
    ("**/keystore.properties", "Android signing credentials."),
    ("**/local.properties", "Machine-local Android settings; not shared."),
    ("**/.env", "Environment secrets."),
    ("**/.env.*", "Environment secrets."),
    ("**/GoogleService-Info.plist", "Firebase project configuration."),
    ("**/google-services.json", "Firebase project configuration."),
    ("**/ExportOptions.plist", "Xcode export and signing options."),
    ("fastlane/Appfile", "Store account configuration."),
    ("fastlane/Matchfile", "Signing repository configuration."),
    ("fastlane/Fastfile", "Release automation."),
    ("**/eas.json", "Expo build, submit and update profiles."),
    (".mobile-coding-agents.json", "Defines the commands `mobile verify` runs and which guards are on."),
    (".gitlab-ci.yml", "CI pipeline: it runs with the pipeline's secrets."),
    (".github/workflows/**", "CI pipeline: it runs with the pipeline's secrets."),
    ("ci_scripts/**", "Xcode Cloud scripts: they run with the workflow's secrets."),
    ("codemagic.yaml", "CI pipeline: it runs with the pipeline's secrets."),
    ("bitrise.yml", "CI pipeline: it runs with the pipeline's secrets."),
]

# Editing these changes what the store, the OS or the user is told about the
# app. Allowed, with a reminder of what must accompany the change.
CAPABILITY = [
    "**/AndroidManifest.xml", "**/Info.plist", "**/*.entitlements",
    "**/PrivacyInfo.xcprivacy", "**/network_security_config.xml",
]

SOURCE_EXTENSIONS = (
    ".swift", ".m", ".mm", ".h", ".c", ".cpp", ".kt", ".kts", ".java", ".dart",
    ".gradle", ".xcconfig", ".pbxproj", ".xcproj", ".plist", ".xib", ".storyboard",
)
SOURCE_NAMES = (
    "Package.swift", "Podfile", "pubspec.yaml", "AndroidManifest.xml",
    "analysis_options.yaml", "libs.versions.toml", "gradle.properties",
)
# JavaScript and TypeScript count as source only in a React Native project:
# elsewhere they are build scripts or web assets that `mobile verify` does not check.
JS_SOURCE_EXTENSIONS = (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs")
JS_SOURCE_NAMES = ("package.json", "app.json", "tsconfig.json")


def _uses_js(platforms):
    return "react-native" in (platforms or ())


def source_pathspecs(platforms=()):
    """Git pathspecs for the files whose change makes a state unverified."""
    extensions = SOURCE_EXTENSIONS + (JS_SOURCE_EXTENSIONS if _uses_js(platforms) else ())
    names = SOURCE_NAMES + (JS_SOURCE_NAMES if _uses_js(platforms) else ())
    return ["*" + ext for ext in extensions] + list(names) + ["*/" + name for name in names]

DEFAULTS = {
    "platforms": [],          # empty means auto-detect
    "baseBranch": "",         # empty means origin/HEAD, then main, master, develop
    "protectedBranches": ["main", "master", "develop", "release/*", "production"],
    "verifyGate": "notice",   # notice | require | off
    "prompts": "few",         # few | strict
    "lintOnEdit": True,
    "verify": {},             # {"ios": {"quick": "...", "test": "...", "full": "..."}}
    "generated": [],
    "sensitive": [],
    "codemap": "docs/agent/CODEMAP.md",
    "prLines": 400,
}


# What still needs a person's yes with `"prompts": "few"`: an action that
# leaves the machine for good, changes signing, would throw work away, or
# skips the repository's own checks. Everything else in guards.py asks only
# with `"prompts": "strict"`.
FEW_PROMPTS = frozenset({"publish", "signing", "lost-work", "skip-checks", "admin", "own-config", "unparsed"})


class Config(object):
    def __init__(self, root, data):
        self.root = root
        self.data = data

    def __getitem__(self, key):
        return self.data[key]

    def get(self, key, default=None):
        return self.data.get(key, default)

    @property
    def keel_adopted(self):
        """True when the project is governed by Keel: its gates take over."""
        return os.path.isfile(os.path.join(self.root, ".keel", "config.json"))

    def asks(self, category):
        """Does this kind of action need a person's yes under the configured `prompts`?"""
        return self.data["prompts"] == "strict" or category in FEW_PROMPTS

    def generated_rules(self):
        return GENERATED + [(p, "Listed as generated in %s." % CONFIG_NAME) for p in self.data["generated"]]

    def sensitive_rules(self):
        return SENSITIVE + [(p, "Listed as sensitive in %s." % CONFIG_NAME) for p in self.data["sensitive"]]


def load(root):
    data = dict(DEFAULTS)
    data["verify"] = {}
    raw = util.read_json(os.path.join(root, CONFIG_NAME), default=None)
    problems = []
    if raw is None:
        if os.path.exists(os.path.join(root, CONFIG_NAME)):
            problems.append("%s is not valid JSON; using defaults." % CONFIG_NAME)
        raw = {}
    if not isinstance(raw, dict):
        problems.append("%s must hold a JSON object; using defaults." % CONFIG_NAME)
        raw = {}
    for key, value in raw.items():
        if key.startswith("$") or key.startswith("_"):
            continue
        if key not in DEFAULTS:
            problems.append("unknown key %r in %s" % (key, CONFIG_NAME))
            continue
        expected = type(DEFAULTS[key])
        if not isinstance(value, expected) or (expected is int and isinstance(value, bool)):
            problems.append("%r in %s should be a %s" % (key, CONFIG_NAME, expected.__name__))
            continue
        data[key] = value
    if data["verifyGate"] not in ("notice", "require", "off"):
        problems.append("verifyGate must be notice, require or off; using notice.")
        data["verifyGate"] = "notice"
    if data["prompts"] not in ("few", "strict"):
        problems.append("prompts must be few or strict; using few.")
        data["prompts"] = "few"
    config = Config(root, data)
    config.problems = problems
    return config


def is_source(rel_path, platforms=()):
    name = rel_path.rsplit("/", 1)[-1]
    if name.endswith(SOURCE_EXTENSIONS) or name in SOURCE_NAMES:
        return True
    return _uses_js(platforms) and (name.endswith(JS_SOURCE_EXTENSIONS) or name in JS_SOURCE_NAMES)
