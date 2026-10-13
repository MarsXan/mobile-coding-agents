"""Decisions for the two PreToolUse guards.

`check_bash` looks at a shell command, `check_edit` at a file write. Each
returns a Verdict: `deny` (do not do this), `ask` (a human must say yes),
or nothing, optionally with a note for the agent.

A deny costs nobody any time: the agent reads the reason and takes the right
route. An ask stops a person, so each one names a category and the project's
`prompts` setting decides whether that category asks at all (config.asks).
By default only the rare, hard-to-undo ones do.

It is a tripwire for honest mistakes, not a security boundary: the OS sandbox
and CI are the boundaries.
"""

import os
import re

from . import config as config_module
from . import shellscan, util

DENY, ASK = "deny", "ask"
_ORDER = {None: 0, ASK: 1, DENY: 2}


class Verdict(object):
    def __init__(self, asks=None):
        self.decision = None
        self.reasons = []
        self.context = []          # (id, text): told to the agent, never to a person
        self._asks = asks or (lambda category: True)

    def add(self, decision, reason, category=None):
        """Record a decision. An ask whose category is switched off is dropped: returns False."""
        if decision == ASK and not self._asks(category):
            return False
        if _ORDER[decision] > _ORDER[self.decision]:
            self.decision = decision
            self.reasons = [reason]
        elif decision == self.decision and reason not in self.reasons:
            self.reasons.append(reason)
        return True

    def note(self, text, ident=None):
        """`ident` makes the note once-per-session; without one it is given every time."""
        if (ident, text) not in self.context:
            self.context.append((ident, text))

    @property
    def reason(self):
        return " ".join(self.reasons[:3])


# --------------------------------------------------------------------------
# Bash
# --------------------------------------------------------------------------

_SIGNING_FILE = re.compile(r"\.(jks|keystore|p12|p8|mobileprovision|provisionprofile|cer)$", re.I)
_SIGNING_DIRS = ("Library/MobileDevice/Provisioning Profiles", "Library/Keychains", "Library/Developer/Xcode/UserData/Provisioning Profiles")
_BROAD_RM_TARGETS = frozenset({"/", "/*", "~", "~/", "~/*", "$HOME", "${HOME}", "$HOME/", "$HOME/*", ".", "./", "./*", "..", "../", "*", ".git", "./.git"})

_RELEASE_WORDS = re.compile(
    r"(release|deploy|publish|upload|beta|testflight|appstore|app_store|playstore|play_store|"
    r"pilot|deliver|supply|submit|distribute|promote|firebase|production|prod)", re.I)
_GRADLE_PUBLISH = re.compile(
    r"^(publish\w*|upload\w*|promote\w*|appDistributionUpload\w*|bintrayUpload|closeAndRelease\w*|sonatype\w*)$", re.I)
_GIT_VALUE_FLAGS = frozenset({"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path", "--super-prefix", "--config-env"})


def _git_subcommand(args):
    i = 0
    while i < len(args):
        arg = args[i]
        if arg in _GIT_VALUE_FLAGS:
            i += 2
            continue
        if arg.startswith("-"):
            i += 1
            continue
        return arg, args[i + 1:]
    return None, []


def _has_flag(args, short=None, long_names=()):
    for arg in args:
        if arg == "--":
            break
        if arg in long_names or any(arg.startswith(name + "=") for name in long_names):
            return True
        if short and re.match(r"^-[A-Za-z]+$", arg) and short in arg[1:]:
            return True
    return False


def _positional(args):
    return [a for a in args if not a.startswith("-")]


def _is_protected_branch(name, patterns):
    name = name.split(":")[-1].lstrip("+")
    name = re.sub(r"^refs/heads/", "", name)
    return bool(name) and util.any_glob(name, patterns) is not None


def _current_branch(root):
    code, out = util.git(root, "rev-parse", "--abbrev-ref", "HEAD", timeout=10)
    return out.strip() if code == 0 else ""


def _would_lose(root, args, what):
    """Is there anything for this git command to destroy? When that cannot be
    told (another repository is named, or git fails), assume there is."""
    if any(a in _GIT_VALUE_FLAGS and a != "-c" for a in args):
        return True
    if what == "stash":
        code, out = util.git(root, "stash", "list", timeout=10)
        return code != 0 or bool(out.strip())
    untracked = what == "untracked"
    code, out = util.git(root, "status", "--porcelain", "--untracked-files=%s" % ("normal" if untracked else "no"), timeout=10)
    if code != 0:
        return True
    lines = [line for line in out.splitlines() if line.strip()]
    return any(line.startswith("??") for line in lines) if untracked else bool(lines)


