# Solver work, 25 to 28 September 2026

What changed in the solver and its tree in the week after the first exploitability numbers, what each
change was measured with, and what each result decided. Every figure is in `results/` as JSON. Units
are BB/100 unless a line says matches won.

The short version: the leak LBR found is bets the tree does not have, a per-street raise schedule
(T2) closes most of it without costing strength, linear CFR stays, and purification is the first
play-time change that gains across the whole field. The week also showed twice that one instrument
on its own picks the wrong answer.

---

## 1. Where the leak is

On 25 September Local Best Response gave its first positive readings on the current ladder, which
makes them lower bounds on exploitability. v5i at 70bb, 128,000 hands a condition
(`results/cfr/lbr_ladder_2026-09-25/`):

| menu the exploiter bets with | 70bb | 100bb |
|---|---|---|
| our own sizes (half pot, pot, 2x pot) | -15.5 ± 3.9 | -41.7 ± 4.9 |
| LBR's default 11 sizes, 0.25 to 3.5 pot | +30.6 ± 4.0 | +16.2 ± 5.1 |
| sizes between ours (0.33 to 5.33 pot) | +56.5 ± 4.3 | +68.8 ± 5.5 |

Restricted to our sizes the exploiter finds nothing, so every measured leak comes from sizes we do not
have. v5x, the station exploiter, reads three to six times higher (+104.9 and +145.2 at 70bb), which
is the price of exploitation in the currency that matters against an adaptive opponent.

A menu of one size at a time loses at every size (`lbr_sizes_2026-09-26`), so no single missing size
is the problem. The exploiter wins by choosing the size by its hand. The trace
(`lbr_trace_2026-09-26`, `scripts/lbr_trace_report.py`) found two holes, both translation:

- **Overbets.** Every bet above 2x pot is read as 2x pot. Preflop the strategy folds 62% to them, so
  LBR steals with medium hands; on the flop and turn it calls them as if they were 2x.
- **Small re-raises preflop.** Where the taper offers only 2x pot and all-in, a 0.25 or 0.33 pot
  re-raise is read as 2x and folded to 61 to 63% of the time.

## 2. Naming the sizes: a result that did not survive

Commit `3c97f5f` let a raise level name its sizes (`--raise-cap half,pot,jam ...`), which costs
nothing because a tree's size depends on how many sizes a level holds and not which. Against v5i in
duels the named rung was level (-0.1 ± 2.3 against its control), so the commit concluded the sizes do
not matter.

LBR overturned that. The named rung reads +87.9 on the default menu and +172.6 between sizes, against
its control's +16.9 and +56.9 (`lbr_named_2026-09-25`). It gave up 2x pot at the opening raise, which
is exactly the gap the trace found. The duel could not see it because v5i never bets off our tree.
**A duel against a set that plays the same sizes cannot measure a change of sizes.**

## 3. A raise schedule per street

Adding both fixes on every street multiplies the tree by 12. Most of the leak is preflop, where the
tree is small, so a schedule can now differ by street (`StreetSchedule`, read the same way by the
Python and native games, the trainer's `--street-raise-cap`, play_pickles, the replay, LBR and both
bots). An equivalence test drives both implementations through every sequence on three schedules.

| tree | what it adds | size | LBR default menu | LBR between |
|---|---|---|---|---|
| control (taper 4,2,1) | | 11,450,572 | +16.9 | +56.9 |
| T1 | half-pot re-raise, preflop | x1.4 | -3.7 | +30.0 |
| T2 | half-pot re-raise, preflop, flop and turn | 34,473,400 (x3.0) | -26.4 | +14.4 |

(v5i's 70bb recipe, 20M iterations, paired by seed, 16 x 8,000 hands. "Default menu" is LBR's own 11
sizes, 0.25 to 3.5 pot, as in section 1; every later LBR figure uses it or the between menu. T2 minus T1 is -22.7 ± 6.3 on
the default menu and -15.5 ± 5.7 between our sizes.)

