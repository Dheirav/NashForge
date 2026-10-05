# Fold counts by the size of our bet

Written 5 October 2026 on branch `fold-by-size` (worktree `~/Code/PokerBot-fs`, uncommitted). This is the fix the
caveat in `2026-10-05-posterior-reads.md` asked for: the size-aware bluff rule compared one overall fold rate with
each bet size's break-even, and every bot folds more to bigger bets. Nothing here touched the platform. Every number
comes from the scout cache and our match logs in the main tree, read through `scripts/fold_by_size_eval.py`
(65 seconds for 2,693 cached matches; the tables below were re-run on the cache as it stood on the evening of 5
October, after the review's fixes).

## 1. The bins

A bet's size is **what it raises by, as a share of the pot after the call**. Into a check that is the plain bet over
the pot. Facing a bet it is the raise over the call, measured against the pot the call makes. This is the engine's
own definition and the one `to_chipzen` sizes by, so the tree's half, pot and 2x land in their own bins whatever
they face. Measured against the pot before the bet, a half-pot raise over a half-pot bet puts in a pot's worth of
chips and would be binned as a pot bet, which is the wrong price to read it at.

| bin | size | why the edge is there |
|---|---|---|
| small | under 0.4 | min-bets and probes, which bots fold to least |
| half | 0.4 to 0.75 | the tree's 0.5, with room for min_raise lifting a small half-pot bet |
| pot | 0.75 to 1.25 | the tree's 1.0 |
| 2x | 1.25 to 2.5 | the tree's 2.0 |
| jam | over 2.5 | at our depths nearly always an all-in |

A shove over a short stack is binned by **what the opponent can be made to call**, not by its nominal size. The
arena sends our shove as our whole stack, but a bettor covering a short opponent gets only the opponent's last
chips called and the rest comes back, so `observe` caps the bet at the opponent's chips, as the player's
`bluff_fraction` and `bluff_break_even` already did. Before the review's fix `observe` used the nominal size, so a
shove of 9,800 over a 700 stack into 400 was counted as a jam while the rule priced the same bet as 2x. The
reviewer found 606 such answers in our logs, 250 of them in a different bin.

Each bin is kept twice, **preflop and postflop** (`pre:half`, `post:pot`, and so on). An open is a half-pot or
pot raise, and a bot can call opens and fold after the flop: Fold-ver-3 folds 2 to 3 percent of opens and 59 to 94
percent of postflop bets. Pooled, the open's calls would set the half-pot bluff's price on the river.

## 2. Method

**Our logs** (`Profiles.observe`). A raise's amount in our logs is the seat's total for the street and a call's is
the increment, the same thing `chipzen_decompose.contributions` found on 2 Oct. I checked it again on 4,760 hands
that ended in a fold: the loser's stack drop matches the street-total reading in all of them and the increment
reading in only 3,935. So `observe` keeps the pot from earlier streets and each seat's total on this one, and at
our raise to L it sizes `(L - their total) / (pot + both totals + the call)`. When the opponent answers that raise,
its fold, call or raise goes into `row["by_size"][key]` as well as the overall count. The sized answers are the
overall answers split, so they always sum to `bets_faced`. To cap a shove at what they can call, `observe` needs each
seat's chips at the start of the hand, which the round result does not carry. It rebuilds them from the closing
stacks: what a seat ended with, less its payout, plus what it put in. On our logs that matches the `round_start`
stacks on 58,798 of 58,800 seat-hands. A seat that won with no payout on record is left out rather than guessed,
and a bet is left uncapped unless every other seat's start is known.

**The scout** (`chipzen_scout.profile`). The platform's hand records are different: a raise's amount there is the
chips it adds. Of 2,983 cached hands with a raise that reached showdown, the increment reading gives the recorded
pot in 2,642 and the street-total reading in 892, of which 891 are hands where the two readings agree (the other 340
match neither, which is chips returned uncalled after an all-in). The scout's existing `pot += amount` is therefore right, and it now also keeps
each seat's street total, so an opponent's raise is sized the same way and the scouted bot's answer is counted in
the same bins. One test feeds the same hand to both, in each source's own format, and requires the same counts.

The scout's sizing assumes one other seat: it sizes a raise against the scouted seat's street total, which is the
wrong call in a three-way hand. The few cached matches with a seat past 1 (multi-table tournament starts, 11 of
2,204 when the reviewer counted) are now **skipped whole** in `chipzen_scout.profile`, as
`copy_validate.load_matches` already skipped them. I chose skipping over sizing the raise over the biggest bet
because every other count there is heads-up shaped too (the U/T letters, three-bet chances, showdowns), so a correct
size alone would still leave the match misread. `fold_by_size_eval.py` reads through `load_matches`, so its numbers
never included those matches.

**Seeding and rebuild.** `chipzen_scout.seed_row` builds the `opponents.json` row, `by_size` included, with the
same counts again as its `scout_base`. `Profiles.rebuild` already starts from a deep copy of the base, so the sized
counts are added to once per start, like everything else (the 4 Oct double-count test now checks them too).

**The read** (`Profiles.fold_at`, `Profiles.fold_upper_at`). `fold_at(name, fraction, preflop)` is the bin's point
rate; `fold_upper_at` is its posterior upper bound, with the prior fitted per bin across the file exactly like the
other rates (each bin is a rate in `RATES`, `fold_at:post:half` and so on). A bin with fewer than `SIZE_MIN = 40`
answers falls back to the overall bound. The fallback matters because a thin bin's posterior is mostly the field's
rate at that size: a station with five pot-sized bets on file would be read near the field's half-pot-or-better and
have its bluffs released on the prior alone. Forty is the same floor the overall read uses. `fold_upper_at` returns
None wherever `fold_floor_upper` does, so a bin can never fire a read that the overall count would not.

**The within-match correlation per bin**, measured the way the posterior note measured the others:

| bin | bots | pooled rho | median rho | answers per match |
|---|---|---|---|---|
| pre:small | 11 | 0.010 | -0.021 | 2.6 |
| pre:half | 24 | 0.035 | 0.044 | 11.1 |
| pre:pot | 29 | 0.032 | 0.014 | 9.1 |
| pre:2x | 20 | 0.079 | 0.091 | 3.7 |
| pre:jam | 13 | 0.220 | 0.153 | 5.4 |
| post:small | 25 | -0.010 | -0.006 | 4.7 |
| post:half | 29 | 0.016 | 0.010 | 12.3 |
| post:pot | 22 | 0.053 | 0.031 | 4.4 |
| post:2x | 13 | -0.010 | 0.024 | 4.3 |
| post:jam | 6 | 0.048 | 0.310 | 1.5 |

The code keeps the values measured earlier on 5 October (pre:half 0.034, pre:pot 0.034, pre:2x 0.088, post:half
0.017, post:pot 0.044), which today's cache moves by at most 0.01. Those five bins have at least 20 bots and a
positive estimate; the rest take fold-to-bet's 0.035. For the thin bins with an estimate near zero that is a wider
bound than their own, but **not for pre:jam**, which is measured at 0.22 on 13 bots: 0.035 there is a narrower bound
than the data supports. It matters less than it sounds, because the one decision that bin drives (mr_hide's preflop
shove, section 4) has an upper bound of 0.995 under either value. The other bins run 4 to 12 answers a match, so
their design effects are 1.1 to 1.3 and the correction is small.

**The player.** Under `--posterior-reads --size-aware-bluffs`, `_bluff_folds_too_rarely` now sizes the raise it is
about to withhold (`bluff_fraction`, the same chips `bluff_break_even` prices, so the bin and the break-even always
describe the same bet), reads `fold_upper_at` for that bin on the decision's street, and withholds only when the
bound is under the break-even. `never_folds` is still the gate, on the overall rate.

## 3. The spread, per bot

Fold rate (answers) to bets of each size. Scout cache: the scouted bot facing its other opponents' bets since its
cut-off, with our matches left out so the two tables are independent. A `*` marks a half-pot bin folding less than
the bot's overall rate, from at least 40 answers.

**Scout cache**

| bot | overall | post small | post half | post pot | post 2x | post jam | pre half | pre pot |
|---|---|---|---|---|---|---|---|---|
| hoops | 0.377 (4322) | 0.13 (569) | 0.49 (996) | 0.51 (229) | 0.63 (218) | 0.49 (69) | 0.08 (524) | 0.29 (918) |
| mr_hide | 0.292 (7099) | 0.09 (894) | 0.17 (1915)* | 0.31 (411) | 0.40 (338) | 0.52 (165) | 0.08 (787) | 0.06 (995) |
| PoetAndCoder | 0.227 (5323) | 0.12 (315) | 0.30 (2080) | 0.38 (478) | 0.45 (94) | 0.57 (30) | 0.01 (773) | 0.10 (1061) |
| Blueprint | 0.529 (6089) | 0.37 (65) | 0.45 (2729)* | 0.52 (598) | 0.56 (18) | 0.25 (8) | 0.61 (471) | 0.63 (2027) |
| wsp | 0.505 (7165) | 0.55 (534) | 0.65 (2698) | 0.67 (433) | 0.57 (142) | 0.68 (38) | 0.17 (1069) | 0.36 (1614) |
| Fold-ver-3 | 0.350 (7303) | 0.48 (623) | 0.59 (2321) | 0.71 (433) | 0.81 (192) | 0.92 (25) | 0.03 (1814) | 0.03 (1283) |
| r0ckGarden | 0.540 (4547) | 0.02 (331) | 0.21 (1005)* | 0.25 (193) | 0.34 (132) | 0.33 (67) | 0.64 (703) | 0.73 (1106) |
| melly | 0.645 (2943) | 0.22 (54) | 0.62 (964)* | 0.72 (286) | 0.84 (110) | 0.40 (5) | 0.59 (764) | 0.68 (502) |

**Our logs** (the opponent facing our bets)

| bot | overall | post small | post half | post pot | post 2x | post jam | pre half | pre pot |
|---|---|---|---|---|---|---|---|---|
| hoops | 0.344 (2143) | 0.14 (14) | 0.37 (777) | 0.56 (208) | 0.61 (103) | 0.52 (25) | 0.06 (429) | 0.30 (376) |
| mr_hide | 0.189 (2375) | 0.00 (29) | 0.14 (969)* | 0.34 (325) | 0.37 (135) | 0.68 (28) | 0.05 (373) | 0.07 (298) |
| PoetAndCoder | 0.308 (52) | 0.00 (1) | 0.45 (20) | 0.50 (4) | 1.00 (1) | 0.33 (3) | 0.00 (13) | 0.25 (4) |
| Blueprint | 0.569 (3414) | 0.00 (3) | 0.47 (1307)* | 0.49 (201) | 0.48 (42) | 0.81 (123) | 0.55 (976) | 0.72 (402) |
| wsp | 0.587 (734) | 0.40 (15) | 0.78 (323) | 0.84 (64) | 0.75 (16) | 0.75 (12) | 0.17 (184) | 0.51 (53) |
| Fold-ver-3 | 0.445 (146) | 1.00 (2) | 0.51 (45) | 0.70 (20) | 0.83 (6) | - | 0.08 (26) | 0.24 (29) |
| r0ckGarden | 0.513 (3052) | 0.04 (28) | 0.13 (769)* | 0.28 (272) | 0.34 (97) | 0.58 (26) | 0.63 (857) | 0.77 (690) |
| melly | 0.700 (50) | - | 0.78 (23) | 1.00 (2) | - | 0.33 (3) | 0.63 (19) | 0.00 (1) |

What this shows:

- **Folds rise with size postflop on every bot with the samples to show it**, while preflop is a different animal:
  hoops folds 8 percent to a half-pot open and 49 percent to a half-pot bet after the flop. This is why the phases
  are kept apart.
- **The overall rate is mostly a preflop number** for the bots that fold their blinds. r0ckGarden folds 54 percent
  overall but 2 to 34 percent of postflop bets, because 64 to 73 percent of opens are folded. Fold-ver-3 is the
  mirror: 35 percent overall, 59 to 92 percent of half-pot and bigger bets after the flop, 3 percent of opens.
- **Half-pot bins under the overall rate** (where the old rule's overall rate overstated folds to half-pot bets):
  mr_hide (0.17 against 0.29, and 0.14 against 0.19 in our logs), r0ckGarden (0.21 against 0.54), Blueprint (0.45
  against 0.53) and melly (0.62 against 0.645, which is within noise). Of these, only mr_hide is a `never_folds` bot,
  and there the old rule was already right to withhold: its overall bound of 0.28 was under the third a half-pot
  bluff needs, and the bin says the same more strongly (0.17). On r0ckGarden and Blueprint no bluff is withheld at
  all, because `never_folds` reads the overall rate and they fold too often overall to be called stations.
- **hoops folds less to our half-pot bets than to other bots'** (0.37 against 0.49), and more to our pot bets (0.56
  against 0.51). The posterior reads the merged row.

The posterior note's hoops figures (44 percent to half-pot, 57 to pot) were first bets on a street only, with a
0.4 to 0.6 half-pot band. These bins also hold raises over a bet and run to 0.75, so they differ a little.

## 4. What the rule decides now

On a clean file built the way `~/pokerbot-scratch/profiles-clean/build.py` builds one (scout counts with our matches
left out, through `seed_row`, then our logs once), under posteriors, for each tree size into a check. W is
withheld, r is released; "was" is the overall bound, "now" is the bin's.

| bot | never folds | overall upper | half bin upper | pot bin upper | 2x bin upper | half was / now | pot was / now | 2x was / now |
|---|---|---|---|---|---|---|---|---|
| hoops | yes | 0.379 | 0.456 | 0.571 | 0.664 | r / r | **W / r** | W / W |
| mr_hide | yes | 0.277 | 0.172 | 0.354 | 0.430 | W / W | W / W | W / W |
| PoetAndCoder | yes | 0.239 | 0.318 | 0.417 | 0.542 | W / W | W / W | W / W |
| Fold-ver-3 | yes | 0.367 | 0.609 | 0.745 | 0.839 | r / r | **W / r** | **W / r** |
| Blueprint, wsp, r0ckGarden, melly | no | | | | | r / r | r / r | r / r |

Preflop, on an open from the small blind at 100bb, priced by the player's own `bluff_break_even` (a jam there puts
in 9,950 to win 150, so it needs 0.985 folds):

