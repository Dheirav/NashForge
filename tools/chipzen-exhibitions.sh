#!/usr/bin/env bash
# Unrated practice matches against named house bots, one after another.
#   tools/chipzen-exhibitions.sh PluriBot Fabulous Chatterbox
# Each match is its own process (so it loads whatever solver ladder exists at
# that moment) and its decisions land in ~/pokerbot-scratch/chipzen/matches/.
# Watch: tail -f ~/pokerbot-scratch/chipzen/exhibitions.log
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DIR="$HOME/pokerbot-scratch/chipzen"; mkdir -p "$DIR"
cd "$ROOT"
for name in "$@"; do
  echo "$(date '+%H:%M:%S') challenging $name"
  timeout 1800 venv/bin/python scripts/chipzen_run.py --log-dir "$DIR" --house-bot "$name" --once \
      > "$DIR/exhibition_${name}.log" 2>&1
  code=$?
  line=$(venv/bin/python - "$DIR/status.json" <<'PY'
import json, sys
s = json.load(open(sys.argv[1])); r = (s.get("recent") or [{}])[0]
print(f"{r.get('outcome') or r.get('reason') or 'no match'} vs {r.get('opponent')} in {r.get('hands')} hands; "
      f"decisions {s['decisions']} misses {s['misses']} fallbacks {s['fallbacks']} rejected {s['rejected']} slowest {s['slowest_ms']:.1f}ms")
PY
)
  echo "$(date '+%H:%M:%S') $name: exit $code: $line"
done
echo "$(date '+%H:%M:%S') exhibitions complete"
