"""`mobile doctor`: is this machine and project set up so the agent can be
trusted to work quickly? Read-only. Prints one line per check.

It looks at four things: the toolchain for the detected platforms, the
project overlay (instruction files, permission rules), permission rules that
quietly defeat every guardrail, and always-on context that is paid for in
every session.
"""

import os
import re

from . import config as config_module
from . import detect, util

OK, WARN, FAIL, INFO = "ok", "warn", "FAIL", "info"

# Allow rules that hand the agent a general-purpose escape hatch.
_BROAD_ALLOW = [
    (re.compile(r"^Bash(\(\*\))?$"), "allows every shell command"),
    (re.compile(r"^Bash\((?:python3?|node|ruby|perl|sh|bash|zsh|osascript)(?:[ :]|\))"), "allows an interpreter, which can run anything"),
    (re.compile(r"^Bash\((?:curl|wget|nc|ncat|scp|ssh|sshpass|rsync|ftp)(?:[ :]|\))"), "allows sending data to any host"),
    (re.compile(r"^Bash\((?:rtk )?git(?: \*|:\*)\)$"), "allows every git command, including force push and hard reset"),
    (re.compile(r"^Bash\((?:rm|sudo|chmod|chown)(?:[ :]|\))"), "allows destructive or privileged commands"),
    (re.compile(r"^Bash\((?:npx|bunx|uvx|pnpm dlx|bundle exec|fvm|mise exec|docker)(?: \*|:\*)\)$"), "allows a runner that executes whatever follows it"),
    (re.compile(r"^(?:Read|Edit)\((?://|~/)?\*\*\)$"), "allows file access everywhere"),
]


def _version_tuple(text):
    match = re.search(r"(\d+)\.(\d+)\.(\d+)", text or "")
    return tuple(int(p) for p in match.groups()) if match else None


def _tool(report, name, required, purpose, version_args=("--version",)):
    path = util.which(name)
    if not path:
        report(FAIL if required else INFO, "%s not found%s" % (name, " (needed for %s)" % purpose if required else " (optional: %s)" % purpose))
        return False
    code, out = util.run([name] + list(version_args), timeout=20)
    first = (out.strip().splitlines() or [""])[0][:70]
    if name == "java" and code != 0:
        report(FAIL if required else INFO, "java is a stub with no runtime installed (%s)" % purpose)
        return False
    report(OK, "%s: %s" % (name, first or path))
    return True


def _frontmatter_description(path):
    text = util.read_text(path, limit=20000)
    match = re.match(r"^---\n(.*?)\n---", text, re.S)
    if not match:
        return ""
    desc = re.search(r"(?ms)^description:\s*(.*?)(?=^\w[\w-]*:|\Z)", match.group(1))
    return desc.group(1).strip() if desc else ""


def _settings_rules(path):
    data = util.read_json(path, default=None)
    if not isinstance(data, dict):
        return None
    permissions = data.get("permissions") or {}
    return {
        "allow": [r for r in permissions.get("allow", []) if isinstance(r, str)],
        "deny": [r for r in permissions.get("deny", []) if isinstance(r, str)],
        "ask": [r for r in permissions.get("ask", []) if isinstance(r, str)],
        "defaultMode": permissions.get("defaultMode"),
        "sandbox": (data.get("sandbox") or {}).get("enabled"),
        "skipDangerous": data.get("skipDangerousModePermissionPrompt"),
        "plugins": data.get("enabledPlugins") or {},
    }


