"""`mobile verify`: run the project's checks and print only what matters.

A mobile build log is thousands of lines; an agent needs the ten that say
what failed. Each step's full output goes to a log file, and the terminal
gets the diagnostics with file and line. On success the current source
fingerprint is recorded, which is what the stop hook compares against.
"""

import hashlib
import json
import os
import re
import shlex
import subprocess
import time

from . import config as config_module
from . import detect, util

LEVELS = ("quick", "test", "full")
TIMEOUTS = {"quick": 900, "test": 2400, "full": 3600}


# --------------------------------------------------------------------------
# Source fingerprint
# --------------------------------------------------------------------------

def source_fingerprint(root, platforms=()):
    """A hash of every source file's content as it is on disk right now.

    It does not change when work is staged or committed, or when a non-source
    file changes; it does change when a source file is edited by any route
    (the Edit tool, sed, a code generator). Nothing is written to the
    repository to compute it. `platforms` are the detected ones: they decide
    which file types count as source.
    """
    pathspecs = config_module.source_pathspecs(platforms)
    if util.git_dir(root):
        code, listing = util.run(["git", "-C", root, "ls-files", "-s", "-z", "--"] + pathspecs, timeout=60)
        code2, dirty = util.run(
            ["git", "-C", root, "ls-files", "-m", "-o", "-d", "-z", "--exclude-standard", "--"] + pathspecs, timeout=60)
        if code == 0 and code2 == 0:
            blobs = {}
            for record in listing.split("\0"):
                meta, _, path = record.partition("\t")
                parts = meta.split()
                if path and len(parts) >= 2:
                    blobs[path] = parts[1]
            touched = sorted(set(p for p in dirty.split("\0") if p))
            present = [p for p in touched if os.path.isfile(os.path.join(root, p)) and "\n" not in p]
            for path in touched:
                if path not in present:
                    blobs.pop(path, None)
            if present:
                try:
                    proc = subprocess.run(
                        ["git", "-C", root, "hash-object", "--stdin-paths"], input="\n".join(present).encode("utf-8"),
                        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=120)
                    hashes = proc.stdout.decode("utf-8", errors="replace").split()
                except (OSError, subprocess.TimeoutExpired):
                    hashes = []
                if len(hashes) == len(present):
                    blobs.update(zip(present, hashes))
                else:
                    for path in present:
                        try:
                            stat = os.stat(os.path.join(root, path))
                            blobs[path] = "stat:%d:%d" % (stat.st_size, stat.st_mtime_ns)
                        except OSError:
                            blobs.pop(path, None)
            return "git:" + util.sha1("\n".join("%s %s" % item for item in sorted(blobs.items())))
    digest = hashlib.sha1()
    for rel, is_dir in util.walk(root, max_depth=util.SOURCE_DEPTH):
        if is_dir or not config_module.is_source(rel.replace(os.sep, "/"), platforms):
            continue
        try:
            stat = os.stat(os.path.join(root, rel))
        except OSError:
            continue
        digest.update(("%s\0%d\0%d\n" % (rel, stat.st_size, stat.st_mtime_ns)).encode("utf-8"))
    return "walk:" + digest.hexdigest()


def read_stamp(root):
    return util.read_json(os.path.join(util.state_dir(root), "verified.json"), default={}) or {}


def write_stamp(root, level, platforms, detected=None):
    """Record that the current source state passed. `detected` is every platform
    in the repository (it sets which files count); `platforms` is what was run."""
    util.write_json(os.path.join(util.state_dir(root), "verified.json"), {
        "fingerprint": source_fingerprint(root, detected if detected is not None else platforms), "level": level,
        "platforms": platforms, "time": int(time.time()),
    })


