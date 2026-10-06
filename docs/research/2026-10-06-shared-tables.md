# Histogram rungs with identical tables share one copy

6 October 2026, branch `shared-tables`. A follow-on to the duel fixes of 5 October
(`2026-10-05-duel-fixes.md`), which stopped each duel worker building its own tables. This stops each
rung in one process holding its own copy.

## What was duplicated

A histogram rung carries flop and turn bucket tables: 1,286,792 and 13,960,050 entries, 137 MB of
numpy arrays, which the native module turns into a `BucketTable` set of about 131 MB more. Rungs
fitted from one abstraction carry the same tables, and on disk that is every histogram rung of
v5iT2p60m: its 50, 70 and 100bb rungs give the same full digest of keys and buckets on both streets,
in the full ladder and in the compact one, with the same centroids. So a v5iT2p60m player held three
copies of about 268 MB where one would do.

## The change

`CardAbstraction.native_tables()` in `abstraction/buckets.py` now keys the native set by a digest of
every array in full (keys and buckets, every street, with their shapes), and an abstraction whose
digest is already held takes that set and its arrays instead of building its own. Four choices, each
for a reason:

- **The digest reads every byte**, never a sample. Two tables that differ in one entry would put a
  hand in the wrong bucket and change play with no error. It costs about 0.2 s a rung at load.
- **The arrays are shared as well as the native set**, because they are the other half of the
  memory (137 MB a rung against 131). Sharing them is safe only if nothing writes to them, so the
  shared arrays are made read-only, and a write through one rung now raises instead of reaching
  the others. Nothing in the tree writes to them; `build_tables` and `--drop-hist-tables` replace the
  dict rather than edit it.
- **Each rung keeps a dict of its own** over the shared arrays, so reassigning a street in one rung
  (as `--drop-hist-tables` does) never touches another.
- **The cache is weak**, so a shared set goes when the last rung holding it does. A script that
  loads and drops many rungs in turn, as a sweep does, would otherwise keep every set it ever saw.

The digest is not stored, because a stored digest would go stale the moment `build_tables` rebuilt
the arrays.

## Checks

- **Lookups:** on the three real rungs, 20,000 random flop and turn lookups agree with an unshared
  `BucketTable` built from the pickle's own arrays the old way, and across the three rungs, both
  through the table and through `bucket()`.
- **Play:** the duel traced decision for decision on main and on the branch (v5iT2p60m compact,
  `--deep-primary --purify all`, against the station, 300 arena matches, seed 41, one worker):
  35,100 decisions each, and the traces are byte-identical. The 2,000-match runs at 2, 4 and 6
  workers win 62.9, 61.6 and 62.6 percent on both, which are main's own numbers.
- **Tests:** 12 in `tests/test_shared_tables.py`, with the related files (`test_duel_prebuild.py`,
  `test_histogram.py`, `test_abstraction.py`, `test_native.py`) passing beside them. They cover
  sharing for identical tables; no sharing when the tables differ in the last bucket of a
  200,000-entry street, the first key, one extra entry, or with the streets swapped; each street
  getting its own table; equal values in another dtype sharing; the arrays being read-only and each
  rung's dict its own; the weak cache letting a set go; no tables giving an empty set and no cache
  entry; real fitted tables shared across pickled copies looking up as an unshared table, and
  pickling again; and the duel prebuild building one set for three rungs. Six planted bugs each fail
  at least one test: a digest of the first 1,000 entries, a digest that ignores the buckets, arrays
  left writable, the shared dict handed out, a strong cache, and the duplicates kept.

`tests/test_flat.py` errors in a fresh worktree because `results/cfr/experiments/nolimit_100bb_eq200.pkl`
is untracked; that is the missing file, not this change.

## Memory

One process after building the player and its tables (PSS, MB):

| ladder | main | branch |
|---|---|---|
| v5iT2p60m compact | 1,084 | 588 |
| v5iT2p60m full | 1,421 | 900 |

A 2,000-match duel against the station (`~/pokerbot-scratch/sharedtables/`), summed PSS of the parent
and its workers, as the peak over the run and as the peak once the workers are playing:

| workers | main, peak | main, playing | branch, peak | branch, playing |
|---|---|---|---|---|
| 2 | 1,374 | 1,271 | 1,409 | 775 |
| 4 | 1,376 | 1,376 | 1,385 | 882 |
| 6 | 1,481 | 1,481 | 1,385 | 986 |

So the memory held while the duel plays falls by about 495 MB at every worker count, which is the
536 MB the two duplicate copies came to. The peak does not fall, and the reason is the load: each
compact rung's `.rung.json` carries its tables as JSON (233 MB a rung), and parsing one costs about
as much again for a moment, before any table is built. On the branch the peak is that parse, and it
is the same as on main. The peak matters only when the machine is short at the moment a duel starts.

## What is not done

- **The load peak.** The tables are written into each rung's JSON, three times for v5iT2p60m, and
  parsed three times. Storing them once in an `.npz` beside the compact table (or once per ladder,
  by digest) would cut the load peak and about 460 MB of disk. That is a format change for
  `cfr/pure.py` and the builder, not done here.
- **The live bot.** The current upload set (v5x, six-class) has no histogram tables, so this does
  nothing for it today. A histogram set on the bot would hold one copy instead of three.
