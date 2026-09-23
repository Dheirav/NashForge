#!/usr/bin/env bash
# `meek` and `bully` were fitted by hand from wsp's and Shadow's node
# frequencies on 23 and 24 September, and the four corpus shapes have never
# been calibrated at all. This plays each against v5i, profiles the hands with
# the scout's own code, and prints the archetype's frequencies beside the real
# bot's. Until those two columns agree, a panel row about them means nothing.
set -u
cd "$HOME/Code/PokerBot"
venv/bin/python scripts/chipzen_calibrate.py --kinds meek bully sticky nofold3bet folder wildpassive \
  --matches 300 --ladder results/cfr/ladder169l_v5i 2>&1 | tail -60
