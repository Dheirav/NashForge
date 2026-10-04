# All-in adjustment for arena bursts (5 October 2026)

## What it does

`scripts/chipzen_decompose.py --allin-adjust` is the cheap half of AIVAT. For every logged hand where the money all
went in before the river and both hands were shown, it replaces our realised net with its expectation over the board
cards still to come: `at_risk * (P(win) - P(lose))`, where `at_risk` is the smaller of the two contributions, because
whatever the covering stack put in beyond it went back uncalled. Ties count as zero, which is the split pot. Every
other hand keeps its realised net. The expectation is over chance alone, so the adjusted mean estimates the same thing
as the raw mean, while it no longer carries the luck of the runout.

The equity is `pokerbot_native.allin_edge(..., exact=True)`, which enumerates every runout: 990 from the flop, 44 from
the turn and all 1,712,304 preflop. Preflop takes about 0.35 s in C++, so nothing is sampled and there is no seed to
state. Contributions come from the action history (a raise's amount is the seat's total for the street, a call's is
the increment), and the board at the all-in is the one on our own decision row for that street. A spot counts only if
the smaller contribution equals the smaller starting stack, the last chip went in before the river and the showdown
lists two hands.

The flag prints each category raw and adjusted side by side, with standard errors and hand counts, and the adjusted
cell says how many of its hands were replaced. A footer per label gives the adjusted hands by street, the raw and
expected chips on them, and the validation count. Without the flag the output is byte-identical to the main tree's
current script on four labels. `--matches-dir` now takes several directories, because a worktree has no logs of its
own.

`hand_nets` in this branch also carries the main tree's uncommitted stack-difference fix (after minus before, from 2
Oct), since the branch was cut before it and the payouts version reads too high.

## How it was validated

- **Tests** (`tests/test_allin_adjust.py`, 5 passed in 2.5 s): a set of sevens against a flush draw on the flop,
  where our 10,000 shove is called for 6,000, matches 6,000 times the edge brute-forced over all 990 runouts through
  the Python evaluator (`score_hand_7_fast`, independent of the native one). A turn spot's expectation equals the mean
  realised net over all 44 rivers exactly. Aces against kings preflop agrees with a seeded 20,000-board Python sample
  to 0.015. A fold, a check-down and a river all-in are left alone. On 400 seeded random flop and turn all-ins, raw and
  adjusted totals agree within four standard errors and the adjusted spread is smaller.
- **Real logs**: the logs carry no final board, but each showdown's `best_hand` lists five cards, and the non-hole ones
  are always board cards (they sat inside the river board on all 3,044 hands where we saw it). That leaves at most 990
  completions per hand, so for each adjusted hand the realised net has to be one this board could have produced. Across
  every logged all-in (836 hands: 556 preflop, 128 flop, 152 turn) all 836 pass, and on the 311 where the revealed cards
  fix the outcome uniquely, the realised net equals it exactly.

## The two bursts

Chips per hand ± standard error (hands) on decision hands. `v5xRR3 purified` is the 20-match burst of 3 October
(07:31 to 08:16 IST); the label also has two single fixtures on 3 and 4 October, which take the raw row to +116 ± 53,
so they were left out.

| category | balanced-next raw | balanced-next adjusted | v5xRR3 purified raw | v5xRR3 purified adjusted |
|---|---|---|---|---|
| all | -19 ± 68 (572) | -17 ± 67 (19 adjusted) | +98 ± 55 (784) | +70 ± 41 (32 adjusted) |
| deep | -50 ± 93 (380) | -49 ± 93 (1 adjusted) | +154 ± 60 (576) | +122 ± 48 (9 adjusted) |
| short | +42 ± 86 (192) | +48 ± 76 (18 adjusted) | -57 ± 123 (208) | -73 ± 77 (23 adjusted) |
| called a preflop jam | -458 ± 1098 (5) | -551 ± 594 (5 adjusted) | +1037 ± 1221 (19) | +670 ± 515 (19 adjusted) |

On the adjusted hands themselves, balanced-next lost 13,009 raw against 11,478 expected (19 hands: 11 preflop, 5 flop,
3 turn), and v5xRR3 purified won 29,575 raw against 7,609 expected (32 hands: 26 preflop, 2 flop, 4 turn).

## What this shows

The 3 October burst ran about 22,000 chips above expectation on its all-ins, almost all on calling preflop jams, so
its +98 is really +70, and the standard error falls from 55 to 41, which is the same as playing about 80 percent more
hands. It is still positive at about 1.7 standard errors, while the preflop-jam row shows the calls were good (+670 ±
515) but not the +1,037 the runouts paid.

The 4 October burst barely moves, and this is the more important finding. Its big losses were not runouts. The three
companion hands that cost 22,897 chips were two river stack-offs (-9,850 and -7,776) and one turn all-in where we were
about 3 percent to win (-5,271 raw, -4,912 adjusted). Of the 21 hands in that burst that moved 4,000 chips or more,
18 were settled on the river with no card left to come, so there is no chance to take the expectation over. Taking
variance out of those hands needs the expensive half of AIVAT, a value estimate for the river decisions and for the
earlier chance cards, which this tool does not attempt. So -19 ± 68 stays about -17 ± 67, and balanced-next is not
resolved by this burst.
