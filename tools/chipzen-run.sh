#!/usr/bin/env bash
# Start NashForge on Chipzen in the background, with a pid file and a log.
#   tools/chipzen-run.sh                 # hold the lobby
#   tools/chipzen-run.sh --house-bot --once
#   tools/chipzen-run.sh stop
# Watch it: tools/chipzen-progress.sh --watch
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DIR="$HOME/pokerbot-scratch/chipzen"
mkdir -p "$DIR"
PID="$DIR/run.pid"; LOG="$DIR/run.log"

if [ "${1:-}" = "stop" ]; then
  if [ -f "$PID" ] && ps -p "$(cat "$PID")" >/dev/null 2>&1; then
    pkill -TERM -P "$(cat "$PID")" 2>/dev/null; kill "$(cat "$PID")"; echo "stopped $(cat "$PID")"
  else
    echo "not running"
  fi
  rm -f "$PID"; exit 0
fi
if [ -f "$PID" ] && ps -p "$(cat "$PID")" >/dev/null 2>&1; then
  echo "already running as $(cat "$PID"); tools/chipzen-run.sh stop first"; exit 1
fi
cd "$ROOT"
# A supervisor loop: the Python process already reconnects the lobby on its
# own, but a process that dies for any other reason would otherwise stay dead
# through a fixture. --once runs (exhibitions) exit cleanly and are not restarted.
nohup bash -c '
  while true; do
    venv/bin/python scripts/chipzen_run.py --log-dir "$0" "$@"; code=$?
    if [ "$code" -eq 0 ]; then exit 0; fi
    echo "$(date "+%F %T") supervisor: exited with $code, restarting in 10s"
    sleep 10
  done' "$DIR" "$@" >> "$LOG" 2>&1 &
echo $! > "$PID"
echo "started $(cat "$PID"); log $LOG"
echo "watch: tools/chipzen-progress.sh --watch"