T1's first head-to-head read +23.8 ± 2.9, but the control missed 6.2% of its decisions and calls on a
miss, so that number was the miss rule. In the arena player, which translates, it was 49.4 ± 0.7% of
matches. Neither is evidence of a gain; LBR is.

**v5iT2** is v5i with its 50, 70 and 100bb rungs rebuilt on T2 (`ladder169l_v5iT2full`). Against
v5iP (v5i with T1's rungs), paired LBR is lower on every rung and menu by 12 to 32 BB/100, and at 70bb
between our sizes the leak falls from v5i's +56.5 to +16.1. Head to head it is level (49.3 ± 0.7% of
5,000 matches). Against calling bots it is one to two points behind (station 58.2 against 60.2%), which
may be its shorter training (10M warm against 60M). It passed the cross-tree gate at all three depths
and the replay on v5i's match record (no new misses), and won 13 of 20 in its first burst on 28
September (+240 ± 65 chips a hand over 832 decision hands).

## 4. How to train it

**Warm start by action** (`cfr/warm.py`). A warm start used to copy regrets by position, which
misaligns every action after an inserted size. It now maps them by action. On the control rung onto
T1's tree, 1,163,595 entries mapped and none dropped. A warm 10M then plays level with a cold 20M
(-0.7 ± 0.7 head to head), so a new tree costs half the iterations.

**20M against 60M.** The extra 40M changes nothing LBR can see (every difference within its error)
but is about a point stronger head to head (48.9 ± 0.7 for 20M against 60M, matching an earlier 51.1
for v5m against v5h), and it removes rare bad nodes. Trials run at 20M; sets that will play get the
60M polish.

**10M against 20M (5 October).** On a 70bb (4,2,1) six-class self-play rung, 10M is level with 20M on
the cross-tree gate (+0.3 ± 2.5 BB/100) and on paired LBR (+2.8 ± 16.5), so trials on trees of this
size can stop at 10M, and an arena head to head with only that rung swapped agrees (50.1 ± 0.7 of 5,000
matches). The one point the 60M polish bought was on 20-class histogram rungs, while the six-class v5x60
read 49.4, so the polish is a rule for histogram sets. The same night v5xRR3's own 70bb exploiter rung
(station share 0.25) at 10M read 49.3 ± 0.5 against its 20M, purified over 10,000 matches, and level
against the station: trials on exploiter rungs can run at 10M, while a set that plays keeps 20M there
until a sub-point purified gap is ruled out. Bigger trees are different: the cap-2 deep rungs at 20M beat their 10M solves
on the same tree by 3 to 6 BB/100, and cap-2 rungs kept improving to 100M. Details in
`docs/research/2026-10-05-visit-counter.md`.

**Discounted CFR is closed.** A grid on v5i's 70bb recipe, 10M, 60,000 hands on two seeds per pair
(`results/cfr/lbr_grid_2026-09-28/`, head to heads in its `h2h.txt`):