def _check_git(cmd, verdict, config, root):
    sub, rest = _git_subcommand(cmd.args)
    if not sub:
        return
    if sub == "push":
        positional = _positional(rest)
        refs = positional[1:]
        forced = _has_flag(rest, "f", ("--force", "--force-with-lease", "--force-if-includes", "--mirror")) or any(r.startswith("+") for r in refs)
        deleting = _has_flag(rest, "d", ("--delete",)) or any(r.startswith(":") for r in refs)
        if forced or deleting:
            what = "Force push" if forced else "Remote branch deletion"
            every_branch = _has_flag(rest, None, ("--mirror", "--all", "--branches"))
            # A bare `git push --force`, or one that names HEAD, pushes the branch that is checked out.
            targets = [_current_branch(root) if r.lstrip("+") in ("HEAD", "@") else r for r in refs] or [_current_branch(root)]
            protected = [r for r in targets if r and _is_protected_branch(r, config["protectedBranches"])]
            if every_branch:
                verdict.add(DENY, "%s of every branch rewrites shared history, protected branches included. Not done by an agent: ask the repository owner." % what)
            elif protected:
                verdict.add(DENY, "%s on a protected branch (%s) rewrites shared history. Not done by an agent: ask the repository owner." % (what, protected[0].lstrip("+:")))
            else:
                verdict.add(ASK, "%s rewrites or removes remote history." % what, "force-push")
        if _has_flag(rest, None, ("--no-verify",)):
            verdict.add(ASK, "`git push --no-verify` skips the pre-push checks.", "skip-checks")
    elif sub == "reset" and _has_flag(rest, None, ("--hard",)):
        if _would_lose(root, cmd.args, "tracked"):
            verdict.add(ASK, "`git reset --hard` would discard uncommitted changes in this working tree.", "lost-work")
    elif sub == "clean" and _has_flag(rest, "f", ("--force",)) and not _has_flag(rest, "n", ("--dry-run",)):
        if _would_lose(root, cmd.args, "untracked"):
            verdict.add(ASK, "`git clean -f` would delete untracked files that git cannot restore.", "lost-work")
    elif sub in ("checkout", "restore"):
        whole_tree = any(p in (".", ":/", "*", "./") for p in _positional(rest))
        only_staged = sub == "restore" and _has_flag(rest, "S", ("--staged",)) and not _has_flag(rest, "W", ("--worktree",))
        if ((whole_tree and not only_staged) or (sub == "checkout" and _has_flag(rest, "f", ("--force",)))) and _would_lose(root, cmd.args, "tracked"):
            verdict.add(ASK, "`git %s` on the whole tree would discard every uncommitted change." % sub, "lost-work")
    elif sub == "stash" and rest[:1] and rest[0] in ("drop", "clear"):
        if _would_lose(root, cmd.args, "stash"):
            verdict.add(ASK, "`git stash %s` deletes stashed work." % rest[0], "lost-work")
    elif sub == "commit" and _has_flag(rest, "n", ("--no-verify",)):
        verdict.add(ASK, "`git commit --no-verify` skips the commit hooks (lint, secret scan).", "skip-checks")
    elif sub in ("filter-branch", "filter-repo"):
        verdict.add(ASK, "`git %s` rewrites history." % sub, "lost-work")
    elif sub == "config" and any("hooksPath" in a for a in rest):
        verdict.add(ASK, "Changing core.hooksPath disables the repository's git hooks.", "skip-checks")


def _check_rm(cmd, verdict, root):
    args = cmd.args
    recursive = _has_flag(args, "r", ("--recursive",)) or _has_flag(args, "R")
    home = os.path.expanduser("~")
    for target in _positional(args):
        expanded = os.path.expanduser(target.replace("$HOME", "~").replace("${HOME}", "~"))
        if _SIGNING_FILE.search(target):
            verdict.add(DENY, "Deleting signing material (%s). A lost upload key or certificate cannot be recreated by the agent." % os.path.basename(target))
            continue
        if any(marker in expanded for marker in _SIGNING_DIRS):
            verdict.add(DENY, "Deleting keychains or provisioning profiles breaks code signing for every project on this machine.")
            continue
        if not recursive:
            continue
        absolute = os.path.normpath(expanded if os.path.isabs(expanded) else os.path.join(root, expanded))
        if target in _BROAD_RM_TARGETS or absolute in (os.path.normpath(root), home, "/") or absolute.endswith(os.sep + ".git"):
            verdict.add(DENY, "`rm -r %s` would delete the repository, its history, or your home directory. Name the specific build directory instead." % target)