| bot | jam bin folds / answers | jam bin upper | half / pot / 2x opens | jam was / now |
|---|---|---|---|---|
| hoops | 288 / 433 | 0.702 | W / W, W / W, W / W | W / W |
| mr_hide | 1,148 / 1,158 | 0.995 | W / W, W / W, W / W | **W / r** |
| PoetAndCoder | 82 / 141 | 0.651 | W / W, W / W, W / W | W / W |
| Fold-ver-3 | 133 / 142 | 0.963 | W / W, W / W, W / W | W / W |

So on the current cache the bins change **four decisions**, all from withheld to released: hoops's pot bluffs and
Fold-ver-3's pot and 2x bluffs after the flop, and **mr_hide's preflop shove**, which it folds to 1,148 times in
1,158. This note first said four postflop changes and "preflop, nothing changes", and both were wrong. Before the
observe fix the hoops 2x bound read 0.670 against the 0.667 it needs, which released its 2x bluffs as a fifth change
(the reviewer's count). Capping our shoves at what hoops could call moved some of its answers out of the postflop
jam bin (33 to 25 in our logs) into smaller ones, and the 2x bound is now 0.664, under the need, so its 2x bluffs
stay withheld. A bound
within 0.003 of its need is not a stable verdict either way; a few more matches could flip it back. Nothing is newly
withheld, because the one bot whose half-pot bin is under its overall rate (mr_hide) was already withheld at every
postflop size. PoetAndCoder's half-pot bin sits at 0.318 against the 0.333 it needs, which is close enough that a
few hundred more answers could flip it.

Read the hoops line with care. The overall-rate version of this rule released hoops's half-pot bluffs and cost 1.2
points on the hoops copy, so releasing its pot bluffs as well is not obviously a gain. The break-even assumes a
called bluff loses its bet and nothing more, while the copy loses later streets too, and the hoops pot bin is only
seven points over its break-even (0.533 point, 0.571 bound, against 0.50). The copy A/B is what settles it.

Read the mr_hide line with care too. A preflop jam that wins 150 when it works and risks 9,950 when it does not is a
bet on the 1 percent the bot calls with, so the release is only as good as the bound, and the bound is only as good
as the jams it counts. The bin pools the scout and our logs, so it counts other bots' shoves at whatever depth they
were made, not only ours at 100bb. Every other open size stays withheld preflop: the stations fold 2 to 9 percent of half-pot
opens and at most 32 percent of pot opens (the bound), under what an open needs. `fold_by_size_eval.py` now prints
this preflop table as well.

## 5. Tests

`tests/test_fold_by_size.py`, 12 tests:

- the tree's sizes land inside their own bins, and the clamped sizes stay inside them;
- `observe` on a hand with an open, a three-bet, a four-bet, a flop bet, a check-raise and a re-raise, in our logs'
  street-total format: the four-bet is a pot raise and the flop re-raise a pot raise only because the pot carries
  the 3,600 from preflop (forgetting it reads 1.33, a 2x bet);
- the scout on the same hand in the platform's chips-added format, from the other seat, gives the same counts, and
  `seed_row` gives the base its own copy, so a live count cannot move it;
- the scout sizes a 2x bet and a shove into a check;
- three rebuilds in a row add the sized live answers once, and the base keeps the scout's counts;
- `fold_at` reads the bin at 40 answers and falls back to the overall rate at 39; `fold_upper_at` falls back to the
  overall bound on a thin bin, is the bin's bound on a full one, and is None under the overall minimum; each bin has
  its own prior;
- the rule: against a 36 percent folder with no bins, a half-pot bluff goes and a pot bluff is withheld (the old
  behaviour, which the fallback keeps); with bins of 44 and 57 percent both go, and the 2x, with no bin, is still
  withheld on the overall rate; with a half-pot bin of 30 percent the half-pot bluff is withheld, and so is a pot
  bluff into a 45 percent pot bin, while a 57 percent pot bin releases it; a preflop bluff reads the preflop bin,
  not the postflop one.

The brief asked for a test that "withholds a pot bluff and releases a half-pot one when the bins say 44 / 57"
and "withholds both if the half-pot bin folds 30". With a 57 percent pot bin the pot bluff is released, since 57 is
over the half it needs, and a 30 percent half-pot bin withholds the half-pot bluff but not a pot bluff the 57
percent bin pays for. So the tests pin the arithmetic as it is: the 44 / 57 split releases both, withholding the pot
bluff is what the overall rate did, and withholding both needs the pot bin under a half too.

Also changed: `tests/test_chipzen_opponents.py` (the 4 Oct double-count test also carries and checks `by_size`) and
`tests/test_chipzen_player.py` (a counted row now has `by_size`).

Run: `tests/test_fold_by_size.py tests/test_chipzen_opponents.py tests/test_chipzen_player.py
tests/test_posterior_reads.py tests/test_opponent_brief.py tests/test_copy_validate.py`, **100 passed in 4.3
seconds**. The full suite was not run.

After the review's fixes, `tests/test_review_fold_by_size.py` (30 tests, no xfail left) joins them: the review file
and the first five above, 118 passed in 1.6 seconds, and `tests/test_opponent_brief.py tests/test_copy_validate.py`
12 passed. `test_fold_by_size.py`'s rebuild test needed stacks that agree with its hand (the shove to 19,800 needs
30,000 deep), because `observe` now reads the closing stacks; its expected counts are unchanged. The review's
three-way scout test asserts the skip, not a size.

