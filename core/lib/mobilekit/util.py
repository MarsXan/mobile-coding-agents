"""Shared helpers: bounded tree walk, glob matching, git and process helpers."""

import hashlib
import json
import os
import re
import subprocess

# Directories that never hold hand-written source. Skipping them keeps every
# command fast on large repositories and keeps vendored code out of reports.
SKIP_DIRS = frozenset(
    {
        ".git", ".hg", ".svn", "node_modules", "Pods", "Carthage", "build",
        ".build", "DerivedData", ".dart_tool", ".gradle", ".idea", ".vscode",
        "vendor", ".symlinks", ".fvm", "xcuserdata", ".swiftpm", ".pub-cache",
        ".kotlin", "__pycache__", ".venv", "venv", ".cxx", ".mobile-coding-agents",
        "SourcePackages", ".bundle", "ephemeral",
    }
)

# Bundle directories that are a single unit to the developer. The walker
# reports them as entries and does not descend into them.
BUNDLE_SUFFIXES = (
    ".xcodeproj", ".xcworkspace", ".xcdatamodeld", ".xcassets", ".lproj",
    ".xcframework", ".framework", ".app", ".bundle", ".playground",
)

MAX_WALK_ENTRIES = 60000
# Deep enough for Kotlin and Java package folders in nested Gradle modules:
# feature/x/impl/src/main/kotlin/com/example/app/feature/x/impl/XViewModel.kt is 15 levels.
SOURCE_DEPTH = 24

# Test code by convention: an `AppTests/` or `AppUITests/` target, `src/test`,
# `src/androidTest`, `src/commonTest`, `test/`, `integration_test/`,
# `__tests__/`, or a `*Tests.swift`, `*Test.kt`, `*_test.dart`, `*.test.tsx`
# or `*.spec.ts` file.
TEST_PATH = re.compile(
    r"(^|/)(?:[A-Za-z0-9_]*(?:Tests|UITests|Test)|tests?|__tests__|androidTest|integration_test|test_driver|testFixtures)(/|$)"
    r"|Tests?\.(?:swift|kt|java|m)$|_test\.dart$|\.(?:test|spec)\.(?:ts|tsx|js|jsx)$")


def walk(root, max_depth=8, max_entries=MAX_WALK_ENTRIES, skip_dirs=SKIP_DIRS):
    """Yield (relative_path, is_dir) under root, breadth-first and bounded.

    Symlinked directories are not followed. Bundle directories are yielded as
    directories but not entered. Returns silently once max_entries is reached.
    """
    seen = 0
    queue = [("", 0)]
    while queue:
        rel_dir, depth = queue.pop(0)
        abs_dir = os.path.join(root, rel_dir) if rel_dir else root
        try:
            entries = sorted(os.scandir(abs_dir), key=lambda e: e.name)
        except OSError:
            continue
        for entry in entries:
            seen += 1
            if seen > max_entries:
                return
            rel = os.path.join(rel_dir, entry.name) if rel_dir else entry.name
            try:
                is_dir = entry.is_dir(follow_symlinks=False)
            except OSError:
                continue
            if is_dir:
                if entry.name in skip_dirs:
                    continue
                yield rel, True
                if entry.name.endswith(BUNDLE_SUFFIXES):
                    continue
                if depth + 1 < max_depth:
                    queue.append((rel, depth + 1))
            else:
                yield rel, False


_GLOB_CACHE = {}


def _expand_braces(pattern):
    match = re.search(r"\{([^{}]*)\}", pattern)
    if not match:
        return [pattern]
    head, tail = pattern[: match.start()], pattern[match.end():]
    out = []
    for option in match.group(1).split(","):
        out.extend(_expand_braces(head + option + tail))
    return out


def _glob_to_regex(pattern):
    i, out = 0, []
    while i < len(pattern):
        ch = pattern[i]
        if ch == "*":
            if pattern[i: i + 3] == "**/":
                out.append("(?:.*/)?")
                i += 3
                continue
            if pattern[i: i + 2] == "**":
                out.append(".*")
                i += 2
                continue
            out.append("[^/]*")
        elif ch == "?":
            out.append("[^/]")
        else:
            out.append(re.escape(ch))
        i += 1
    return "".join(out)


