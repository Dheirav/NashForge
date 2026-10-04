# LBR probes the all-in-only raise: what changed and how to run it

5 October 2026, branch `lbr-thirdraise` (worktree `~/Code/PokerBot-lbr-thirdraise`). Nothing here
has been run against a real rung yet. Every number below is either from a unit test on a tiny
synthetic game or from earlier LBR logs, and I say which.

## The hole

Our deep rungs use the (4, 2, 1) taper. The first raise of a street can be half pot, pot, 2x pot or
all-in, the second can be 2x pot or all-in, and the third can only be all-in. The live bridge
(`chipzen/bridge.py`, `_as_abstract`) reads any raise at that third level as all-in, because there
is no sized raise to translate it onto. A 0.4 pot third raise therefore gets the strategy's answer
to a shove. If the strategy folds to that shove often, the small raise wins the same folds while
risking a fraction of the stack. If the bot calls and the hand goes on, `_close_street` re-reads
the street with the raise and call collapsed into one call, so later streets are looked up on a
line that never had the raise.

LBR could not see any of this. `_abstract_raises` only offers sizes the tree has at that node.
Where the tree offers only all-in, LBR's choices were fold, call or shove, so the cheap version of
the shove was never tried.

## What changed

**`cfr/lbr.py`**

- `LocalBestResponse(..., offtree_third_raise=(0.4, 0.6, 1.0))`, also on `lbr_value`. At any node
  where the schedule's menu at the current raise depth is all-in only, LBR may also raise those pot
  fractions. On a (4, 2, 1) rung that node is the third raise of a street, while on (4, 3, 2, 1)
  it is the fourth, because that tree still has 2x pot at the third. A probe whose real cost
  would take the whole stack is skipped, because that is the shove LBR already had.
- The bot's reading of a probe comes from the bridge's own functions, called directly and not
  copied. `_as_abstract` gives the perceived action, using the fraction and ceiling the bridge would
  compute from the arena's chip levels. `_close_street` re-reads the street when the next one is
  dealt. The bridge's `Hand` object holds the pseudo all-in record for the whole hand. The only
  part rewritten is the three-line splice at the end of `replay` that applies the edits, and a
  test pins it to `replay` itself.
- The bot answers the way `ChipzenPlayer.decide` looks up: the true history first and, if that
  misses, the collapsed re-read history. LBR's range tracking uses the same lookup, so its
  read of the bot follows the bot's real behaviour.
- Chips are real. The probe moves its true cost (`raise_by_fraction` with the perceived action
  `ALL_IN`), so the pot, the fold payoff, the call price and the showdown all use what was
  actually bet. The pricing in `_candidates` uses the same real-chip state.
- `play(..., paired_seed=N)` gives each hand its own generators, one for cards and one for
  decisions, seeded by `(N, hand, seat)`. Two runs that differ only in the menu then deal the same
  cards and make the same decisions until the first probe, so a hand where no probe was taken
  differs by exactly zero. `LBRResult.values` carries the per-hand results for the difference.
- `_choose` is now `_candidates` (every move with its value) plus an argmax, so a test can check a
  single decision.
- `probe_stats` counts probes made, how the bot answered them, streets collapsed, and lookups
  on the re-read history that hit or missed.

With the option off, the output is identical to before. The test pins the pre-change result on a
fixed seed (mean 8.95, stderr 13.418474805345609) to the last digit.

**`scripts/lbr_ladder.py`**: `--offtree-third-raise F ...` and `--paired`. Paired mode runs probes
off and then on in one process over the same per-hand seeds. It writes both arms, the
difference (with exact sums for pooling), the hands that changed, and `probe_stats`. The trace is
the probe arm's, and probe records carry `"probe": true` and `"depth"`.

**`scripts/lbr_paired_report.py`** pools chunks by condition. It pools the difference from the
per-hand sums, so the standard error is the paired one. It groups by condition name because
every ladder calls its rung `cap2_70bb.pkl`, and grouping by rung merged two solves in the first
version.

**`tools/lbr-thirdraise.sh`** and **`tools/lbr-thirdraise-progress.sh`** are the lane and its
progress reader (see below).

## What it does not model

- **The companion solver and the rules.** The live player tries a companion solver between the
  true and the re-read lookup, and falls back to a rule on a full miss. LBR measures one strategy,
  so a full miss is played uniformly, as LBR has always done. `alt_misses` counts how often that
  happens. If it is large, the number is about uniform play and not about our bot.
- **The river solver and the profile rules** in `decide` are not modelled. That has always been
  true of LBR.
- **A mismatch I found but did not change.** At depths that do have sized raises, LBR translates
  its overbets onto the largest size, while the bridge reads anything at 1.5x the largest size or
  more as a pseudo all-in. So LBR's 2.75 and 3.5 pot bets are heard as 2x pot by LBR's model of
  the bot but as all-in by the real bridge. This predates today's change. Routing those through
  `_as_abstract` too is the obvious next step, but it would change every earlier LBR number, so
  it should be its own option.

## Tests

`tests/test_lbr_thirdraise.py`, 7 tests, 3.7 s, all on a 4-bucket game with a (4, 2, 1) tree and
a synthetic strategy that re-raises 2x over an open, folds to anything read as all-in unless it
holds the top bucket, and otherwise checks or calls:

- off reproduces the pre-change result exactly, and on a one-raise tree with no all-in-only menu
  probes on and off are the same run;
- probes are offered only at the all-in-only node, not one raise earlier and not with the option
  off, and not when the probe would cost the whole stack;
- the same hand through LBR and through `chipzen.bridge.replay` gives the same key (`345`), the
  same history after the call (`3451/`) and the same re-read history (`341/`), and the bot is
  answered from the re-read key when the true one misses;
- chips: the probe puts in 54 against a 400 stack, a fold pays LBR the bot's 30, and a call
  makes it 54 each;
- against the synthetic strategy the best value at the constructed node is higher with probes
  and is a probe, and over 300 paired hands the probe arm wins more while more than 250 hands are
  identical.

`tests/test_lbr.py` still passes (11 tests). Together the two files took 57 s at a 188 MB peak.
The full suite was not run.

## Commands, for after the final

Run from the worktree, because main does not have the probe code. Check memory first:

```bash
free -m      # "available" well over 1,500 MB; the lane also waits for that before each chunk
```

The lane runs three streams at once (v5xRR3 70bb, v5xRR3 100bb, and the (4, 3, 2, 1) 70bb rung),
each with 16 paired chunks of 8,000 hands on seeds 1000k+7, the shape of the 25 Sept lanes:

```bash
cd ~/Code/PokerBot-lbr-thirdraise
nohup tools/lbr-thirdraise.sh > /dev/null 2>&1 &
tools/lbr-thirdraise-progress.sh --watch      # chunks done of 16 per rung, elapsed, ETA from the measured rate
```

It writes to `~/Code/PokerBot/results/cfr/lbr_thirdraise_<date>/`. The (4, 3, 2, 1) rung is
`results/cfr/experiments/hist20_70bb_cap4321_160m.pkl`, the output name in
`~/pokerbot-scratch/cap4321/run.sh`. `lbr_ladder.py` globs `*_70bb.pkl` in a ladder directory and
that file name does not match, so the lane reads it through `ladder169l_v5i_cap4321/cap2_70bb.pkl`,
which links to it. The lane's log line for each stream prints the resolved path, so check it there.

One rung by hand, if you want only one:

```bash
cd ~/Code/PokerBot-lbr-thirdraise
M=~/Code/PokerBot/results/cfr; OUT=$M/lbr_thirdraise_manual; mkdir -p $OUT
for k in $(seq 1 16); do
  venv/bin/python scripts/lbr_ladder.py --ladder $M/ladder169l_v5xRR3 --rungs 70bb --hands 8000 \
    --seed $((1000 * k + 7)) --offtree-third-raise 0.4 0.6 1.0 --paired \
    --trace $OUT/rr3_70bb_trace.jsonl --out $OUT/rr3_70bb_$(printf %02d $k).json
done
# 100bb: --rungs 100bb.  (4,3,2,1): --ladder $M/ladder169l_v5i_cap4321 --rungs 70bb
```

Reading it:

```bash
venv/bin/python scripts/lbr_paired_report.py ~/Code/PokerBot/results/cfr/lbr_thirdraise_*/*_[0-9][0-9].json
grep '"probe": true' <dir>/rr3_70bb_trace.jsonl > /tmp/probes.jsonl
venv/bin/python ~/Code/PokerBot/scripts/lbr_trace_report.py /tmp/probes.jsonl --min 20   # untracked in main, not on this branch
```

The column to read is "on minus off". The two arms' own errors will be about ±4 to 6 BB/100 each at
128,000 hands, but the difference is paired, so it is much tighter than that. Read it only when
the lane has finished. A partial pool is a counter, not a result. A positive difference clear of
zero is a lower bound on what the hole is worth, and a difference near zero only means this
greedy exploiter did not find it. Check `alt_misses` before quoting anything, for the reason
above.

## Time and memory, estimated

**Time.** On 25 Sept, the v5x lanes, which used the same 70bb solve as v5xRR3
(`br25_station_70bb_t421_20m`), took 1.8 to 2.1 minutes per 8,000-hand chunk at 70bb and 100bb,
with four LBR streams running at once (`results/cfr/lbr_ladder_v5x_2026-09-25/*.log`). Rungs of
1.1 to 3.7 million information sets took 1.2 to 2.6 minutes (`lbr_ladder_2026-09-25`,
`lbr_v5iT2full_2026-09-28`), so the cost follows hands more than tree size. A paired chunk plays
each hand twice and probes add a few candidates at rare nodes. I therefore expect about 4 to 5
minutes a chunk, 65 to 85 minutes for 16 chunks, and about the same wall time for all three
streams running in parallel. The (4, 3, 2, 1) stream also loads a 159 MB table first. This is an
estimate from those logs, so plan on the progress reader's rate once a chunk has finished.

**Memory, not measured on a real rung.** The synthetic smoke run peaked at 140 MB with a
50,000-entry table. The flat tables are 24 MB (RR3 70bb), 31 MB (RR3 100bb) and 159 MB
(cap4321), and cap4321's side pickle is a further 137 MB. I would guess 200 to 300 MB per RR3
stream and 450 to 650 MB for cap4321, so 0.9 to 1.3 GB for all three. The lane records each
chunk's real peak in `time.log`, and the progress reader shows it after the first chunk. Use
that, not this guess.
