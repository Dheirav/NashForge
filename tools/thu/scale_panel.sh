#!/usr/bin/env bash
# Does the strength-scale fix help, hurt, or do nothing?
#
# Every threshold in the player was chosen when every rung had six classes, and
# v5i's deep rungs carry twenty, so `< top - 1` passes two thirds of hands short
# and nine tenths deep. The fix (branch opponent-reads) expresses each cut as
# the share it had on six classes. It touches rules that have fired 439 and 247
# times on deep rungs, so it does not go near a match without this.
#
# Both arms are the same ladder and the same archetypes; only the tree the code
# is read from differs. The main tree has the old thresholds, the worktree the
# new ones.
set -u
set -o pipefail   # a step that fails inside a pipeline must not report success
MAIN=$HOME/Code/PokerBot
TREE=$HOME/Code/PokerBot-reads
OUT=$HOME/pokerbot-scratch/hist/thu_scale_panel.md
FLAGS="--deep-primary --stack-cap"
: > "$OUT"
for arm in old new; do
  root=$MAIN; [ "$arm" = new ] && root=$TREE
  row="| $arm |"
  for kind in station nit maniac foldraise hoops meek bully; do
    ( cd "$root" && venv/bin/python scripts/chipzen_duel.py --a results/cfr/ladder169l_v5i \
        "--a-flags=$FLAGS" --a-label "v5i-$arm" --b "archetype:$kind" --b-label "$kind" \
        --arena-matches 2000 --seed 7 --workers 4 \
        --output "results/chipzen/panel/scale_${arm}_${kind}.json" ) \
        > "$HOME/pokerbot-scratch/hist/thu_scale_${arm}_${kind}.log" 2>&1
    row="$row $(grep -oE 'wins +[0-9.]+% ± +[0-9.]+' "$HOME/pokerbot-scratch/hist/thu_scale_${arm}_${kind}.log" | sed -E 's/wins +//') |"
  done
  echo "$row" >> "$OUT"
done
echo "| arm | station | nit | maniac | foldraise | hoops | meek | bully |" | cat - "$OUT" > "$OUT.tmp" && mv "$OUT.tmp" "$OUT"
cat "$OUT"
echo
echo "Read it as: if the new arm is not clearly better on any shape, the fix is"
echo "correct in principle and worth nothing in play, and it can wait for the"
echo "close season. If it is worse anywhere, the old thresholds were doing"
echo "something the six-class tuning did not intend and that is worth knowing."

# Prove it: the table must carry both arms with real percentages in them.
rows=$(grep -cE '^\| (old|new) \|.*%' "$OUT" || true)
[ "${rows:-0}" -ge 2 ] || { echo "scale-panel produced $rows arm rows, expected 2" >&2; exit 1; }
