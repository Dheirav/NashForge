# LBR hears its overbets the way the bridge does: what changed and what it is worth

5 October 2026, branch `lbr-overbet` (worktree `~/Code/PokerBot-lbr-overbet`). One small paired run on
v5xRR3 at 70bb, two chunks of 8,000 hands. Everything else here is unit tests on a synthetic game.

## The mismatch

At a raise depth that has sized raises, `cfr/lbr.py` translated LBR's own off-tree sizes through
`abstraction.translation.translate` onto the legal sized raises. Above the largest size that clamps, so
every overbet was heard as 2x pot. The live bridge (`chipzen/bridge.py`, `_as_abstract`) does something
else: a bet of 1.5 times the largest size or more is a pseudo all-in, and so is any bet that costs the
bettor's whole stack. If the bot calls a pseudo all-in and the hand goes on, `_close_street` re-reads the
street. So LBR was scoring the bot's answer at the 2x-pot node, while in play the bot answers at the all-in
node.

One correction to how this was described on the third-raise branch. On our (4, 2, 1) rungs the largest
sized raise is 2x pot at every depth that has one, so the line is 3.0 pot. **A 2.75 pot bet is under it and
the bridge reads it as 2x pot too**, unless it costs the stack. The sizes that actually change are 3.5 in
the default menu and 5.33 in `--between-sizes`, plus any size that is stack-capped. The tests pin 2.75
on both sides of that.

That holds only on a schedule whose largest sized raise is 2x pot, because the line is 1.5 times the
largest size. On `ladder169l_ns` the 70bb rung's schedule is `[[2, 3, 5], [2, 3, 5], [5]]`, whose largest
sized raise is pot, so its pseudo all-in line is 1.5 pot and every size from 1.6 to 2.75 pot is read as
all-in there as well. Which LBR numbers this branch changes therefore depends on the rung's schedule, not
only on the menu.

## What changed

**`cfr/lbr.py`**: `LocalBestResponse(..., bridge_translation=False)`, also on `lbr_value`.

- When on, `_apply_move` reads each of LBR's sized bets through `_bridge_perceive`, which calls the bridge's
  own `_as_abstract` on the hand's bridge record. The record is the same `chipzen.bridge.Hand` the probes
  use, so a called pseudo all-in is re-read by `_close_street` when the next street is dealt, and the bot is
  then asked on the true history first and the re-read one second, as `ChipzenPlayer.decide` does.
- Pricing in `_candidates` uses `_bridge_distribution`, the readings the bridge may give with their
  probabilities. Its all-in readings come from `_as_abstract` itself on a scratch hand, because they are
  deterministic. Otherwise the bridge draws a pseudo-harmonic pair over the schedule's sized raises, and
  that pair is laid out from the same inputs. A test samples `_as_abstract` 2,000 times per size and
  checks the frequencies, so if the bridge changes, pricing and play cannot drift apart silently.
- The fraction the bridge is handed is recomputed from the real chips (`_bridge_view`), as `replay`
  computes it from the arena's levels. That includes the cost's rounding and the one big blind minimum, so
  a few in-range bets are bracketed slightly differently from before as well. That is also what the bridge
  does, which is the point.
- Tree actions are unchanged, and so is the all-in-only node: LBR's sizes still are not offered there. That
  node is the third-raise probes' job (`offtree_third_raise`), and the two options combine.
- `probe_stats` gains `overbet_allins` (read as a pseudo all-in with chips kept) and `capped_allins` (cost
  the stack, a real all-in). `folded` and `called` now count answers to any pseudo all-in, probe or overbet.

**`scripts/lbr_ladder.py`**: `--bridge-translation`. `--paired` now accepts it or `--offtree-third-raise`, and
its off arm drops both, so the difference is what the options are worth together. JSON rows carry
`bridge_translation`. `scripts/lbr_paired_report.py` reads these chunks unchanged; its column headers now
say "arm off" and "arm on", because the report serves both options and here the arms are the old and the
bridge translation.

**`tools/lbr-overbet.sh`** and **`tools/lbr-overbet-progress.sh`**: one stream, chunks in sequence, seeds
1000k+7, waits for 2,500 MB available before each chunk, writes into the worktree's `results/cfr/`.
`LADDER`, `RUNG`, `CHUNKS`, `HANDS`, `SIZES` and `LANE` override the defaults. The lane was exercised end to
end on 30 hands before the real run, which caught `NAME` colliding with the shell's own variable.

## Tests

`tests/test_lbr_overbet.py`, 12 tests, on the third-raise tests' 4-bucket (4, 2, 1) game and their
`ShyOfShoves` strategy (folds to anything read as all-in unless it holds the top bucket, re-raises a
preflop open):