def changed_files(root):
    """Source files that differ from HEAD or are untracked, relative to root."""
    files = []
    code, out = util.git(root, "diff", "--name-only", "HEAD")
    if code == 0:
        files += out.splitlines()
    code, out = util.git(root, "ls-files", "--others", "--exclude-standard")
    if code == 0:
        files += out.splitlines()
    seen, result = set(), []
    for rel in files:
        rel = rel.strip()
        if rel and rel not in seen and os.path.isfile(os.path.join(root, rel)):
            seen.add(rel)
            result.append(rel)
    return result


# --------------------------------------------------------------------------
# Default steps per platform
# --------------------------------------------------------------------------

class Step(object):
    def __init__(self, ident, command, cwd=None):
        self.ident = ident
        self.command = command          # list (exec) or str (shell)
        self.cwd = cwd

    def display(self):
        if isinstance(self.command, str):
            return self.command
        return " ".join(shlex.quote(part) for part in self.command)


class NeedsConfig(Exception):
    pass


def _pick_scheme(ios):
    schemes = [s for s in ios.get("schemes", []) if not re.search(r"(Tests|UITests)$", s)]
    if len(schemes) == 1:
        return schemes[0]
    names = [os.path.splitext(os.path.basename(p))[0] for p in ios.get("workspaces", []) + ios.get("projects", [])]
    for name in names:
        if name in schemes:
            return name
    return None


def _pick_simulator():
    code, out = util.run(["xcrun", "simctl", "list", "devices", "available", "-j"], timeout=30)
    if code != 0:
        return None
    try:
        devices = json.loads(out).get("devices", {})
    except ValueError:
        return None
    best = None
    for runtime, entries in devices.items():
        match = re.search(r"iOS-(\d+)-(\d+)", runtime)
        if not match:
            continue
        version = (int(match.group(1)), int(match.group(2)))
        for entry in entries:
            if "iPhone" not in entry.get("name", ""):
                continue
            rank = (entry.get("state") == "Booted", version)
            if best is None or rank > best[0]:
                best = (rank, entry.get("udid"))
    return best[1] if best else None


def _derived_data(root):
    return os.path.join(os.path.expanduser("~/Library/Caches/mobile-coding-agents/DerivedData"), util.sha1(root)[:12])


def _ios_steps(root, facts, level, changed):
    ios = facts["ios"]
    steps = []
    if util.which("swiftlint") and ".swiftlint.yml" in ios.get("lint", []):
        if level == "full":
            steps.append(Step("swiftlint", ["swiftlint", "lint", "--quiet"]))
        else:
            swift = [f for f in changed if f.endswith(".swift")]
            if swift:
                steps.append(Step("swiftlint", ["swiftlint", "lint", "--quiet"] + swift[:300]))
    sandboxed = util.in_os_sandbox()
    if ios.get("projects") or ios.get("workspaces"):
        if sandboxed:
            raise NeedsConfig(
                "iOS: xcodebuild cannot run inside the Claude Code sandbox (it cannot reach the simulator service or its own "
                "caches). Add \"mobile verify *\" and \"xcodebuild *\" to sandbox.excludedCommands in your settings, "
                "then run this again.")
        if ios.get("workspaces"):
            container = ["-workspace", ios["workspaces"][0]]
        else:
            container = ["-project", ios["projects"][0]]
        scheme = _pick_scheme(ios)
        if not scheme:
            candidates = [s for s in ios.get("schemes", []) if not re.search(r"(Tests|UITests)$", s)]
            example = "xcodebuild build %s %s -scheme %s -destination 'generic/platform=iOS Simulator' -quiet CODE_SIGNING_ALLOWED=NO" % (
                container[0], shlex.quote(container[1]), shlex.quote(candidates[0] if candidates else "<scheme>"))
            raise NeedsConfig(
                "iOS: %s. Choose one by setting verify.ios.%s in %s, for example: %s"
                % ("several app schemes are shared (%s)" % ", ".join(candidates) if candidates else "no shared scheme found",
                   level, config_module.CONFIG_NAME, example))
        base = ["xcodebuild"] + container + ["-scheme", scheme, "-derivedDataPath", _derived_data(root), "-quiet"]
        if level in ("quick", "full"):
            steps.append(Step("xcodebuild-build", base[:1] + ["build"] + base[1:] + [
                "-destination", "generic/platform=iOS Simulator", "CODE_SIGNING_ALLOWED=NO"]))
        if level in ("test", "full"):
            udid = _pick_simulator()
            if not udid:
                raise NeedsConfig("iOS: no available iPhone simulator found for tests. Install one in Xcode, or set verify.ios.%s in %s." % (level, config_module.CONFIG_NAME))
            steps.append(Step("xcodebuild-test", base[:1] + ["test"] + base[1:] + [
                "-destination", "platform=iOS Simulator,id=%s" % udid, "CODE_SIGNING_ALLOWED=NO"]))
    elif ios.get("packages"):
        package_dir = os.path.dirname(ios["packages"][0]) or None
        # SwiftPM starts its own sandbox, which cannot nest inside another one.
        extra = ["--disable-sandbox"] if sandboxed else []
        if level in ("quick", "full"):
            steps.append(Step("swift-build", ["swift", "build"] + extra, cwd=package_dir))
        if level in ("test", "full"):
            steps.append(Step("swift-test", ["swift", "test"] + extra, cwd=package_dir))
    return steps


