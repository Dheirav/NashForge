# Leg (d): does a stronger hand fold more to an all-in than its neighbour?

5 October 2026, branch `fold-jumps`. The stopping rule in `2026-10-05-convergence-and-compute.md`
has four legs, and (d), "adjacent-hand fold jumps at shove nodes do not worsen", was the one with no
script. This is that script, `scripts/fold_jumps.py`, with 15 tests in `tests/test_fold_jumps.py`.

## What it checks

A jump between neighbouring hands is not a defect by itself. Facing an all-in, the right answer is
close to a threshold (call above it, fold below it), so two neighbours can be a whole 1.0 apart and
both be right. What cannot be right is the order going the wrong way, where a hand that beats its
neighbour card for card folds clearly more. So at every preflop node facing an all-in, each class is
compared with the class one rank below it in either card, same suitedness (AQs against AJs and
KQs, KK against QQ), and a pair is flagged when the stronger hand folds at least 0.2 more.

Two things are left out because nothing trained them: a class whose own reach to the node is under
0.05, and an entry still exactly uniform (counted, not compared).

**Own reach alone was not enough, and the first run showed why.** At `5` (the small blind
open-shoves) the big blind has not acted, so every class's own reach is 1. The node is still almost
never trained, because the solver's small blind almost never open-shoves at 70bb, and its table is
nonsense: on the 70bb rung at 10M the big blind folded 33 there and called with 22. On the 20M rung,
59 of 70 flagged pairs were at that node and the three where the small blind's raise is shoved over
by a line it rarely meets, all at a line probability of 0.002 or less. So each flag is weighted by
how often the line is played, which is the opponent's line probability (its range's own reach, by
combinations) times the stronger class's own reach. The verdict between a solve at T and one at 2T
is pass when that weighted excess is no larger at 2T.

## Results

**The 70bb (4,2,1) self-play rung, 10M against 20M** (the pair from the 10M check): weighted excess
0.0563 at 10M and 0.0498 at 20M, so **(d) passes**. On the lines that are actually played, 10 pairs
are flagged at 10M and 11 at 20M, so doubling the iterations did not change the order. That agrees
with the other three legs on this rung.

**v5xRR3, the live set, rung by rung** (`~/pokerbot-scratch/h2h10m/fold_jumps_v5xRR3.json`). Most
flags sit on lines that are almost never played: 35bb has 123 flagged pairs carrying 0.0007 of
weight, and the 100bb cap-2 rung has 73 carrying 0.003. Two rungs stand out:

- **12bb, at `15` (we limp, they shove), a line the opponent takes 21 percent of the time.** Q7s
  folds 97 percent against Q6s 37, and 97s folds 69 against 87s 12.
- **18bb, at `35` (we raise pot, they shove), a line probability of 0.08.** Q8o folds 98 against
  J8o 49.

**Priced the same night, the 12bb spot is not a leak.** Each small-blind class's equity against the
rung's own shove range (its big blind's shove share after a limp, by combinations, from
`results/cfr/chance/nolimit_12bb_preflop_allin.npy`, card removal ignored), against the 45.8 percent a
call needs (11bb to win a 24bb pot): the whole fold and call mix at `15` costs **0.022 bb/100** against
the best reply to that range. Every flagged hand is within about 1.5 points of the line (equity 44.2
to 46.8 percent), so calling or folding any of them is worth 0.4bb or less. And the order the check
assumed is not always the order of equity there: 87s has slightly more than 97s, T7s more than J7s
(45.6 against 45.2) and T8s more than J8s (46.8 against 46.0), likely because the shove range holds
the AJ, KJ and QJ that dominate a jack more than a ten. Q7s folding against Q6s calling 63 percent is
Q7s right (44.9 percent) and Q6s calling slightly wrong (44.2). So no retrain. The 18bb spot was not
priced.

## The verdict moved to chips (6 October)

The 12bb pricing showed that rank order cannot be the verdict: the most flagged pair on that rung was correct
play, and near the calling line rank is not even the order of equity. So `scripts/fold_jumps.py` now prices
every preflop all-in node, and the T against 2T verdict is on that price. The rank pairs are still printed,
as a list to read.

