#!/usr/bin/env bash
# The field panel: a set against each scripted shape of the arena's field
# (chipzen/archetypes.py), in arena matches, one row per shape. Every duel
# before 22 September was our solver against our solver, which a change aimed
# at the field cannot register on; this is the instrument for those changes.
#   tools/panel.sh results/cfr/ladder169l_v5i "--deep-primary --stack-cap" v5i [matches]
# Writes results/chipzen/panel/<label>.json and prints the row.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; cd "$ROOT"
DIR=$1; FLAGS=$2; LABEL=$3; N=${4:-1000}
mkdir -p results/chipzen/panel
row="| $LABEL |"
for kind in station nit maniac foldraise; do
  out=results/chipzen/panel/${LABEL}_vs_${kind}.json
  line=$(venv/bin/python scripts/chipzen_duel.py --a "$DIR" "--a-flags=$FLAGS" --a-label "$LABEL" --b archetype:$kind --b-label $kind \
         --arena-matches "$N" --seed 7 --output "$out" 2>&1 | grep -E "arena matches, " | tail -1)
  pct=$(echo "$line" | grep -oE "wins +[0-9.]+% ± +[0-9.]+" | sed -E 's/wins +//')
  row="$row $pct |"
done
echo "| set | station | nit | maniac | foldraise |"; echo "|---|---|---|---|---|"; echo "$row"
