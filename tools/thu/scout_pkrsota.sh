#!/usr/bin/env bash
# Thursday's opponent, which had nothing on the platform at all as of 23 Sept:
# zero matches on record, rating 0, three walkovers. If tonight's round gave it
# a match, this picks it up; if not, we go in blind and the fixture is probably
# won by turning up.
set -u
cd "$HOME/Code/PokerBot"
venv/bin/python scripts/chipzen_scout.py --names pkr-sota lil-bot-v2 RiverReasonBot \
  --refresh --seed-profiles 2>&1 | tail -25
echo
venv/bin/python scripts/opponent_coverage.py 2>&1 | head -12