def _android_steps(root, facts, level, changed):
    android = facts["android"]
    wrapper = None
    for rel, is_dir in util.walk(root, max_depth=3):
        if not is_dir and os.path.basename(rel) == "gradlew":
            wrapper = rel
            break
    if not wrapper:
        raise NeedsConfig("Android: no gradlew wrapper found. Set verify.android.%s in %s." % (level, config_module.CONFIG_NAME))
    if "flavors" in android.get("flags", []):
        raise NeedsConfig(
            "Android: product flavors are defined, so task names carry a flavor. Set verify.android.%s in %s, "
            "for example \"./gradlew --console=plain :app:compileStagingDebugSources\"." % (level, config_module.CONFIG_NAME))
    cwd = os.path.dirname(wrapper) or None
    base = ["./gradlew", "--console=plain", "-q"]
    tasks = {"quick": ["compileDebugSources"], "test": ["testDebugUnitTest"], "full": ["lintDebug", "testDebugUnitTest"]}[level]
    return [Step("gradle-" + level, base + tasks, cwd=cwd)]


def _gradle_wrapper(root):
    for rel, is_dir in util.walk(root, max_depth=3):
        if not is_dir and os.path.basename(rel) == "gradlew":
            return rel
    return None


def _kotlin_multiplatform_steps(root, facts, level, changed):
    """Shared code: compile it for one Apple target (the Android plan covers the Android side), then run every target's tests.

    Compiling one target is the cheap check. `build` and `assemble` link every framework and are far slower.
    """
    targets = facts["kotlin-multiplatform"].get("targets", [])
    wrapper = _gradle_wrapper(root)
    if not wrapper:
        raise NeedsConfig("Kotlin Multiplatform: no gradlew wrapper found. Set verify.kotlin-multiplatform.%s in %s." % (level, config_module.CONFIG_NAME))
    compile_task = next((task for target, task in (
        ("iosSimulatorArm64", "compileKotlinIosSimulatorArm64"), ("iosArm64", "compileKotlinIosArm64"), ("iosX64", "compileKotlinIosX64"),
    ) if target in targets), "compileKotlinMetadata")
    tasks = {"quick": [compile_task], "test": ["allTests"], "full": [compile_task, "allTests"]}[level]
    return [Step("gradle-shared-" + level, ["./gradlew", "--console=plain", "-q"] + tasks, cwd=os.path.dirname(wrapper) or None)]


