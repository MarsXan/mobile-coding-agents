"""Claude Code hook entry points: `mobile hook <event>`.

Each reads the event JSON on stdin and answers on stdout in the documented
hook output format. Every handler is silent in a repository with no mobile
platform, so enabling the plugin somewhere else costs nothing.

Under Keel (a `.keel/config.json` in the project) the lint and stop handlers
stand down: Keel's own gates own those decisions.
"""

import json
import os
import re
import sys
import time

from . import config as config_module
from . import detect, guards, util, verify


def _read_payload():
    try:
        data = json.load(sys.stdin)
        return data if isinstance(data, dict) else {}
    except (ValueError, OSError):
        return {}


def _emit(obj):
    sys.stdout.write(json.dumps(obj))
    sys.stdout.write("\n")


def _root(payload):
    start = os.environ.get("CLAUDE_PROJECT_DIR") or payload.get("cwd") or os.getcwd()
    start = os.path.realpath(start)
    return util.git_root(start) or start


def _data_dir():
    return os.environ.get("CLAUDE_PLUGIN_DATA") or os.path.join(os.path.expanduser("~"), ".cache", "mobile-coding-agents")


def _session_path(payload):
    session_id = re.sub(r"[^A-Za-z0-9_-]", "_", str(payload.get("session_id") or "nosession"))[:80]
    return os.path.join(_data_dir(), "sessions", session_id + ".json")


def _prune_sessions(keep_days=14):
    directory = os.path.join(_data_dir(), "sessions")
    try:
        cutoff = time.time() - keep_days * 86400
        for name in os.listdir(directory):
            path = os.path.join(directory, name)
            if os.path.getmtime(path) < cutoff:
                os.remove(path)
    except OSError:
        pass


def _session(payload, root, create=True):
    """Per-session facts kept outside the repository: platforms and baseline."""
    path = _session_path(payload)
    session = util.read_json(path, default=None)
    if isinstance(session, dict) and session.get("root") == root:
        return session, path
    if not create:
        return {}, path
    facts = detect.detect(root)
    session = {"root": root, "platforms": facts["platforms"], "notes": []}
    if facts["platforms"]:
        session["baseline"] = verify.source_fingerprint(root, facts["platforms"])
    try:
        util.write_json(path, session)
    except OSError:
        pass
    session["_facts"] = facts
    return session, path


def _save(session, path):
    try:
        util.write_json(path, {k: v for k, v in session.items() if not k.startswith("_")})
    except OSError:
        pass


# --------------------------------------------------------------------------

def session_start(payload):
    root = _root(payload)
    _prune_sessions()
    path = _session_path(payload)
    previous = util.read_json(path, default=None)
    facts = detect.detect(root)
    if not facts["platforms"]:
        return 0
    session = {"root": root, "platforms": facts["platforms"], "notes": []}
    if isinstance(previous, dict) and previous.get("root") == root and previous.get("baseline"):
        session["baseline"] = previous["baseline"]      # a resumed session keeps its starting point
        session["nagged"] = previous.get("nagged")
        session["noticed"] = previous.get("noticed")
    else:
        session["baseline"] = verify.source_fingerprint(root, facts["platforms"])
    _save(session, path)

    config = config_module.load(root)
    lines = ["Mobile project facts, read from the project files by the mobile-coding-agents plugin:"]
    lines += detect.profile_lines(facts)
    lines.append("- An API newer than a minimum version above needs an availability check or a fallback.")
    if config.keel_adopted:
        lines.append("- This project is governed by Keel; its gates decide when a change is done.")
    else:
        lines.append("- `mobile verify --level quick|test|full` runs this project's checks and prints only the failures.")
    codemap = os.path.join(root, config["codemap"])
    if os.path.isfile(codemap):
        age_days = int((time.time() - os.path.getmtime(codemap)) / 86400)
        lines.append("- Code map: %s (updated %d days ago). It describes the modules, entry points and risky areas." % (config["codemap"], age_days))
    else:
        lines.append("- No code map exists yet (%s). `mobile recon` prints a structural inventory of this repository." % config["codemap"])
    for problem in getattr(config, "problems", []):
        lines.append("- Configuration problem: " + problem)
    sys.stdout.write("\n".join(lines) + "\n")
    return 0


def _fresh_notes(verdict, session, path):
    """The verdict's notes for the agent. One that carries an id is given once per session."""
    seen = set(session.get("notes") or [])
    texts = []
    for ident, text in verdict.context:
        if ident is None:
            texts.append(text)
        elif ident not in seen:
            seen.add(ident)
            texts.append(text)
    if len(seen) != len(session.get("notes") or []):
        session["notes"] = sorted(seen)
        _save(session, path)
    return texts


def _decision(verdict, notes=()):
    out = {"hookEventName": "PreToolUse"}
    if verdict.decision:
        out["permissionDecision"] = verdict.decision
        out["permissionDecisionReason"] = "[mobile-coding-agents] " + verdict.reason
    if notes and verdict.decision != guards.DENY:
        out["additionalContext"] = "[mobile-coding-agents] " + " ".join(notes)
    return {"hookSpecificOutput": out} if len(out) > 1 else None


def pre_bash(payload):
    root = _root(payload)
    session, _ = _session(payload, root)
    if not session.get("platforms"):
        return 0
    command = (payload.get("tool_input") or {}).get("command") or ""
    verdict = guards.check_bash(command, config_module.load(root), root)
    out = _decision(verdict)
    if out:
        _emit(out)
    return 0