def _check_fastlane(cmd, verdict):
    args = cmd.args
    words = [a for a in args if not a.startswith("-") and ":" not in a]
    if not words:
        return
    if words[0] == "match":
        if "nuke" in words:
            verdict.add(DENY, "`fastlane match nuke` revokes the team's certificates and profiles.")
        elif not any(re.match(r"^(--readonly|readonly:true)$", a) for a in args):
            verdict.add(ASK, "`fastlane match` can create or revoke signing assets; use `--readonly` to only fetch.", "signing")
        return
    if any(_RELEASE_WORDS.search(w) for w in words):
        verdict.add(ASK, "`fastlane %s` looks like a release lane: it can upload a build to TestFlight, the App Store or Google Play." % " ".join(words[:2]), "publish")


def _check_gradle(cmd, verdict):
    for task in _positional(cmd.args):
        leaf = task.rsplit(":", 1)[-1]
        if leaf.lower() == "publishtomavenlocal":
            continue
        if _GRADLE_PUBLISH.match(leaf):
            verdict.add(ASK, "Gradle task `%s` publishes or uploads outside this machine." % task, "publish")


def _check_adb(cmd, verdict):
    args, i = cmd.args, 0
    while i < len(args) and args[i].startswith("-"):
        i += 2 if args[i] in ("-s", "-H", "-P", "-t", "-L") else 1
    rest = args[i:]
    if not rest:
        return
    joined = " ".join(rest)
    if rest[0] == "uninstall" or re.search(r"\bpm\s+(clear|uninstall)\b", joined):
        verdict.add(ASK, "`adb %s` deletes an app and its data from the connected device." % " ".join(rest[:3]), "device-data")
    elif rest[0] == "shell" and re.search(r"\b(rm\s+-[a-z]*r|wipe|factory)", joined):
        verdict.add(ASK, "`adb shell` command deletes data on the connected device.", "device-data")
    elif rest[0] == "reboot" and len(rest) > 1:
        verdict.add(ASK, "`adb reboot %s` takes the device out of normal operation." % rest[1], "device-data")


def _check_install(cmd, verdict):
    prog, args = cmd.prog, cmd.args
    positional = _positional(args)
    first = positional[0] if positional else ""
    reason = None
    if prog == "brew" and first in ("install", "tap", "reinstall", "upgrade"):
        reason = "`brew %s`" % first
    elif prog == "gem" and first == "install":
        reason = "`gem install`"
    elif prog in ("pip", "pip3", "pipx", "uv") and ("install" in positional[:2]):
        reason = "`%s install`" % prog
    elif prog in ("npm", "pnpm", "yarn", "bun") and first in ("install", "i", "add") and _has_flag(args, "g", ("--global",)):
        reason = "a global `%s` install" % prog
    elif prog in ("npx", "bunx", "pnpx", "uvx") or (prog in ("pnpm", "yarn") and first == "dlx"):
        reason = "`%s` (downloads and runs a package)" % prog
    elif prog in ("dart", "flutter") and positional[:3] == ["pub", "global", "activate"]:
        reason = "`%s pub global activate`" % prog
    elif prog == "mint" and first in ("install", "run"):
        reason = "`mint %s`" % first
    elif prog == "claude" and positional[:2] in (["plugin", "install"], ["plugins", "install"], ["mcp", "add"]):
        reason = "`claude %s`" % " ".join(positional[:2])
    if reason:
        verdict.add(ASK, "%s installs or runs third-party code on this machine. Vet the source and pin a version first." % reason, "install")