## 6. What you need to run next

Nothing here runs on the platform, and the live set is untouched: the rule only acts under
`--posterior-reads --size-aware-bluffs`, which nothing plays yet.

1. **Merge first.** The scout writes into its own tree's `results/chipzen/` (`opponents.json`, and the `scout/`
   cache it reads from). The worktree has neither, so a scout run from `~/Code/PokerBot-fs` would download every
   match again into the worktree. Merge `fold-by-size`, then run from `~/Code/PokerBot`.
2. **The re-scout**, paced, from the main tree:

       venv/bin/python scripts/chipzen_scout.py --names hoops mr_hide PoetAndCoder Blueprint wsp Fold-ver-3 \
           r0ckGarden melly --seed-profiles --reseed --pace 1.5

   `--pace 1.5` keeps under the RATE_001 limit (28 Sept: 227 refused back to back). The cached matches cost
   nothing, so only matches since the last scout are fetched. Each seeded row now carries `by_size` and `matches`,
   and `scout.md` gets a line per bot with its postflop folds by size.
3. **The clean-profile rebuild**, `~/pokerbot-scratch/profiles-clean/build.py <out dir>`. It calls
   `chipzen_scout.profile`, so it computes the sized counts, **but it does not carry them**: it builds its `base`
   dict from a fixed list of keys, and `by_size` is not in the list. It needs one change before it is run, which I
   have not made since the scratch tree is yours: replace the `base = {...}` literal, the `json.loads` line after
   it and the `clean[name] = ...` line with `clean[name] = sc.seed_row(r)`, or add
   `"by_size": r["by_size"], "matches": r["matches"]` to the literal. `seed_row` is the better fix, because it also
   carries `matches` for the posterior's clustering correction, and a count added to the scout later then cannot be
   left out again. It also
   imports from `~/Code/PokerBot`, so it reads the new `profile()` only after the merge.

