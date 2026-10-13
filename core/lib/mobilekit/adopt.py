"""`mobile adopt`: write the project overlay into an application repository.

Run by a person, in their own terminal, once per repository. It never
overwrites: a file that already exists is left alone and the proposed
version is written beside it as `<name>.proposed`, so a human merges it.
The one exception is `--merge-settings`, which only ever adds entries to
`.claude/settings.json` and keeps a timestamped backup.
"""

import json
import os
import time

from . import config as config_module
from . import detect, util

MARKETPLACE = "mobile-coding-agents"
PLATFORMS = ("ios", "android", "flutter")


def templates_dir():
    return os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "templates"))


def marketplace_root():
    return os.path.normpath(os.path.join(templates_dir(), "..", ".."))


def _render(text, values):
    for key, value in values.items():
        text = text.replace("{{%s}}" % key, value)
    return text


def _union(existing, extra):
    out = list(existing)
    for item in extra:
        if item not in out:
            out.append(item)
    return out


def build_settings(platforms, marketplace_source):
    """Compose .claude/settings.json from the shared and per-platform fragments."""
    base = util.read_json(os.path.join(templates_dir(), "settings", "shared.json"), default={})
    permissions = base.setdefault("permissions", {})
    for platform in platforms:
        fragment = util.read_json(os.path.join(templates_dir(), "settings", "%s.json" % platform), default={})
        for kind in ("allow", "ask", "deny"):
            permissions[kind] = _union(permissions.get(kind, []), (fragment.get("permissions") or {}).get(kind, []))
    plugins = {"mobile-core@%s" % MARKETPLACE: True}
    for platform in platforms:
        plugins["mobile-%s@%s" % (platform, MARKETPLACE)] = True
    base["enabledPlugins"] = plugins
    if marketplace_source:
        base["extraKnownMarketplaces"] = {MARKETPLACE: {"source": marketplace_source}}
    return base


def _marketplace_source(value):
    """Return (source_object, is_machine_local)."""
    if not value:
        return {"source": "directory", "path": marketplace_root()}, True
    if os.path.isdir(os.path.expanduser(value)):
        return {"source": "directory", "path": os.path.abspath(os.path.expanduser(value))}, True
    if "/" in value and "://" not in value and not value.endswith(".git") and "@" not in value and value.count("/") == 1:
        return {"source": "github", "repo": value}, False
    return {"source": "git", "url": value}, False


def plan(target, platforms, marketplace=None):
    """Return the list of (relative_path, content, mode) the overlay consists of."""
    facts = detect.detect(target)
    platforms = platforms or facts["platforms"]
    name = os.path.basename(os.path.abspath(target))
    values = {
        "PROJECT": name,
        "PLATFORMS": ", ".join({"ios": "iOS", "android": "Android", "flutter": "Flutter"}[p] for p in platforms) or "mobile",
    }
    source, local = _marketplace_source(marketplace)
    files = []
    tdir = templates_dir()
    files.append(("AGENTS.md", _render(util.read_text(os.path.join(tdir, "AGENTS.md")), values)))
    files.append(("CLAUDE.md", _render(util.read_text(os.path.join(tdir, "CLAUDE.md")), values)))
    files.append((config_module.CONFIG_NAME, _render(util.read_text(os.path.join(tdir, "mobile-coding-agents.json")), values)))
    for platform in platforms:
        files.append((".claude/rules/mobile-%s.md" % platform, util.read_text(os.path.join(tdir, "rules", "%s.md" % platform))))
    settings = build_settings(platforms, None if local else source)
    files.append((".claude/settings.json", json.dumps(settings, indent=2) + "\n"))
    if local:
        files.append((".claude/settings.local.json", json.dumps({"extraKnownMarketplaces": {MARKETPLACE: {"source": source}}}, indent=2) + "\n"))
    return platforms, files, local


def _merge_settings(path, proposed):
    existing = util.read_json(path, default=None)
    if not isinstance(existing, dict):
        return None
    merged = json.loads(json.dumps(existing))
    permissions = merged.setdefault("permissions", {})
    for kind in ("allow", "ask", "deny"):
        permissions[kind] = _union(permissions.get(kind, []), (proposed.get("permissions") or {}).get(kind, []))
    for key in ("enabledPlugins", "extraKnownMarketplaces"):
        if proposed.get(key):
            section = merged.setdefault(key, {})
            for name, value in proposed[key].items():
                section.setdefault(name, value)
    return merged


def main(target, platforms=None, marketplace=None, merge_settings=False, dry_run=False, out=print):
    target = os.path.abspath(target)
    if not os.path.isdir(target):
        out("mobile adopt: %s is not a directory" % target)
        return 2
    if os.path.realpath(target) == os.path.realpath(marketplace_root()):
        out("mobile adopt: this is the toolkit itself. Run it inside an application repository (or pass --target).")
        return 2
    unknown = [p for p in (platforms or []) if p not in PLATFORMS]
    if unknown:
        out("mobile adopt: unknown platform %s (choose from %s)" % (", ".join(unknown), ", ".join(PLATFORMS)))
        return 2
    chosen, files, local = plan(target, platforms, marketplace)
    if not chosen:
        out("mobile adopt: no iOS, Android or Flutter project found in %s. Pass --platforms ios,android,flutter to adopt anyway." % target)
        return 2
    out("mobile adopt · %s · platforms: %s%s" % (target, ", ".join(chosen), " · dry run" if dry_run else ""))
    for rel, content in files:
        path = os.path.join(target, rel)
        if not os.path.exists(path):
            out("  create   %s" % rel)
            if not dry_run:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "w", encoding="utf-8") as handle:
                    handle.write(content)
            continue
        if util.read_text(path) == content:
            out("  same     %s" % rel)
            continue
        if rel.endswith("settings.json") and merge_settings:
            merged = _merge_settings(path, json.loads(content))
            if merged is not None:
                backup = "%s.bak-%s" % (rel, time.strftime("%Y%m%d-%H%M%S"))
                out("  merge    %s (entries added only; previous version kept as %s)" % (rel, backup))
                if not dry_run:
                    os.replace(path, os.path.join(target, backup))
                    with open(path, "w", encoding="utf-8") as handle:
                        handle.write(json.dumps(merged, indent=2) + "\n")
                continue
        out("  exists   %s -> proposed version written to %s.proposed (merge by hand)" % (rel, rel))
        if not dry_run:
            with open(path + ".proposed", "w", encoding="utf-8") as handle:
                handle.write(content)
    out("")
    out("Next:")
    out("  1. Read the files above. AGENTS.md is yours: keep only what an agent could not work out from the code.")
    out("  2. Set the verify commands in %s if the defaults do not fit (`mobile verify --dry-run` shows them)." % config_module.CONFIG_NAME)
    if local:
        out("  3. The marketplace points at a path on this machine (.claude/settings.local.json; keep it out of git).")
        out("     For the team, host the toolkit in git and re-run with --marketplace <git url>.")
    out("  %d. Start Claude Code here, accept the plugin trust prompt, and run `mobile doctor`." % (4 if local else 3))
    return 0
