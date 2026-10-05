# Two duel fixes: shared bucket tables, and a compact ladder the runner reads correctly

5 October 2026, branch `duel-fixes`. Both came out of building compact ladders for duels the same day
(`~/pokerbot-scratch/compact-ladders/report.md`, findings 1 and 3). Neither changes how a bot plays.

## A. The histogram tables are built once, before the fork

`scripts/chipzen_duel.py` forks its workers so they share the players' tables copy-on-write. A
histogram rung's native bucket tables were the exception, because `native_tables()` builds them
lazily on the first postflop decision, which happens inside each worker. So every worker built its
own copy, about 450 MB for v5iT2p60m.

Now both forking paths (arena matches and duplicate deals) go through `_fork_pool`, which hands the
players over and calls `prebuild_tables` in the parent first. One worker does not fork and does not
prebuild, so a single-worker run is the old path exactly.

Measured on v5iT2p60m's compact ladder against the station, 2,000 arena matches, seed 7, peak PSS of
the parent and its workers (`~/pokerbot-scratch/dfix/`):

| workers | main | this branch |
|---|---|---|
| 2 | 1,687 MB | 1,396 MB |
| 4 | 2,635 MB (5 Oct) | 1,424 MB |
| 6 | 3,527 MB (5 Oct) | 1,492 MB |

The 2-worker pair was run here back to back. The 4 and 6-worker figures for main are the
5 October measurements, not re-run, because main at 6 workers needs most of the free memory. At
2 workers the two runs are identical: 62.9 percent, 235,100 decisions and 597 misses for our side,
and every counter equal. So memory no longer grows with the worker count, and a histogram duel can
run at 4 to 6 workers where it ran at 2.

## B. The builder writes the links the runner needs, and checks the set

`container/build_ladder.py` writes only the rungs that play. Under `--deep-primary` the runner swaps a
cap2 rung in only at a depth where the folder holds a `nolimit_<d>bb` entry, so a compact folder on
its own played the shipped one-raise solver at every depth and dropped every cap2 rung, with no
error. On 5 October the links were added by hand.

The builder now writes, for every cap2 rung, a relative link `nolimit_<d>bb.pkl` to the source's own
one-raise rung (and its flat pair when the source has one), and it ends by checking that the runner
picks the same rungs, by name, from the new folder as from the source. A depth whose one-raise rung
the source does not have, or a real file where a link should go, stops the build.

The upload had to change with it. `container/package.py` copied the ladder with `copytree`, which
follows links, so a link would have put the source's full pickle or flat table into a zip with a
250 MB limit. `copy_ladder` now leaves out every link and every pickle. The image lists `*.rung.json`
only, so it never read them anyway.

Checked on a real build: v5xRR3 rebuilt into a fresh folder in 31 s, the same-set check passed with
21 links, and every `.compact.npz` and `.rung.json` is byte-identical to the hand-linked folder that was
verified decision for decision on 5 October. The upload copy of that folder is 23 MB with no links;
following the links, the folder is 111 MB.

## Tests

12 tests: `tests/test_duel_prebuild.py` (5) and `tests/test_build_ladder_links.py` (7). They cover the
prebuild skipping scripted players and rungs without tables, forked workers inheriting the tables
built in the parent, both forking paths prebuilding, one worker not forking, the original bug
reproduced (no links, the runner drops the cap2 rungs), relative links and flat pairs, a rebuild
replacing a stale link, a real file left untouched, a missing source rung, a missing built rung, and
the upload leaving the links out. Seven planted bugs each fail at least one test.

The duel tests need the native module (the scripted opponents use it); in a fresh worktree, link
main's `pokerbot_native*.so` in.