A caution on step 2: `--seed-profiles` seeds from every scouted match, ours included, and `rebuild` then adds our
logs on top, so our own matches against a bot are counted twice in a seeded row. `build.py` avoids this by leaving
out matches against NashForge. That predates this branch and applies to every count, not only the sized ones, so the
clean rebuild is the file to play from.

After that, the measurement: a copy A/B on the hoops and Fold-ver-3 copies, `--posterior-reads --size-aware-bluffs`
in one arm against `--posterior-reads` alone, 10,000 to 20,000 matches each, then the cross-tree gate and bursts read
decomposed. Reproduce this note with `venv/bin/python scripts/fold_by_size_eval.py`.

## 7. Left open

- `never_folds`, the gate, still reads the overall rate. r0ckGarden is a postflop station (2 to 35 percent) that it
  never flags, because blind folds lift its overall rate to 54 percent, while Fold-ver-3 is flagged on its preflop
  calls although it folds postflop. Gating on the postflop bins would fix both, but it adds a read rather than
  refining one, so it should be a separate switch and its own measurement.
- The fallback is all or nothing at 40 answers. A prior centred on the bot's own overall rate, shifted by the field's
  gap between that bin and the overall rate, would use thin bins too. It is not worth the complexity until a bot we
  play has bins that thin.