def check_bash(command, config, root):
    """Return a Verdict for a shell command line."""
    verdict = Verdict(config.asks)
    commands = shellscan.split(command or "")
    if commands is None:
        # Could not parse: scan the text. Unparseable plus risky words is worth a look.
        if re.search(r"\b(fastlane|altool|notarytool|simctl\s+(erase|delete)|pm\s+clear|--force|reset\s+--hard|rm\s+-[a-zA-Z]*r)", command):
            verdict.add(ASK, "This command could not be parsed and contains a release or destructive keyword.", "unparsed")
        return verdict
    for cmd in commands:
        prog, args = cmd.prog, cmd.args
        positional = _positional(args)
        if cmd.sudo:
            verdict.add(ASK, "`sudo %s` runs with administrator rights." % prog, "admin")
        if cmd.piped_from in ("curl", "wget") and prog in shellscan.SHELLS + ("python", "python3", "ruby", "node", "perl"):
            verdict.add(ASK, "Piping a download into `%s` runs unreviewed code. Download, read, then run." % prog, "admin")
        if prog == "git":
            _check_git(cmd, verdict, config, root)
        elif prog == "rm":
            _check_rm(cmd, verdict, root)
        elif prog == "fastlane":
            _check_fastlane(cmd, verdict)
        elif prog in ("gradlew", "gradle"):
            _check_gradle(cmd, verdict)
        elif prog == "adb":
            _check_adb(cmd, verdict)
        elif prog == "fastboot":
            verdict.add(ASK, "`fastboot` flashes or wipes a device.", "device-data")
        elif prog == "simctl" and positional[:1] and positional[0] in ("erase", "delete"):
            verdict.add(ASK, "`simctl %s` destroys simulator data (installed apps, their databases and keychains)." % positional[0], "device-data")
        elif prog == "altool" and any(a in ("--upload-app", "--upload-package", "--notarize-app") for a in args):
            verdict.add(ASK, "`altool` uploads a build to App Store Connect.", "publish")
        elif prog == "notarytool" and positional[:1] == ["submit"]:
            verdict.add(ASK, "`notarytool submit` sends a build to Apple.", "publish")
        elif prog == "iTMSTransporter":
            verdict.add(ASK, "`iTMSTransporter` uploads to App Store Connect.", "publish")
        elif prog == "xcodebuild":
            if "-allowProvisioningUpdates" in args:
                verdict.add(ASK, "`-allowProvisioningUpdates` lets xcodebuild create profiles and register devices in the developer account.", "signing")
            if "-exportArchive" in args and "-exportOptionsPlist" in args:
                index = args.index("-exportOptionsPlist")
                plist = util.read_text(os.path.join(root, args[index + 1])) if index + 1 < len(args) else ""
                if re.search(r"<key>destination</key>\s*<string>upload</string>", plist):
                    verdict.add(ASK, "This export uploads the archive to App Store Connect (ExportOptions destination is `upload`).", "publish")
        elif prog == "security":
            if positional[:1] and positional[0].startswith("delete-"):
                verdict.add(DENY, "`security %s` removes keychain items used for code signing." % positional[0])
            elif positional[:1] and positional[0] in ("import", "create-keychain", "default-keychain", "set-key-partition-list", "set-keychain-settings"):
                verdict.add(ASK, "`security %s` changes the keychain used for code signing." % positional[0], "signing")
        elif prog == "keytool" and any(a in ("-delete", "-importkeystore", "-storepasswd", "-keypasswd", "-changealias", "-genkeypair", "-genkey", "-importcert") for a in args):
            verdict.add(ASK, "`keytool` is about to change a keystore. Losing or overwriting a release key is not recoverable.", "signing")
        elif prog == "firebase" and positional[:1] and re.match(r"^(deploy|appdistribution:distribute|crashlytics:(symbols|mappingfile):upload|hosting:.*)$", positional[0]):
            verdict.add(ASK, "`firebase %s` publishes outside this machine." % positional[0], "publish")
        elif prog in ("flutter", "dart") and positional[:2] == ["pub", "publish"] and "--dry-run" not in args:
            verdict.add(ASK, "`pub publish` releases a package to pub.dev permanently.", "publish")
        elif prog == "pod" and positional[:2] in (["trunk", "push"], ["repo", "push"]):
            verdict.add(ASK, "`pod %s` publishes a podspec." % " ".join(positional[:2]), "publish")
        elif prog == "shorebird" and positional[:1] and positional[0] in ("release", "patch"):
            verdict.add(ASK, "`shorebird %s` ships code to users' devices." % positional[0], "publish")
        elif prog in ("gh", "glab") and positional[:1] == ["release"] and positional[1:2] and positional[1] in ("create", "delete", "upload", "edit"):
            verdict.add(ASK, "`%s release %s` changes a public release." % (prog, positional[1]), "publish")
        _check_install(cmd, verdict)
    return verdict