- **off reproduces the old numbers exactly.** Pinned from the code before the change: `--between-sizes`
  menu on a shared generator (27.366666666666667 ± 11.858087818207936), the same on paired seed 21
  (36.016666666666666, sum 2161.0), and the default menu both ways (the third-raise pin, 8.95 ±
  13.418474805345609, and 10.008333333333333 paired).
- **an overbet is heard as the bridge hears it**: 2.75, 3.5 and 5.33 pot, as an open and as a re-raise over a
  pot open. The history LBR builds equals the one `chipzen.bridge.replay` builds from the same chips. With
  the option 3.5 and 5.33 read as all-in and 2.75 as 2x pot; without it all three are 2x pot. The chips are
  identical either way.
- a 2.75 open that costs a 6bb stack is all-in to the bridge and 2x pot to the old translation;
- **the bot answers the bridge's node**: after a 3.5 pot open the strategy is asked at `5` (fold, or call
  with the top bucket) and not at `4` (re-raise); called, the flop is `51/` with re-read line `41/`, both
  equal to `replay`'s;
- the pricing distribution matches sampled `_as_abstract` for every size in both menus, at both depths;
- over 200 paired hands every pseudo all-in is answered, no call collapses more streets than there were
  calls (a called river pseudo all-in collapses none, since nothing follows it), no re-read lookup misses,
  and some hands are left exactly equal.

`tests/test_lbr_overbet.py`, `tests/test_lbr.py` and `tests/test_lbr_thirdraise.py` together: 30 passed in
57 s, 192 MB peak. The full suite was not run.

## The comparison

v5xRR3 70bb (`ladder169l_v5xRR3/cap2_70bb.pkl`, resolving to `br25_station_70bb_t421_20m.pkl`, 390,376
information sets), `--between-sizes`, paired, seeds 1007 and 2007, 8,000 hands each. Each chunk took about
4.5 minutes at a 250 MB peak. Output is in `results/cfr/lbr_overbet_2026-10-05/` in this worktree.

| | BB/100 |
|---|---|
| old translation | +131.8 ± 12.5 |
| bridge translation | +95.7 ± 10.9 |
| **bridge minus old, paired** | **-36.1 ± 9.2** |

By chunk the difference was -29.7 ± 13.1 and -42.6 ± 13.0. 6,568 of the 16,000 hands changed.

This shows the old translation overstated LBR's bound on this rung by about 36 BB/100, roughly a quarter
of it, which is four standard errors from zero. The direction makes sense. Heard as 2x pot, a 5.33 pot bet
was answered by the bot's 2x-pot strategy, which calls and re-raises much more than its all-in strategy,
so LBR was being paid off on a node the bot never reaches in play. Heard as all-in the bot folds 86% of the
time, which wins less than getting called by worse hands. In the bridge arm's trace, 10,750 of LBR's bets
were 5.33 pot read as all-in, with 1,533 calls, and 1,528 of those calls collapsed a street. The other 5
were river calls, which have no next street to re-read. 3,493 lookups went to the
re-read history and 28 missed, so the miss rate after a collapse is under 1% and the number is about the
bot's strategy, not uniform play.

The rung is still clearly exploitable at +95.7, so this does not change what NEXT.md says about v5xRR3's
deep rungs being leaky. It changes how big the bound is. Two caveats. First, this is 16,000 hands, two
chunks, and one rung on one menu; the 100bb rung and the default menu (where 3.5 pot is the affected size)
were not run. Second, the +131.8 here is the paired-seed old arm and is not the same draw as the +99 in
NEXT.md, whose menu and seeds I did not check, so the two should not be differenced.

## What it means for earlier numbers

On (4, 2, 1) rungs, every LBR number whose menu included a size at 3.0 pot or more, or that was
stack-capped often, carries this bias (on a schedule whose largest sized raise is pot, the line is 1.5 pot
instead): the default menu (3.5) and `--between-sizes` (5.33) both do. The defaults are left off so those
numbers stay reproducible. A menu that stops at 2.75 or below is affected only through stack caps and the
chip rounding. Going forward I would run LBR with `--bridge-translation` on, because the whole reason for
LBR here is to measure the bot the arena plays.

To repeat this at more chunks or on 100bb:

```bash
cd ~/Code/PokerBot-lbr-overbet
free -m                                             # the lane waits for 2,500 MB available
CHUNKS=16 RUNG=100bb tools/lbr-overbet.sh results/cfr/lbr_overbet_100bb &
tools/lbr-overbet-progress.sh results/cfr/lbr_overbet_100bb --watch
```
