#!/bin/bash
# Does a command work inside Claude Code's OS sandbox with given settings?
#
# Claude Code has no "run this in the sandbox" command, so this starts a headless
# session on the cheapest model that runs exactly one command and prints its output.
# Each probe costs well under one US cent. Run it from the project you want to test,
# in your own terminal (not from inside a sandboxed session).
#
#   scripts/sandbox-probe.sh [--settings '<json for the "sandbox" key>'] -- <command...>
#
# Examples
#   scripts/sandbox-probe.sh -- swift build --disable-sandbox
#   scripts/sandbox-probe.sh --settings '{"network":{"allowLocalBinding":true}}' -- flutter test --no-pub
#   scripts/sandbox-probe.sh -- ./gradlew --offline compileDebugKotlin
set -euo pipefail

extra='{}'
if [ "${1:-}" = "--settings" ]; then extra="$2"; shift 2; fi
[ "${1:-}" = "--" ] && shift
if [ "$#" -eq 0 ]; then sed -n '2,15p' "$0"; exit 2; fi
command -v claude >/dev/null || { echo "claude CLI not found"; exit 2; }

settings="$(python3 - "$extra" <<'EOF'
import json, sys
sandbox = {"enabled": True, "allowUnsandboxedCommands": False, "autoAllowBashIfSandboxed": True, "failIfUnavailable": True}
sandbox.update(json.loads(sys.argv[1]))
print(json.dumps({"sandbox": sandbox}))
EOF
)"

log=".sandbox-probe.log"
cmd="$*"
prompt="Use the Bash tool exactly once to run the command below with timeout 600000. Do not change it, do not retry, do not run anything else. Then reply with only the full tool output, verbatim, inside one code block.

( $cmd ) > $log 2>&1; echo PROBE_EXIT=\$?; tail -12 $log | cut -c1-240"

echo "sandbox settings: $settings"
echo "command:          $cmd"
result="$(claude -p "$prompt" --model haiku --max-turns 4 --allowedTools "Bash" --settings "$settings" --output-format json < /dev/null)"
python3 - "$result" <<'EOF'
import json, sys
data = json.loads(sys.argv[1])
print(data.get("result", "").strip())
print("cost: $%.4f" % (data.get("total_cost_usd") or 0))
EOF
rm -f "$log"