def _flutter_steps(root, facts, level, changed):
    flutter = facts["flutter"]
    tool = ["fvm", "flutter"] if flutter.get("pinnedFlutter") and util.which("fvm") else ["flutter"]
    cwd = None if flutter.get("root") in (None, ".", "") else flutter["root"]
    steps = []
    if level in ("quick", "full"):
        steps.append(Step("flutter-analyze", tool + ["analyze", "--no-pub"], cwd=cwd))
    if level in ("test", "full"):
        steps.append(Step("flutter-test", tool + ["test", "--no-pub", "--reporter", "expanded"], cwd=cwd))
    return steps


_JS_FILE = re.compile(r"\.(?:ts|tsx|js|jsx)$")


def _react_native_steps(root, facts, level, changed):
    rn = facts["react-native"]
    base = "" if rn.get("root") in (None, ".", "") else rn["root"]
    cwd = base or None
    manager = rn.get("packageManager") or "npm"
    run = {"yarn": ["yarn", "run"], "pnpm": ["pnpm", "run"], "bun": ["bun", "run"]}.get(manager, ["npm", "run", "--silent"])
    # Run the project's own binary; never let a runner download one with the same name.
    local = {"yarn": ["yarn"], "pnpm": ["pnpm", "exec"], "bun": ["bunx", "--no-install"]}.get(manager, ["npx", "--no-install"])
    scripts = rn.get("scripts", [])
    steps = []
    if level in ("quick", "full"):
        typecheck = next((name for name in ("typecheck", "type-check", "tsc") if name in scripts), None)
        if typecheck:
            steps.append(Step("typecheck", run + [typecheck], cwd=cwd))
        elif rn.get("typescript"):
            steps.append(Step("typecheck", local + ["tsc", "--noEmit", "--pretty", "false"], cwd=cwd))
        if level == "full" and "lint" in scripts:
            steps.append(Step("lint", run + ["lint"], cwd=cwd))
        elif rn.get("eslint"):
            prefix = base + "/" if base else ""
            files = [f[len(prefix):] for f in changed if _JS_FILE.search(f) and f.startswith(prefix) and "node_modules/" not in f]
            if level == "full":
                steps.append(Step("eslint", local + ["eslint", "."], cwd=cwd))
            elif files:
                steps.append(Step("eslint", local + ["eslint"] + files[:300], cwd=cwd))
    if level in ("test", "full"):
        if any(name in rn.get("testing", []) for name in ("jest", "jest-expo")):
            steps.append(Step("jest", local + ["jest", "--ci"], cwd=cwd))
        elif "test" in scripts:
            steps.append(Step("test", run + ["test"], cwd=cwd))
    if not steps:
        raise NeedsConfig(
            "React Native: no type check, lint or test setup found for the %s level. Set verify.react-native.%s in %s, "
            "for example \"npx tsc --noEmit\"." % (level, level, config_module.CONFIG_NAME))
    return steps


_DEFAULTS = {
    "ios": _ios_steps, "android": _android_steps, "flutter": _flutter_steps,
    "react-native": _react_native_steps, "kotlin-multiplatform": _kotlin_multiplatform_steps,
}


def plan(root, config, facts, level, platforms=None):
    """Return (steps, problems). Configured commands win over defaults."""
    steps, problems = [], []
    chosen = platforms or config["platforms"] or facts["platforms"]
    changed = changed_files(root)
    for platform in chosen:
        configured = (config["verify"].get(platform) or {}).get(level)
        if configured:
            commands = [configured] if isinstance(configured, str) else list(configured)
            for index, command in enumerate(commands):
                steps.append(Step("%s-%s-%d" % (platform, level, index + 1), command))
            continue
        if platform not in facts or platform not in _DEFAULTS:
            problems.append("%s: not detected in this repository." % platform)
            continue
        try:
            steps += _DEFAULTS[platform](root, facts, level, changed)
        except NeedsConfig as exc:
            problems.append(str(exc))
    return steps, problems


# --------------------------------------------------------------------------
# Running and compacting
# --------------------------------------------------------------------------