def glob_match(path, pattern):
    """Match a /-separated relative path against a gitignore-style glob.

    `**` crosses directories, `*` stays inside one segment, `{a,b}` expands.
    A pattern without a slash matches the file name at any depth.
    """
    path = path.replace(os.sep, "/")
    compiled = _GLOB_CACHE.get(pattern)
    if compiled is None:
        alternatives = []
        for expanded in _expand_braces(pattern.replace(os.sep, "/")):
            if expanded.startswith("./"):
                expanded = expanded[2:]
            if "/" not in expanded:
                expanded = "**/" + expanded
            alternatives.append(_glob_to_regex(expanded))
        compiled = re.compile("^(?:" + "|".join(alternatives) + ")$")
        _GLOB_CACHE[pattern] = compiled
    return compiled.match(path) is not None


def any_glob(path, patterns):
    for pattern in patterns:
        if glob_match(path, pattern):
            return pattern
    return None


def read_text(path, limit=2_000_000):
    """Read a text file leniently; returns '' when it is missing or binary."""
    try:
        with open(path, "rb") as handle:
            data = handle.read(limit)
    except OSError:
        return ""
    if b"\x00" in data[:4096]:
        return ""
    return data.decode("utf-8", errors="replace")


def read_json(path, default=None):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return default


def write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, sort_keys=True)
        handle.write("\n")
    os.replace(tmp, path)


def run(cmd, cwd=None, timeout=60, env=None):
    """Run a command (list form). Returns (exit_code, combined_output).

    Exit code 127 means the program is missing, 124 means it timed out.
    """
    try:
        proc = subprocess.run(
            cmd, cwd=cwd, env=env, timeout=timeout,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
    except FileNotFoundError:
        return 127, ""
    except subprocess.TimeoutExpired as exc:
        out = exc.stdout.decode("utf-8", errors="replace") if exc.stdout else ""
        return 124, out
    except OSError as exc:
        return 126, str(exc)
    return proc.returncode, proc.stdout.decode("utf-8", errors="replace")


_SEATBELT = None


def in_os_sandbox():
    """True when this process already runs inside a macOS Seatbelt sandbox.

    Sandboxes do not nest: tools that start their own (SwiftPM for manifests
    and plugins) fail inside Claude Code's. Asking the kernel for a trivial
    sandbox is the reliable way to find out.
    """
    global _SEATBELT
    if _SEATBELT is None:
        if os.uname().sysname != "Darwin" or not os.path.exists("/usr/bin/sandbox-exec"):
            _SEATBELT = False
        else:
            code, _ = run(["/usr/bin/sandbox-exec", "-p", "(version 1)(allow default)", "/usr/bin/true"], timeout=10)
            _SEATBELT = code != 0
    return _SEATBELT


def which(program):
    for directory in os.environ.get("PATH", "").split(os.pathsep):
        candidate = os.path.join(directory, program)
        if directory and os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    return None


def git(root, *args, timeout=30):
    return run(["git", "-C", root] + list(args), timeout=timeout)


def git_root(path):
    code, out = git(path, "rev-parse", "--show-toplevel")
    return out.strip() if code == 0 and out.strip() else None


def git_dir(root):
    code, out = git(root, "rev-parse", "--absolute-git-dir")
    return out.strip() if code == 0 and out.strip() else None


def project_root(start=None):
    """The directory every command treats as the project.

    Claude Code sets CLAUDE_PROJECT_DIR for hooks; otherwise the git top level
    of the starting directory, otherwise the starting directory itself.
    """
    env_root = os.environ.get("CLAUDE_PROJECT_DIR")
    if not start and env_root and os.path.isdir(env_root):
        return os.path.realpath(env_root)
    start = os.path.realpath(start or os.getcwd())
    return git_root(start) or start


def state_dir(root):
    """Where the toolkit keeps its own state: inside .git, never committed."""
    gdir = git_dir(root)
    base = os.path.join(gdir, "mobile-coding-agents") if gdir else os.path.join(root, ".mobile-coding-agents")
    os.makedirs(base, exist_ok=True)
    return base


def sha1(text):
    return hashlib.sha1(text.encode("utf-8", errors="replace")).hexdigest()


def rel_to(root, path):
    """Path relative to root with forward slashes, or None when outside root."""
    try:
        real_root = os.path.realpath(root)
        real = os.path.realpath(path if os.path.isabs(path) else os.path.join(root, path))
    except OSError:
        return None
    if real == real_root:
        return ""
    if not real.startswith(real_root + os.sep):
        return None
    return os.path.relpath(real, real_root).replace(os.sep, "/")


def truncate(lines, limit, label="more"):
    lines = list(lines)
    if len(lines) <= limit:
        return lines
    return lines[:limit] + ["... %d %s" % (len(lines) - limit, label)]
