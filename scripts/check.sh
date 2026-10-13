#!/bin/bash
# Static checks for the toolkit itself. Free: nothing here calls a model.
#   scripts/check.sh           run everything
# Exit code is non-zero if any check fails.
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT" || exit 1
fail=0

step() { printf '\n== %s\n' "$1"; }

step "Unit tests (guards, shell scanner, detection, verify, risk, hooks, adopt, doctor)"
for py in python3 /usr/bin/python3; do
  if command -v "$py" >/dev/null 2>&1; then
    printf '%s: ' "$("$py" --version 2>&1)"
    "$py" -m unittest discover -s core/tests -p 'test_*.py' 2>&1 | tail -3 | tr '\n' ' '
    echo
    "$py" -m unittest discover -s core/tests -p 'test_*.py' >/dev/null 2>&1 || fail=1
  fi
done

step "JSON files parse"
find . -name '*.json' -not -path './.git/*' -not -path '*/evals/results/*' -print0 | while IFS= read -r -d '' f; do
  python3 -c 'import json,sys; json.load(open(sys.argv[1]))' "$f" 2>/dev/null || { echo "invalid JSON: $f"; exit 1; }
done || fail=1
echo "ok"

step "Skill files: frontmatter, size, links to reference files"
python3 - <<'EOF' || fail=1
import glob, os, re, sys
bad = 0
for path in sorted(glob.glob("*/skills/*/SKILL.md")):
    text = open(path).read()
    match = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not match:
        print("no frontmatter:", path); bad += 1; continue
    front = match.group(1)
    desc = re.search(r"(?m)^description:\s*(.+)$", front)
    if not desc:
        print("no description:", path); bad += 1
    elif len(desc.group(1)) > 1024:
        print("description over 1024 characters (%d): %s" % (len(desc.group(1)), path)); bad += 1
    lines = text.count("\n")
    if lines > 500:
        print("over 500 lines:", path); bad += 1
    for link in re.findall(r"\]\((references/[^)]+)\)", text):
        if not os.path.isfile(os.path.join(os.path.dirname(path), link)):
            print("broken link %s in %s" % (link, path)); bad += 1
    for ref in re.findall(r"`references/([a-z-]+\.md)`", text):
        if not os.path.isfile(os.path.join(os.path.dirname(path), "references", ref)):
            print("missing reference %s named in %s" % (ref, path)); bad += 1
for rule in sorted(glob.glob("core/templates/rules/*.md")):
    platform = os.path.basename(rule)[:-3]
    skill = glob.glob("*/skills/%s/references" % platform)
    for ref in re.findall(r"`([a-z-]+\.md)`", open(rule).read()):
        if skill and not os.path.isfile(os.path.join(skill[0], ref)):
            print("rule %s names a missing reference: %s" % (rule, ref)); bad += 1
print("ok" if not bad else "%d problems" % bad)
sys.exit(1 if bad else 0)
EOF

step "Eval fixtures run and produce a project the hooks recognise"
for f in $(find core/evals evals -name fixture.sh | sort); do
  t="$(mktemp -d)"
  if (cd "$t" && HOME="$t" bash "$ROOT/$f" >/dev/null 2>&1) && [ -n "$(python3 core/bin/mobile detect --root "$t" | grep '^- ')" ]; then
    :
  else
    echo "fixture failed: $f"; fail=1
  fi
  rm -rf "$t"
done
echo "checked $(find core/evals evals -name fixture.sh | wc -l | tr -d ' ') fixtures"

if command -v claude >/dev/null 2>&1; then
  step "claude plugin validate --strict"
  for target in . core iOS Android Flutter ReactNative KotlinMultiplatform; do
    if claude plugin validate "$target" --strict >/dev/null 2>&1; then echo "ok   $target"; else echo "FAIL $target"; claude plugin validate "$target" --strict 2>&1 | tail -8; fail=1; fi
  done

  step "Always-on context cost (claude plugin details)"
  claude --plugin-dir core plugin details mobile-core 2>/dev/null | grep -E 'Always-on' | sed 's/^ */mobile-core:    /'
  for pair in iOS:mobile-ios Android:mobile-android Flutter:mobile-flutter ReactNative:mobile-react-native KotlinMultiplatform:mobile-kotlin-multiplatform; do
    claude --plugin-dir core --plugin-dir "${pair%%:*}" plugin details "${pair##*:}" 2>/dev/null | grep -E 'Always-on' | sed "s/^ */${pair##*:}: /"
  done
else
  step "claude CLI not on PATH: skipped plugin validation and cost measurement"
fi

if command -v node >/dev/null 2>&1; then
  step "Workflow script parses"
  node -e '
    const fs = require("fs");
    const src = fs.readFileSync("core/workflows/migration-audit.js", "utf8").replace(/^export const meta/m, "const meta");
    const AsyncFunction = Object.getPrototypeOf(async function(){}).constructor;
    new AsyncFunction("agent", "pipeline", "parallel", "phase", "log", "args", src);
    console.log("ok");' || fail=1
fi

printf '\n%s\n' "$([ "$fail" = 0 ] && echo 'ALL CHECKS PASSED' || echo 'SOME CHECKS FAILED')"
exit "$fail"