**How each node is priced.**

- *The price* comes from the trainer's own chip rules: the history is replayed through
  `games.nolimit.NoLimitHoldem`, which gives the call and the final pot if called. The native solver sizes
  raises by the same formula (`native/src/nolimit.hpp`, half pot, pot and twice pot from the pot after calling,
  at least a big blind, capped at the stack, rounding half to even as Python's `round` does), so these are the
  tree's sizes. A history the game would not allow raises an error instead of being priced as something else.
  Checked against a hand calculation on seven lines, for example `15` at 12bb is 11bb into a 24bb pot (45.8
  percent), `35` at 18bb is 15bb into 36bb (41.7), and `1445` at 70bb is 45bb into 140bb (32.1).
- *The equity* of each class against the opponent's range at the node, where the range is each class's
  combinations times the opponent's own reach to the node, from the preflop all-in table
  (`results/cfr/chance/nolimit_12bb_preflop_allin.npy`). The table was built at 12bb, but preflop all-in equity
  does not depend on the stacks, so it holds at every depth. Its cells are sampled (a few hundredths of noise)
  and card removal between the two hands is ignored. The 169 classes are numbered by a fixed sort, so every
  169-class solve indexes the table alike; a coarser preflop abstraction is not priced.
- *The cost* of a class is what its fold share loses against the best reply to that range: the call's value
  times the fold share when calling wins, the call's loss times the call share when it loses. It is weighted
  by how often the class is dealt and reaches the node and by the opponent's line probability, in big blinds
  per 100 hands dealt at that depth. Entries still uniform are priced as they would play.

This measures the solve against the best reply to its own ranges, which is not exploitability. A range that
is itself wrong, too tight or too loose against real opponents, is not caught here.

**The 12bb spot reproduces:** `15` on v5xRR3's 12bb rung costs 0.0220 bb/100, the figure of the scratch
pricing. **The 18bb spot I left unpriced** (`35`, we open pot and face a shove, line probability 0.082) costs
0.042 bb/100: the same near-the-line mixing, Q6s at 40.3 percent equity calling 56 percent and K5o at 42.2
folding 40, where a call needs 41.7.

**v5xRR3, every rung, bb per 100 hands at that depth** (`~/pokerbot-scratch/fold-cost/v5xRR3.json`):

| rung | cost | where most of it is |
|---|---|---|
| cap2 100bb | 0.72 | `245` 0.53 |
| cap2 70bb | 1.15 | `245` 0.61, `345` 0.35 |
| cap2 50bb | 1.00 | `245` 0.55, `345` 0.25 |
| cap2 35bb | 0.03 | |
| cap2 25bb | 0.09 | |
| cap2 18bb | 0.05 | `35` 0.04 |
| cap2 12bb | 0.13 | `5` 0.04, `25` 0.04, `15` 0.02 |
| nolimit 5 to 100bb | 0.05 to 0.27 | mostly `5`, the open shove, which these one-raise rungs see |
| taper42 12 to 35bb | 0.40 to 0.82 | `15` and `5` |

**The deep exploiter rungs call four-bet shoves too wide.** At `245` (we three-bet, the small blind
four-bets all in) the 50, 70 and 100bb rungs call AQo, AJo and ATo with a fold share of 0 to 1 percent, at 22
to 38 percent equity against the rung's own shove range, for example AQo at 100bb loses 26.5bb a call at 31.7
percent where 45 is needed. It is the recipe, not the iterations: on the self-play 70bb rung the same node
costs 0.05 to 0.06 (its shove range is wider, AQo has 46 percent against it and folds 31), and v5xRR3's
station-share 70bb rung costs 0.61 there at both 10M and 20M. Against the solver's own range this is the
largest cost on the set. Whether it costs chips in the arena depends on how wide real bots four-bet shove,
which this check cannot see; the next step is the same pricing against the shove ranges in the opponent
profiles, before calling it a leak.

**10M against 20M on the chip verdict.** The self-play 70bb pair: 0.374 bb/100 at 10M and 0.252 at 20M,
pass. v5xRR3's station-share 70bb rung retrained at 10M against its 20M: 1.432 and 1.149, pass. Both agree
with the rank verdict, and with the other legs on those rungs.

## Limits

- Raising one card by a rank is nearly always worth equity against an all-in range, but not always
  by much. Connectors against one-gappers (87s and 97s) are close, so a flag there may be noise
  around a real tie.
- **Near the calling line the rank order is not the equity order**, because a shove range dominates
  some higher cards more than lower ones (the 12bb result above). A flag between two hands within a
  couple of points of the line can be correct play. The better test there is the one used above, the
  cost against the shove range from the all-in table, and a later version of this script should
  flag by that cost rather than by rank.
- Preflop only, because only there are the classes hands; a postflop bucket mixes strength with
  texture.
- It reads folds facing a shove. Our own shoves, such as v5f's 27 percent T9s and 98 percent jacks,
  are what `scripts/strategy_sweep.py` lists.
- The weighted excess is comparable between two solves of one tree, not across depths, because the
  line probabilities differ.
- The reach weight is the same self-play proxy as the visit counter's. On an exploiter rung trained
  against a scripted opponent, the opponent's line probability in the table is the solver's own
  model of that seat, not the script's.

## Checks of the cost version

15 more tests (30 in all): the price on seven hand-built lines and the refusal of three histories the tree
cannot hold, the equity table's orientation on a real 169-class rung (AA against 72o above 0.85, AKs against
QQ just under half, the table and its transpose summing to one within the sampling noise), the cost formula
against a hand calculation, a best reply costing nothing and a line nobody takes costing nothing, the cost
scaling with a class's own reach, the cost verdict, a coarse abstraction left unpriced, and a real rung
priced end to end. Eight planted bugs: seven fail tests (the call left out of the pot, the loss branches
swapped, no line weight, the range read from the wrong player, the equity table transposed, the verdict
flipped, an illegal history priced). The eighth, the small blind posted as a full blind, passes, and it is an
equivalent change rather than a hole: every raise is sized from the pot after calling, which is 2bb at the
root either way, and the small blind has always acted by the time anyone faces an all-in. The branch that
returns an uncalled excess cannot fire in this tree, where both stacks start equal.

