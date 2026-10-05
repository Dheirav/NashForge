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

These are worth reading but are not yet shown to be leaks. A flag is a gap in probability, not in
chips: two hands both near the calling threshold lose almost nothing by mixing the wrong way. The
next step on them is the cost, which is each hand's equity against the shove range at that node
against its pot odds.

## Limits

- Raising one card by a rank is nearly always worth equity against an all-in range, but not always
  by much. Connectors against one-gappers (87s and 97s) are close, so a flag there may be noise
  around a real tie.
- Preflop only, because only there are the classes hands; a postflop bucket mixes strength with
  texture.
- It reads folds facing a shove. Our own shoves, such as v5f's 27 percent T9s and 98 percent jacks,
  are what `scripts/strategy_sweep.py` lists.
- The weighted excess is comparable between two solves of one tree, not across depths, because the
  line probabilities differ.
- The reach weight is the same self-play proxy as the visit counter's. On an exploiter rung trained
  against a scripted opponent, the opponent's line probability in the table is the solver's own
  model of that seat, not the script's.

## Checks

15 tests on hand-built strategies: the neighbour grid (276 pairs on the full 169, each one step and
card for card higher), own reach counting only the player's own actions, the line probability, the
flag and its weight, the inclusive threshold, unreached and uniform entries, a line nobody takes,
the verdict, and a saved pickle read end to end. Five planted bugs (no line weight, verdict
flipped, the wrong player's reach, no uniform skip, a suited step allowed onto a pair) each fail at
least one test. On three real trees (the 70bb self-play rung, v5xRR3's 100bb, v5iT2p60m's 70bb on
the per-street schedule) every preflop entry's width matches the action list the script builds,
4,732, 4,732 and 6,760 entries with no mismatch, so nothing is skipped silently.
