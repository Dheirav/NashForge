#!/usr/bin/env bash
# The 05:35 burst, read by depth and by which solver decided, with standard
# errors. The headline has put the wrong set forward twice (v5b for Shadow and
# for PoetAndCoder) and the decomposition reversed both, so the headline is not
# the thing to read.
set -u
cd "$HOME/Code/PokerBot"
venv/bin/python scripts/chipzen_decompose.py --label v5x 2>&1 | tail -40
echo
echo "Twenty matches is about ±11 points, and this morning's queue served"
echo "Blueprint 16 times out of 20, so this can reject a disaster and cannot"
echo "confirm a gain. The replay is the evidence; this checks the protocol."
