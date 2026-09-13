#!/usr/bin/env bash
# What the Chipzen bot is doing, from its status file. --watch to refresh.
set -uo pipefail
DIR="$HOME/pokerbot-scratch/chipzen"
show() {
  if [ -f "$DIR/run.pid" ] && ps -p "$(cat "$DIR/run.pid")" >/dev/null 2>&1; then
    echo "process: running (pid $(cat "$DIR/run.pid"))"
  else
    echo "process: NOT running"
  fi
  [ -f "$DIR/status.json" ] || { echo "no status yet"; return; }
  python3 - "$DIR/status.json" <<'PY'
import json, sys, time
s = json.load(open(sys.argv[1]))
age = time.time() - s["last_event_at"] if s["last_event_at"] else None
up = time.time() - s["started_at"]
print(f"lobby:    {s['lobby']}   (connected {s['lobby_connects']}x, up {up/60:.0f} min)")
print(f"last:     {s['last_event']}" + (f"   [{age:.0f}s ago]" if age is not None else ""))
print(f"matches:  {s['matches_finished']} finished, {s['matches_active']} active, "
      f"{s['wins']} won / {s['losses']} lost   hands {s['hands']}")
print(f"decides:  {s['decisions']}  misses {s['misses']}  fallbacks {s['fallbacks']}  "
      f"rejected {s['rejected']}  slowest {s['slowest_ms']:.1f} ms")
c = s.get("current") or {}
if c:
    print(f"current:  vs {c.get('opponent')}  seat {c.get('seat')}  hand {c.get('hands')}  "
          f"rated={c.get('rated')}  clock {c.get('timeout_ms')} ms")
for r in (s.get("recent") or [])[:5]:
    print(f"  {time.strftime('%H:%M', time.localtime(r['finished_at']))}  "
          f"{r.get('outcome') or r.get('reason')}  vs {r.get('opponent')}  {r.get('hands')} hands  "
          f"{'rated' if r.get('rated') else 'unrated'}")
PY
}
if [ "${1:-}" = "--watch" ]; then
  while true; do clear; date '+%H:%M:%S IST'; show; sleep 5; done
else
  show
fi