_DIAGNOSTICS = [
    re.compile(r"^(?P<loc>(?:/|[A-Za-z0-9_.~@+-]).*?:\d+(?::\d+)?): (?P<kind>fatal error|error): (?P<msg>.+)$"),
    re.compile(r"^e: (?:file://)?(?P<loc>.+?:\d+:\d+):? (?P<msg>.+)$"),
    re.compile(r"^\s*(?P<kind>error) [•-] (?P<msg>.+?) [•-] (?P<loc>\S+:\d+:\d+) [•-] (?P<code>\S+)\s*$"),
    re.compile(r"^\s*(?P<kind>error) - (?P<loc>\S+:\d+:\d+) - (?P<msg>.+?) - (?P<code>\S+)\s*$"),
    re.compile(r"^(?P<msg>.+ > .+ FAILED)\s*$"),
    re.compile(r"^(?P<msg>> Task \S+ FAILED)\s*$"),
    re.compile(r"^(?P<msg>\d+:\d+ \+\d+(?: ~\d+)? -\d+: .*\[E\].*)$"),
    re.compile(r"^(?P<msg>✘ .+)$"),
    re.compile(r"^(?P<msg>(?:ld|clang|xcodebuild): error: .+)$"),
    re.compile(r"^(?P<msg>error: .+)$"),
    re.compile(r"^(?P<msg>Undefined symbols? for architecture .+)$"),
    re.compile(r"^(?P<msg>\*\* (?:BUILD|TEST|ARCHIVE) FAILED \*\*)$"),
    re.compile(r"^(?P<msg>FAILURE: .+|BUILD FAILED.*)$"),
    re.compile(r"^(?P<loc>[^\s(]+\(\d+,\d+\)): (?P<kind>error) (?P<code>TS\d+): (?P<msg>.+)$"),      # tsc
    re.compile(r"^\s*● (?!Console\b)(?P<msg>.+ › .+)$"),                                              # a failed Jest test
    re.compile(r"^(?P<msg>FAIL\s+\S+\.(?:ts|tsx|js|jsx).*)$"),                                         # a failed Jest file
]
_ESLINT_FILE = re.compile(r"^(?P<file>/.*\.(?:ts|tsx|js|jsx|mjs|cjs))$")      # ESLint prints the absolute path
_ESLINT_FINDING = re.compile(r"^\s+(?P<line>\d+):(?P<col>\d+)\s+error\s+(?P<msg>.+?)\s{2,}(?P<rule>\S+)\s*$")
_WARNING = re.compile(r"^(?P<loc>(?:/|[A-Za-z0-9_.~@+-]).*?:\d+(?::\d+)?): warning: (?P<msg>.+)$")


def _relativize(text, root):
    return text.replace(root.rstrip("/") + "/", "")


def extract_diagnostics(output, root, limit=25, include_warnings=False):
    """Pull the lines that explain a failure out of a build or test log."""
    found, seen = [], set()
    lines = output.splitlines()
    eslint_file = None
    for index, line in enumerate(lines):
        line = line.rstrip()
        entry = None
        # ESLint's default report names the file on one line and lists its findings below it.
        file_match = _ESLINT_FILE.match(line)
        if file_match:
            eslint_file = file_match.group("file")
            continue
        finding = _ESLINT_FINDING.match(line) if eslint_file else None
        if finding:
            entry = "%s:%s:%s: %s (%s)" % (eslint_file, finding.group("line"), finding.group("col"), finding.group("msg"), finding.group("rule"))
        for pattern in ([] if entry else _DIAGNOSTICS):
            match = pattern.match(line)
            if match:
                groups = match.groupdict()
                if groups.get("loc"):
                    entry = "%s: %s" % (groups["loc"], groups["msg"])
                    if groups.get("code"):
                        entry += " (%s)" % groups["code"]
                else:
                    entry = groups["msg"]
                break
        if entry is None and include_warnings:
            match = _WARNING.match(line)
            if match:
                entry = "%s: warning: %s" % (match.group("loc"), match.group("msg"))
        if entry is None and line.startswith("* What went wrong:"):
            block = [l.strip() for l in lines[index + 1: index + 6] if l.strip() and not l.startswith("*")]
            entry = "Gradle: " + " ".join(block)[:400] if block else None
        if entry is None:
            continue
        if "[E]" in entry:
            # A failed Dart test: keep the expectation that follows it.
            detail = []
            for follow in lines[index + 1: index + 9]:
                if not follow.startswith("  ") or not follow.strip():
                    break
                detail.append(follow.strip())
            if detail:
                entry += " | " + " ".join(detail)
        entry = _relativize(entry, root)[:500]
        if entry not in seen:
            seen.add(entry)
            found.append(entry)
    if not found:
        tail = [l.rstrip() for l in lines if l.strip()][-12:]
        found = [_relativize(l, root)[:300] for l in tail]
    return util.truncate(found, limit, "more lines in the log")


