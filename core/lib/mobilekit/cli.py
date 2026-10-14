"""Command-line entry point: `mobile <command>`."""

import argparse
import json
import os
import sys

from . import __version__, util


def _root(args):
    return util.project_root(getattr(args, "root", None))


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="mobile",
        description="Deterministic checks for iOS, Android and Flutter repositories. No command calls a model.")
    parser.add_argument("--version", action="version", version="mobile-coding-agents %s" % __version__)
    sub = parser.add_subparsers(dest="command")

    p = sub.add_parser("detect", help="platforms, minimum OS versions and toolchain versions read from project files")
    p.add_argument("--json", action="store_true")
    p.add_argument("--root")

    p = sub.add_parser("verify", help="run the project's checks; print only failures with file and line")
    p.add_argument("--level", choices=("quick", "test", "full"), default="quick")
    p.add_argument("--platform", action="append", choices=("ios", "android", "flutter", "react-native", "kotlin-multiplatform"))
    p.add_argument("--dry-run", action="store_true", help="show the commands without running them")
    p.add_argument("--root")

    p = sub.add_parser("recon", help="structural inventory of the repository: sizes, patterns, hotspots")
    p.add_argument("--json", action="store_true")
    p.add_argument("--root")

    p = sub.add_parser("risk", help="mobile risk signals in the current change (schema, permissions, weakened tests)")
    p.add_argument("--base", help="commit or branch to compare against (default: merge base with the base branch)")
    p.add_argument("--json", action="store_true")
    p.add_argument("--fail-on", choices=("block", "warn", "info", "never"), default="block")
    p.add_argument("--root")

    p = sub.add_parser("doctor", help="check toolchain, project overlay, permission rules and always-on context")
    p.add_argument("--root")

    p = sub.add_parser("adopt", help="write the project overlay into an application repository (never overwrites)")
    p.add_argument("--target", default=".")
    p.add_argument("--platforms", help="comma-separated: ios,android,flutter,react-native,kotlin-multiplatform (default: detected)")
    p.add_argument("--marketplace", help="git URL, owner/repo, or local path of the toolkit (default: this checkout)")
    p.add_argument("--merge-settings", action="store_true", help="add entries to an existing .claude/settings.json")
    p.add_argument("--dry-run", action="store_true")

    p = sub.add_parser("hook", help="Claude Code hook entry point (called by the plugin, not by people)")
    p.add_argument("event")

    args = parser.parse_args(argv)
    if args.command == "detect":
        from . import detect
        facts = detect.detect(_root(args))
        if args.json:
            print(json.dumps(facts, indent=2))
        else:
            lines = detect.profile_lines(facts)
            print("\n".join(lines) if lines else "No mobile project detected in %s" % facts["root"])
        return 0
    if args.command == "verify":
        from . import verify
        return verify.main(_root(args), level=args.level, platforms=args.platform, dry_run=args.dry_run)
    if args.command == "recon":
        from . import recon
        return recon.main(_root(args), as_json=args.json)
    if args.command == "risk":
        from . import risk
        return risk.main(_root(args), base=args.base, as_json=args.json, fail_on=args.fail_on)
    if args.command == "doctor":
        from . import doctor
        return doctor.main(_root(args))
    if args.command == "adopt":
        from . import adopt
        platforms = [p.strip() for p in args.platforms.split(",") if p.strip()] if args.platforms else None
        return adopt.main(os.path.abspath(args.target), platforms=platforms, marketplace=args.marketplace,
                          merge_settings=args.merge_settings, dry_run=args.dry_run)
    if args.command == "hook":
        from . import hooks
        return hooks.main(args.event)
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