| update rule | against linear 10M | against the 60M reference |
|---|---|---|
| DCFR 1.5, 0, 2 (the paper's) | -22.3 ± 1.5 | -27.8 ± 3.2 |
| DCFR 1.5, 0, 1 | -23.9 ± 2.1 | -27.3 ± 0.8 |
| DCFR 1.5, 0.5, 2 | -140.9 ± 3.2 | -123.8 ± 5.7 |
| DCFR 1.5, 0.5, 1 | -157.0 ± 3.2 | -141.0 ± 1.7 |
| linear, pruning off | -1.1 ± 1.6 | -6.0 ± 0.7 |
| linear, pruning on | | -5.0 ± 2.1 |

A second training seed agrees, and linear stays ahead at 2.5M and 5M too. DCFR also never lets
regret pruning fire (no visits skipped, against about 76 million for linear), so it does not buy
speed either. Pruning itself is a tie in strength and barely faster.

## 5. The instrument that picks the wrong answer

LBR rated the best DCFR arm as less exploitable than linear, by 12.9 ± 6.1 on the default menu and 34.8 ± 6.2
between our sizes, 16 seeds of 16, while it loses 24 BB/100 head to head. It did the same the night before.
LBR is a greedy one-step exploiter and mostly measures what the tree cannot express, so a strategy
that is worse at playing can still look harder to exploit. Section 2 is the mirror image: the duel
rated a leaking tree as level. **A change is judged on the head to head, the field duels and LBR
together, and adopted only when none of them objects.**

## 6. Purification

`cfr/purify.py` plays a cleaner version of a solved strategy (Ganzfried and Sandholm, 2012): the most
probable action everywhere (`all`), only after the flop (`postflop`), or everything under a threshold
dropped (`t10`, `t20`). One function, so the bot that plays and LBR that measures see the same
strategy.

On v5x, 20,000 matches per duel against the same rows as its baselines
(`results/chipzen/purify_v5x_2026-09-28/`, LBR in `results/cfr/lbr_purify_2026-09-28/`):

| opponent | as solved | all |
|---|---|---|
| station | 73.2 | 76.2 |
| nit | 66.4 | 69.7 |
| wsp copy | 65.1 | 68.0 |
| v003 copy | 71.8 | 74.3 |
| wildpassive | 83.1 | 85.5 |
| maniac | 71.8 | 73.8 |
| melly copy | 64.5 | 65.3 |

That is 2.4 points of matches won on average, each ± 0.3. Head to head against v5x as solved it is
50.0 ± 0.7, and LBR at 70bb does not rise (+4.0 ± 4.7 on the default menu, +1.5 ± 7.8 between our sizes). `postflop`
gains about as much in the field but raises LBR by 44.5 ± 6.4, and the thresholds gain less and cost
more, so all three are rejected. What none of these instruments can see is an opponent that learns a
deterministic strategy over a match. At the LLM table, on the deals of a match the LLM had won
against v5x as solved in 56 hands, it lost to purified v5x in 103. One match is mostly cards, so this
shows no sign of a purified set being easier to read, and does not prove it is not.

On v5iT2 the gain is twice as large. Its unpurified control was rerun from the same code, because the
morning baseline came from the per-street branch (it moved by 0.0 to 1.4 points), 10,000 matches per
duel (`results/chipzen/purify_v5iT2_2026-09-28/`):

| opponent | as solved | all |
|---|---|---|
| station | 59.6 | 65.8 |
| wsp copy | 59.6 | 65.7 |
| melly copy | 56.8 | 62.0 |
| v003 copy | 61.1 | 65.5 |
| maniac | 60.7 | 65.0 |

That is 5.2 points on average, each ± 0.5. Here purification also wins head to head, 52.5 ± 0.7 against
v5iT2 as solved, and LBR at 70bb does not rise (+4.1 ± 8.1 on the default menu, +1.3 ± 7.7 between).
The likely reason it gains more is that v5iT2's deep rungs had 10M warm iterations on a tree three
times the size, so their mixes hold more unfinished noise for purification to remove.

## 7. Open

- The 60M polish of v5iT2's deep rungs, then more bursts before it is believed.
- A burst with `--purify all`, and purification measured again after the 60M polish. Whether a
  strong adaptive opponent reads a purified set over a long match is still open.
- The overbet action: the other half of the traced leak, which needs room in the history key.
- Real-time solving on the actual bet size, which is what closes translation leaks for good.
- v5x folds 79% of its opens to a 3x re-raise, and any two cards re-raise at a profit above 62%. A
  read that calls wider moved nothing in the field, so the fix is retraining with a re-raising
  opponent in its mix (`--opponent-mix`); a first try with the maniac in the mix did not fix it.
- Of the reads added for aggressive bots, the over-folder bet lost (wsp copy 65.1 to 54.5% of
  matches) and is withdrawn, and the river bluff-catch is small; both stay off by default.
