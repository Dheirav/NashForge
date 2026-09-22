#!/usr/bin/env bash
# The Stack (chipzen.ai/stack/rss.xml), checked for new items.
#
# The feed is the platform's own writing: thirteen items from 25 May to 15
# September 2026, weekly through the summer and monthly since, and it is
# where a platform change is announced (the lobby-pushed challenges and
# auto-accept Dave promised in September, for one). It also published the
# 248k-hand corpus the archetypes are fitted to. A conditional fetch on the
# ETag costs nothing, so this is meant to run weekly from cron:
#   7 10 * * 3  ~/Code/PokerBot/tools/stack-feed.sh >> ~/pokerbot-scratch/stack-feed.log 2>&1
# Prints nothing when nothing is new, so a quiet log is the normal state.
set -euo pipefail
DIR="${STACK_DIR:-$HOME/pokerbot-scratch/stack}"; mkdir -p "$DIR"
FEED="$DIR/rss.xml"; SEEN="$DIR/seen.txt"; touch "$SEEN"
curl -sL --max-time 60 -z "$FEED" -o "$FEED.new" https://chipzen.ai/stack/rss.xml || { echo "$(date '+%F %T') fetch failed"; exit 0; }
[ -s "$FEED.new" ] && mv "$FEED.new" "$FEED" || rm -f "$FEED.new"
[ -s "$FEED" ] || exit 0
new=$(grep -oE "<link>https://chipzen.ai/stack/[^<]+</link>" "$FEED" | sed -E 's#</?link>##g' | grep -v '^https://chipzen.ai/stack/$' | grep -vxF -f "$SEEN" || true)
[ -z "$new" ] && exit 0
echo "$(date '+%F %T') new on The Stack:"
for url in $new; do
  title=$(grep -B4 "<link>$url</link>" "$FEED" | grep -oE "<title>[^<]*</title>" | tail -1 | sed -E 's#</?title>##g')
  date=$(grep -A6 "<link>$url</link>" "$FEED" | grep -oE "<pubDate>[^<]*</pubDate>" | head -1 | sed -E 's#</?pubDate>##g')
  echo "  ${date:0:16}  $title"
  echo "    $url"
done
printf '%s\n' $new >> "$SEEN"