def pre_edit(payload):
    root = _root(payload)
    session, path = _session(payload, root)
    if not session.get("platforms"):
        return 0
    verdict = guards.check_edit(payload.get("tool_name") or "Edit", payload.get("tool_input") or {}, config_module.load(root), root)
    out = _decision(verdict, _fresh_notes(verdict, session, path))
    if out:
        _emit(out)
    return 0


_LINT_LINE = re.compile(r"^(?P<file>.+?):(?P<line>\d+)(?::\d+)?: (?:(?P<kind>warning|error): )?(?P<msg>.+)$")


def _touched_range(root, rel, tool_name, tool_input):
    if tool_name == "Write" or tool_input.get("replace_all"):
        return None
    new_string = tool_input.get("new_string") or ""
    if not new_string.strip():
        return None
    text = util.read_text(os.path.join(root, rel), limit=5_000_000)
    offset = text.find(new_string)
    if offset < 0:
        return None
    first = text.count("\n", 0, offset) + 1
    last = first + new_string.count("\n")
    return first - 1, last + 1


def _find_up(root, rel, name):
    directory = os.path.dirname(os.path.join(root, rel))
    real_root = os.path.realpath(root)
    while True:
        if os.path.isfile(os.path.join(directory, name)):
            return True
        if os.path.realpath(directory) == real_root or os.path.dirname(directory) == directory:
            return False
        directory = os.path.dirname(directory)


def lint_touched(root, rel, tool_name, tool_input, limit=8):
    """Lint one file with the project's own linter; keep findings on touched lines."""
    if rel.endswith(".swift") and util.which("swiftlint") and _find_up(root, rel, ".swiftlint.yml"):
        code, out = util.run(["swiftlint", "lint", "--quiet", rel], cwd=root, timeout=25)
    elif rel.endswith((".kt", ".kts")) and util.which("ktlint") and _find_up(root, rel, ".editorconfig"):
        code, out = util.run(["ktlint", "--relative", rel], cwd=root, timeout=25)
    else:
        return []
    if code in (124, 126, 127):
        return []
    touched = _touched_range(root, rel, tool_name, tool_input)
    findings = []
    for line in out.splitlines():
        match = _LINT_LINE.match(line.strip())
        if not match:
            continue
        number = int(match.group("line"))
        if touched and not (touched[0] <= number <= touched[1]):
            continue
        findings.append("line %d: %s" % (number, match.group("msg").strip()))
    return util.truncate(findings, limit, "more findings in this file")


def post_edit(payload):
    root = _root(payload)
    session, path = _session(payload, root)
    if not session.get("platforms"):
        return 0
    tool_name = payload.get("tool_name") or "Edit"
    tool_input = payload.get("tool_input") or {}
    file_path = tool_input.get("file_path") or ""
    rel = util.rel_to(root, file_path) if file_path else None
    if not rel:
        return 0
    config = config_module.load(root)
    parts = []
    seen = set(session.get("notes") or [])
    for ident, text in guards.edit_notes(tool_name, tool_input, config, root):
        if ident not in seen:
            seen.add(ident)
            parts.append(text)
    if len(seen) != len(session.get("notes") or []):
        session["notes"] = sorted(seen)
        _save(session, path)
    if config["lintOnEdit"] and not config.keel_adopted:
        findings = lint_touched(root, rel, tool_name, tool_input)
        if findings:
            parts.append("Lint findings on the lines just edited in %s:\n  %s" % (rel, "\n  ".join(findings)))
    if parts:
        _emit({"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": "\n\n".join(parts)}})
    return 0


_UNVERIFIED = "Source files changed in this session and the current state has not passed `mobile verify`."


def stop(payload):
    """What happens when the agent finishes with source changes that were not verified.

    notice (default): one line for the person, once until the next verify. The
    agent is not sent back and nothing runs, so it costs no time.
    require: the agent is sent back once per unverified state to run the checks.
    """
    if payload.get("stop_hook_active"):
        return 0
    root = _root(payload)
    session, path = _session(payload, root, create=False)
    if not session.get("platforms") or not session.get("baseline"):
        return 0
    config = config_module.load(root)
    gate = config["verifyGate"]
    if config.keel_adopted or gate == "off":
        return 0
    current = verify.source_fingerprint(root, session["platforms"])
    if current == session.get("baseline") or verify.read_stamp(root).get("fingerprint") == current:
        if session.get("noticed"):
            session["noticed"] = False      # verified again: the next unverified change is news
            _save(session, path)
        return 0
    if gate == "require":
        if current == session.get("nagged"):
            return 0
        session["nagged"] = current
        _save(session, path)
        _emit({"decision": "block", "reason": "[mobile-coding-agents] " + _UNVERIFIED + (
            " Run `mobile verify --level quick` (use `test` when behaviour changed), then report the result."
            " If it cannot be verified here, say that plainly instead of calling the work done.")})
        return 0
    if session.get("noticed"):
        return 0
    session["noticed"] = True
    _save(session, path)
    _emit({"systemMessage": "[mobile-coding-agents] " + _UNVERIFIED})
    return 0


HANDLERS = {
    "session-start": session_start,
    "pre-bash": pre_bash,
    "pre-edit": pre_edit,
    "post-edit": post_edit,
    "stop": stop,
}


def main(event):
    handler = HANDLERS.get(event)
    if handler is None:
        sys.stderr.write("unknown hook event: %s\n" % event)
        return 1
    return handler(_read_payload())
