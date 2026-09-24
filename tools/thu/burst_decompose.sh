#!/usr/bin/env bash
# The 05:35 burst, read by depth and by which solver decided, with standard
# errors. The headline has put the wrong set forward twice (v5b for Shadow and
# for PoetAndCoder) and the decomposition reversed both, so the headline is not
# the thing to read.
set -u
set -o pipefail   # a step that fails inside a pipeline must not report success
cd "$HOME/Code/PokerBot"
venv/bin/python scripts/chipzen_decompose.py --label v5x 2>&1 | tail -40
echo
echo "Twenty matches is about ±11 points, and this morning's queue served"
echo "Blueprint 16 times out of 20, so this can reject a disaster and cannot"
echo "confirm a gain. The replay is the evidence; this checks the protocol."

# Prove it: an empty decomposition is exactly what happened on 24 September,
# every category blank, and the step still reported done.
filled=$(venv/bin/python scripts/chipzen_decompose.py --label v5x 2>/dev/null | grep -cE '^\| .* [0-9]' || true)
[ "${filled:-0}" -ge 2 ] || { echo "decomposition came back empty ($filled filled rows)" >&2; exit 1; }