def _check_settings(report, label, path):
    rules = _settings_rules(path)
    if rules is None:
        return None
    broad = []
    for rule in rules["allow"]:
        if "*" not in rule and rule not in ("Bash", "Read", "Edit"):
            continue                    # an exact command is not a broad grant
        for pattern, why in _BROAD_ALLOW:
            if pattern.search(rule):
                broad.append("%s (%s)" % (rule[:60], why))
                break
    if broad:
        report(WARN, "%s has %d allow rules that bypass guardrails: %s" % (label, len(broad), "; ".join(broad[:4]) + (" ..." if len(broad) > 4 else "")))
    if rules["allow"] and not rules["deny"]:
        report(WARN, "%s has %d allow rules and no deny rules" % (label, len(rules["allow"])))
    if rules["defaultMode"] == "bypassPermissions":
        report(WARN, "%s starts sessions in bypassPermissions mode: no prompt, no classifier" % label)
    if rules["skipDangerous"]:
        report(INFO, "%s suppresses the bypass-permissions warning prompt" % label)
    if not broad and (rules["deny"] or not rules["allow"]):
        report(OK, "%s: %d allow, %d ask, %d deny rules" % (label, len(rules["allow"]), len(rules["ask"]), len(rules["deny"])))
    return rules


def main(root, out=print):
    counts = {OK: 0, WARN: 0, FAIL: 0, INFO: 0}

    def report(level, message):
        counts[level] += 1
        out("[%s] %s" % (level, message))

    out("mobile doctor · %s" % root)
    facts = detect.detect(root)
    config = config_module.load(root)
    platforms = config["platforms"] or facts["platforms"]

    out("\nProject")
    if platforms:
        report(OK, "platforms: " + ", ".join(platforms))
        for line in detect.profile_lines(facts):
            out("     " + line)
    else:
        report(INFO, "no mobile project detected here; the plugin's hooks stay silent")
    for problem in getattr(config, "problems", []):
        report(WARN, problem)
    if config.keel_adopted:
        report(INFO, "Keel governs this project: the mobile-coding-agents stop notice and lint-on-edit stand down")
    elif platforms:
        report(OK, "guards: prompts %s (few: only before something hard to undo), end of turn %s" % (config["prompts"], config["verifyGate"]))

    instruction_files = [name for name in ("AGENTS.md", "CLAUDE.md", ".claude/CLAUDE.md") if os.path.isfile(os.path.join(root, name))]
    if platforms and not instruction_files:
        report(INFO, "no AGENTS.md or CLAUDE.md. The plugins work without one; `mobile adopt` writes a short starter")
    for name in instruction_files:
        lines = util.read_text(os.path.join(root, name)).count("\n")
        report(WARN if lines > 150 else OK, "%s: %d lines%s" % (name, lines, " (over 150: every line is paid for in every request)" if lines > 150 else ""))
    for platform in platforms:
        rule = os.path.join(root, ".claude", "rules", "mobile-%s.md" % platform)
        if not os.path.isfile(rule):
            report(INFO, "no path-scoped rule for %s (.claude/rules/mobile-%s.md)" % (platform, platform))
    codemap = os.path.join(root, config["codemap"])
    if platforms:
        report(OK if os.path.isfile(codemap) else INFO, "code map %s: %s" % (config["codemap"], "present" if os.path.isfile(codemap) else "not written yet (run /mobile-core:recon)"))

    out("\nToolchain")
    _tool(report, "git", True, "everything")
    code, version_text = util.run(["claude", "--version"], timeout=20)
    version = _version_tuple(version_text)
    if version is None:
        report(INFO, "claude CLI not found on PATH (fine inside a session; needed for `claude plugin eval`)")
    else:
        need = [((2, 1, 269), "plugin evals"), ((2, 1, 277), "reading AGENTS.md natively"), ((2, 1, 295), "onFailure on hooks")]
        missing = [what for minimum, what in need if version < minimum]
        report(WARN if missing else OK, "claude %s%s" % (".".join(map(str, version)), " (too old for: %s)" % ", ".join(missing) if missing else ""))
    if "ios" in platforms:
        _tool(report, "xcodebuild", True, "building iOS", ("-version",))
        _tool(report, "swiftlint", False, "lint feedback on edited Swift lines", ("version",))
        _tool(report, "xcbeautify", False, "readable xcodebuild output in your own terminal")
    if "android" in platforms:
        _tool(report, "java", True, "Gradle", ("-version",))
        sdk = os.environ.get("ANDROID_HOME") or os.environ.get("ANDROID_SDK_ROOT") or os.path.expanduser("~/Library/Android/sdk")
        report(OK if os.path.isdir(sdk) else FAIL, "Android SDK: %s" % (sdk if os.path.isdir(sdk) else "not found (set ANDROID_HOME)"))
        _tool(report, "adb", False, "device logs and installs")
        _tool(report, "ktlint", False, "lint feedback on edited Kotlin lines")
    if "kotlin-multiplatform" in platforms:
        if "android" not in platforms:
            _tool(report, "java", True, "Gradle", ("-version",))
        if any(t.startswith(("ios", "macos", "watchos", "tvos")) for t in (facts.get("kotlin-multiplatform") or {}).get("targets", [])):
            _tool(report, "xcodebuild", True, "compiling the Apple targets of the shared code", ("-version",))
    if "react-native" in platforms:
        rn = facts.get("react-native") or {}
        _tool(report, "node", True, "everything in a React Native project", ("--version",))
        manager = rn.get("packageManager") or "npm"
        _tool(report, manager, True, "installing dependencies and running scripts", ("--version",))
        if os.path.isfile(os.path.join(root, rn.get("root") or ".", "ios", "Podfile")):
            _tool(report, "pod", True, "installing the iOS dependencies", ("--version",))
        _tool(report, "watchman", False, "fast file watching for Metro", ("--version",))
    if "flutter" in platforms:
        _tool(report, "flutter", True, "building Flutter")
        _tool(report, "dart", True, "analysis and tests")
        if (facts.get("flutter") or {}).get("pinnedFlutter"):
            _tool(report, "fvm", True, "the Flutter version this project pins")
    _tool(report, "gitleaks", False, "secret scanning before commit and in CI", ("version",))

    out("\nPermissions")
    project_rules = _check_settings(report, ".claude/settings.json", os.path.join(root, ".claude", "settings.json"))
    _check_settings(report, ".claude/settings.local.json", os.path.join(root, ".claude", "settings.local.json"))
    home = os.path.expanduser("~")
    user_rules = _check_settings(report, "~/.claude/settings.json", os.path.join(home, ".claude", "settings.json"))
    home_local = os.path.join(home, ".claude", "settings.local.json")
    if os.path.isfile(home_local):
        _check_settings(report, "~/.claude/settings.local.json (applies to sessions started in your home directory)", home_local)
    if platforms and project_rules is None:
        report(WARN, "no .claude/settings.json: secrets and signing files are not read-protected for this project")
    sandboxed = any(r and r["sandbox"] for r in (project_rules, user_rules))
    report(OK if sandboxed else INFO, "OS sandbox for shell commands: %s" % ("enabled" if sandboxed else "off (permission rules and hooks are not a boundary; see docs/03-setup-and-validation.md)"))

    out("\nAlways-on context")
    agents_dir = os.path.join(home, ".claude", "agents")
    if os.path.isdir(agents_dir):
        chars = sum(len(_frontmatter_description(os.path.join(agents_dir, n))) for n in os.listdir(agents_dir) if n.endswith(".md"))
        number = len([n for n in os.listdir(agents_dir) if n.endswith(".md")])
        if number:
            tokens = chars // 4
            report(WARN if tokens > 1500 else INFO, "%d user-level agents load their descriptions into every session of every project (~%d tokens)" % (number, tokens))
    enabled = sorted(k for k, v in ((user_rules or {}).get("plugins") or {}).items() if v)
    if enabled:
        report(INFO, "%d plugins enabled for every project: %s. `claude plugin details <name>` shows what each costs per session" % (len(enabled), ", ".join(enabled)))

    out("\n%d ok · %d warnings · %d failures" % (counts[OK], counts[WARN], counts[FAIL]))
    return 1 if counts[FAIL] else 0