def run_step(step, root, log_dir, timeout):
    cwd = os.path.join(root, step.cwd) if step.cwd else root
    log_path = os.path.join(log_dir, "%s.log" % re.sub(r"[^A-Za-z0-9_.-]", "_", step.ident))
    started = time.time()
    try:
        with open(log_path, "wb") as log:
            proc = subprocess.run(
                step.command, cwd=cwd, shell=isinstance(step.command, str),
                stdout=log, stderr=subprocess.STDOUT, timeout=timeout,
                env=dict(os.environ, NSUnbufferedIO="YES"),
            )
        code = proc.returncode
    except FileNotFoundError:
        code = 127
        with open(log_path, "w") as log:
            log.write("command not found: %s\n" % step.display())
    except subprocess.TimeoutExpired:
        code = 124
        with open(log_path, "a") as log:
            log.write("\ntimed out after %d seconds\n" % timeout)
    return code, time.time() - started, log_path


def main(root, level="quick", platforms=None, dry_run=False, out=print):
    """Run verification. Returns 0 (pass), 1 (fail), 2 (cannot verify)."""
    config = config_module.load(root)
    facts = detect.detect(root)
    steps, problems = plan(root, config, facts, level, platforms)
    out("mobile verify · level=%s · platforms=%s" % (level, ",".join(platforms or config["platforms"] or facts["platforms"]) or "none"))
    for problem in problems + list(getattr(config, "problems", [])):
        out("  ! " + problem)
    if dry_run:
        for step in steps:
            out("  would run [%s]: %s%s" % (step.ident, step.display(), "  (in %s)" % step.cwd if step.cwd else ""))
        return 2 if (problems and not steps) else 0
    if not steps:
        out("RESULT: CANNOT VERIFY (no runnable check for this level). Say so instead of claiming the change is verified.")
        return 2
    log_dir = os.path.join(util.state_dir(root), "logs")
    os.makedirs(log_dir, exist_ok=True)
    failed = 0
    for step in steps:
        code, seconds, log_path = run_step(step, root, log_dir, TIMEOUTS[level])
        if code == 0:
            out("[ok]   %s (%.0fs)" % (step.ident, seconds))
            continue
        failed += 1
        label = {127: "tool not installed", 124: "timed out"}.get(code, "exit %d" % code)
        out("[FAIL] %s (%s, %.0fs): %s" % (step.ident, label, seconds, step.display()[:200]))
        output = util.read_text(log_path, limit=20_000_000)
        for line in extract_diagnostics(output, root, include_warnings=step.ident.startswith("swiftlint")):
            out("    " + line)
        out("    full log: %s" % log_path)
    if failed:
        out("RESULT: FAIL (%d of %d checks failed)" % (failed, len(steps)))
        return 1
    if problems:
        out("RESULT: INCOMPLETE (%d checks passed, %d could not be planned). Not recorded as verified." % (len(steps), len(problems)))
        return 2
    write_stamp(root, level, platforms or config["platforms"] or facts["platforms"], detected=facts["platforms"])
    out("RESULT: PASS (%d checks) · recorded for the current source state" % len(steps))
    return 0
