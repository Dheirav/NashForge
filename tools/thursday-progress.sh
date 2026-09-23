#!/usr/bin/env bash
# Where Thursday's driver has got to, and what is left.
#   tools/thursday-progress.sh [--watch]
#
# Reads the plan and the status file, so it tells you the truth even if the
# plan was edited mid-day. Times left are the sum of the remaining budgets,
# which is a ceiling rather than a guess: steps usually finish inside them.
PLAN=${PLAN:-$HOME/pokerbot-scratch/hist/thursday.plan}
STATUS=${STATUS:-$HOME/pokerbot-scratch/hist/thursday.status}
LOG=${LOG:-$HOME/pokerbot-scratch/hist/laneTHU.log}
CUTOFF=${CUTOFF:-"2026-09-24 21:45"}

report() {
  echo "=== $(date '+%a %H:%M:%S %Z')   plan: $PLAN"
  [ -s "$PLAN" ] || { echo "  no plan file"; return; }
  local left=0 running="" now
  now=$(date +%s)
  printf "  %-18s %-11s %s\n" STEP STATE NOTE
  grep -vE '^\s*#|^\s*$' "$PLAN" | while read -r mode name budget cmd; do
    local row state note
    row=$(grep "|$name|" "$STATUS" 2>/dev/null | tail -1)
    if [ -n "$row" ]; then
      state=$(echo "$row" | cut -d'|' -f3); note=$(echo "$row" | cut -d'|' -f4)
      if [ "$state" = "started" ]; then
        local began; began=$(date -d "$(echo "$row" | cut -d'|' -f1)" +%s)
        note="running ${budget}m budget, $(( (now - began) / 60 ))m elapsed"
      fi
    else
      state="waiting"; note="${budget}m budgeted"
    fi
    printf "  %-18s %-11s %s\n" "$name" "$state" "$note"
  done
  left=$(grep -vE '^\s*#|^\s*$' "$PLAN" | while read -r mode name budget cmd; do
           grep -q "|$name|" "$STATUS" 2>/dev/null || echo "$budget"; done | paste -sd+ | bc 2>/dev/null)
  if [ -n "$left" ]; then
    local window slack burst=55
    local from=$now
    [ -n "${START:-}" ] && [ "$(date -d "${START:-@0}" +%s 2>/dev/null || echo 0)" -gt "$now" ] && from=$(date -d "$START" +%s)
    window=$(( ( $(date -d "$CUTOFF" +%s) - from ) / 60 ))
    slack=$(( window - left ))
    [ "$(date +%H%M)" -gt 0630 ] && burst=0
    slack=$(( slack - burst ))
    echo "  budgeted still to run: $((left / 60))h $((left % 60))m"
    echo "  window to the $CUTOFF cutoff: $((window / 60))h $((window % 60))m"
    if [ "$slack" -ge 0 ]; then
      echo "  SLACK: ${slack}m spare$([ "$burst" -gt 0 ] && echo " (after allowing $burst m for the burst)")"
    else
      echo "  OVER BY $(( -slack ))m: edit the plan, or the last steps will hit the cutoff"
    fi
  fi
  echo "  last lines:"; tail -3 "$LOG" 2>/dev/null | sed 's/^/    /'
}
if [ "${1:-}" = "--watch" ]; then
  while :; do report; sleep 120; echo; done
else
  report
fi