## Checks

15 tests on hand-built strategies: the neighbour grid (276 pairs on the full 169, each one step and
card for card higher), own reach counting only the player's own actions, the line probability, the
flag and its weight, the inclusive threshold, unreached and uniform entries, a line nobody takes,
the verdict, and a saved pickle read end to end. Five planted bugs (no line weight, verdict
flipped, the wrong player's reach, no uniform skip, a suited step allowed onto a pair) each fail at
least one test. On three real trees (the 70bb self-play rung, v5xRR3's 100bb, v5iT2p60m's 70bb on
the per-street schedule) every preflop entry's width matches the action list the script builds,
4,732, 4,732 and 6,760 entries with no mismatch, so nothing is skipped silently.

## The four-bet-shove calls, priced against real opponents (6 October)

The cost check put the deep exploiter rungs' largest preflop cost at `245`: they call a four-bet shove with AQo,
AJo and ATo almost always, at 22 to 38 percent equity against their own solver's shove range. That range is the
solver's model of a shove, so the same calls were priced against what real opponents shoved
(`~/pokerbot-scratch/fourbet/price_real.py`): every logged hand where the opponent's last preflop action was an
all-in over two or more earlier raises and both hands were shown. We call those shoves almost always and our
call does not depend on their cards, so the shown hands sample the shove range without bias, apart from card
removal.

| | hands | equity a call needed | AQo | AJo | ATo |
|---|---|---|---|---|---|
| four-bet shoves, 40bb and deeper | 11 | 35.8% | 38.3% | 37.6% | 34.5% |
| four-bet shoves, any depth | 41 | 30.9% | 52.5% | 49.7% | 46.0% |

Real bots shove far wider than the solver models (T8s, KJo, JTo beside the aces and kings) and at a better price,
so against them AQo and AJo are calls and ATo is about even. The spot is also rare: 11 deep cases in 576 matches,
Blueprint 7, mr_hide 3, hoops 1. So the station-share recipe is not changed for it. Eleven hands is a loose
estimate, but every row points the same way.