# --------------------------------------------------------------------------
# Edit / Write
# --------------------------------------------------------------------------

# High-precision secret shapes. A match is a real credential format, so the
# write is refused. Anything shipped inside an app binary is public.
_SECRETS = [
    ("a private key block", re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP |ENCRYPTED )?PRIVATE KEY-----")),
    ("an AWS access key ID", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("a Google API key", re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b")),
    ("a Stripe live secret key", re.compile(r"\b[sr]k_live_[0-9A-Za-z]{20,}\b")),
    ("a Slack token", re.compile(r"\bxox[abprs]-[0-9A-Za-z-]{10,}\b")),
    ("a GitHub token", re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{40,})\b")),
    ("a GitLab token", re.compile(r"\bglpat-[A-Za-z0-9_\-]{20,}\b")),
    ("an Anthropic or OpenAI API key", re.compile(r"\bsk-(?:ant-|proj-)[A-Za-z0-9_\-]{20,}\b")),
    ("a SendGrid API key", re.compile(r"\bSG\.[A-Za-z0-9_\-]{16,}\.[A-Za-z0-9_\-]{16,}\b")),
    ("a hard-coded Android signing password", re.compile(r"\b(?:storePassword|keyPassword)\s*(?:=|\s)\s*[\"'][^\"'$]{4,}[\"']")),
]
_SECRET_PLACEHOLDER = re.compile(r"(example|sample|dummy|fake|placeholder|your[_-]?|xxxx|0000|test[_-]?key|changeme|redacted)", re.I)
_GENERIC_SECRET = re.compile(r"(?i)\b(api[_-]?key|secret|access[_-]?token|auth[_-]?token|client[_-]?secret|password|passwd)\b\s*[:=]\s*[\"'][A-Za-z0-9+/=_\-]{24,}[\"']")

# Ways to silence a checker or a test instead of fixing the cause.
_SUPPRESSIONS = [
    ("a SwiftLint suppression", re.compile(r"swiftlint:disable")),
    ("a skipped test", re.compile(r"\bXCTSkip\b|\.disabled\(|@Ignore\b|@Disabled\b|\bskip:\s*true\b|@Skip\(")),
    ("a concurrency-safety escape hatch", re.compile(r"@unchecked\s+Sendable|nonisolated\(unsafe\)")),
    ("a Kotlin/Java warning suppression", re.compile(r"@Suppress(?:Lint|Warnings)?\s*\(|//\s*noinspection\b|tools:ignore=")),
    ("a ktlint or detekt suppression", re.compile(r"ktlint-disable|detekt:disable")),
    ("a Dart analyzer suppression", re.compile(r"//\s*ignore(?:_for_file)?:")),
    ("a coverage exclusion", re.compile(r"coverage:ignore|LCOV_EXCL|@ExcludeFromJacocoGeneratedReport")),
    ("a looser screenshot-comparison tolerance", re.compile(r"\b(?:perceptualPrecision|maxPercentDifference|changeThreshold|maxDiffPixelRatio)\b")),
]

_PERSISTED_MODEL = re.compile(
    r"@Entity\b|@Database\s*\(|@Model\b|NSManagedObject\b|extends\s+Table\b|@DriftDatabase|"
    r"DatabaseMigrator\b|RealmObject\b|:\s*Object\s*\{|@HiveType|@collection\b|onUpgrade\s*:|PersistableRecord\b|"
    r"VersionedSchema\b|SchemaMigrationPlan\b")

_CONTEXT_PERSISTED = (
    "This file defines data that is stored on users' devices. Installed apps keep the old data: a change to a stored "
    "type, table or key needs a versioned migration and a test that opens data written by the previous version. "
    "`mobile risk` reports a schema change that has no migration."
)
_CONTEXT_CAPABILITY = (
    "This file declares permissions, capabilities or privacy details. A new permission needs a user-facing purpose, "
    "may change store review and the privacy declarations (iOS privacy manifest, Google Play data safety), and must be "
    "named in the change summary."
)
_CONTEXT_GENERIC_SECRET = (
    "The edit assigns a long literal to a key, secret, token or password name. If it is a real credential it must not "
    "be in the repository or the app binary."
)
_CONTEXT_PBXPROJ = (
    "The Xcode project file is a serialized graph. Change only the entries the task needs, keep the existing order "
    "and identifiers, and confirm with `xcodebuild -list` that the project still loads."
)


def _count(pattern, text):
    return len(pattern.findall(text)) if text else 0


def check_edit(tool_name, tool_input, config, root):
    """Return a Verdict for an Edit or Write call."""
    verdict = Verdict(config.asks)
    path = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
    rel = util.rel_to(root, path) if path else None
    if not rel:
        return verdict
    name = rel.rsplit("/", 1)[-1]

    for pattern, hint in config.generated_rules():
        if util.glob_match(rel, pattern):
            verdict.add(DENY, "%s is generated; a hand edit is lost on the next build. %s" % (rel, hint))
            return verdict
    for pattern, hint in config_module.LOCKFILES:
        if util.glob_match(rel, pattern):
            verdict.add(DENY, "%s is a lockfile and is only changed by its resolver. %s" % (rel, hint))
            return verdict
    for pattern, why in config_module.SIGNING_MATERIAL:
        if util.glob_match(rel, pattern):
            verdict.add(DENY, (
                "%s: %s It is made by its own tool (keytool, Keychain Access, the developer portal); "
                "writing over it by hand destroys it." % (rel, why)))
            return verdict
    if not name.endswith((".example", ".sample", ".template", ".dist")):
        for pattern, why in config.sensitive_rules():
            if util.glob_match(rel, pattern):
                category = "own-config" if rel == config_module.CONFIG_NAME else "sensitive-files"
                if not verdict.add(ASK, "%s: %s Editing it needs a person's approval." % (rel, why), category):
                    verdict.note((
                        "%s: %s Keep the change small and name it in your summary; "
                        "`mobile risk` reports it for review." % (rel, why)), ident="sensitive:" + rel)
                break

    if tool_name == "Write":
        new_text = tool_input.get("content") or ""
        old_text = util.read_text(os.path.join(root, rel))
    else:
        new_text = tool_input.get("new_string") or ""
        old_text = tool_input.get("old_string") or ""

    for label, pattern in _SECRETS:
        for match in pattern.finditer(new_text):
            value = match.group(0)
            if value in old_text or _SECRET_PLACEHOLDER.search(value):
                continue
            verdict.add(DENY, (
                "This write contains %s. Anything committed or compiled into the app is recoverable by anyone. "
                "Keep real secrets on a server; load build-time keys from an untracked file "
                "(xcconfig, local.properties, --dart-define-from-file) that CI supplies." % label))
            break
    if verdict.decision != DENY:
        for label, pattern in _SUPPRESSIONS:
            if _count(pattern, new_text) > _count(pattern, old_text):
                if not verdict.add(ASK, (
                        "This edit adds %s. Fix the cause instead; if the suppression is truly right, the reason belongs "
                        "next to it and a person should agree." % label), "suppressions"):
                    verdict.note((
                        "This edit adds %s. Fix the cause where you can. If it has to stay, put the reason next to it "
                        "and name it in your summary: `mobile risk` reports new suppressions for review." % label))
                break
    return verdict


def edit_notes(tool_name, tool_input, config, root):
    """Facts worth telling the agent once after it edits a file: (id, text) pairs."""
    notes = []
    path = tool_input.get("file_path") or ""
    rel = util.rel_to(root, path) if path else None
    if not rel:
        return notes
    name = rel.rsplit("/", 1)[-1]
    new_text = tool_input.get("content") or tool_input.get("new_string") or ""
    old_text = tool_input.get("old_string") or ""
    if _GENERIC_SECRET.search(new_text) and not _GENERIC_SECRET.search(old_text):
        notes.append(("generic-secret", _CONTEXT_GENERIC_SECRET))
    if util.any_glob(rel, config_module.CAPABILITY):
        notes.append(("capability", _CONTEXT_CAPABILITY))
    if name == "project.pbxproj" or (name.endswith(".xcproj") and ".xcodeproj/" in rel):
        notes.append(("pbxproj", _CONTEXT_PBXPROJ))
    persisted = ".xcdatamodeld/" in rel or bool(_PERSISTED_MODEL.search(new_text) or _PERSISTED_MODEL.search(old_text))
    if not persisted and name.endswith((".swift", ".kt", ".java", ".dart")):
        persisted = bool(_PERSISTED_MODEL.search(util.read_text(os.path.join(root, rel), limit=200_000)))
    if persisted:
        notes.append(("persisted-model", _CONTEXT_PERSISTED))
    return notes
