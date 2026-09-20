# What to do next

One page, kept current. [`BACKLOG.md`](BACKLOG.md) holds the reasoning and everything closed;
[`docs/training-plan.md`](docs/training-plan.md) holds the full phase plan and its results. This
file is only the next thing to do.

**Last updated:** 20 September 2026, 19:35 IST · 343 tests (~7m with the machine shared; collection ~3m24s)

---

## Where this stands

| | | |
|---|---|---|
| CFR | measured | Validated against Kuhn's −1/18 and exact Leduc exploitability. Produced the abstraction crossover, +0.916 ± 0.118 chips/hand at the 2560s budget |
| Evolutionary search | measured | Loses to the solver by 211.8 BB/100. Fifty generations are worth +43.9 ± 20 — small, separated, and invisible against a weaker opponent |
| PPO | measured | Loses to the solver by about 75 BB/100 at every rung. Flat: more training does not close it |

All three are measured, and **Phase 4 — the comparison the project's title promises — is done**
(`results/comparison/phase4_native.json`). One panel, 40,000 hands, a hands axis, in BB/100:

| family | hands | vs random | vs always-call | vs CFR |
|---|---|---|---|---|
| CFR (the solver, 250k) | — | +258.7 | +647.3 | — |
| evolution, 50 generations | 36,000,000 | +202.7 | −0.2 | **−211.8** |
| PPO | 500,000 | +191.2 | +372.6 | **−84.6** |
| PPO | 2,000,000 | +137.2 | +373.2 | **−72.5** |
| PPO | 8,000,000 | +226.8 | +329.1 | **−74.9** |

Every row on one panel, 11 September, measured against a solver trained by the **C++ core**
(`results/comparison/phase4_native.json`). CFR lookup miss rate 0.0% throughout.

**This table is a re-measurement and every conclusion survived it.** The native solver bucketing
is seeded from the cards rather than from Python's tuple hash, so it is a genuinely independent
implementation with different draws, in another language. Against the previous panel the same
figures were +245.9 / +603.4 for the solver, −200.9 for evolution and −79.7 / −73.5 / −72.0 for
PPO. **Every one moved by less than its own interval**, and the columns that structurally cannot
move — PPO and evolution against random and always-call, which never touch the solver — are
identical to the decimal. See `docs/retrain-plan.md`.

**Both learned families lose to the solver.** PPO by about 75 BB/100, evolutionary search by
about 200. Neither ever beat it: the earlier reading came from a panel whose CFR agent had
**4,000 iterations — about two minutes of training**.

**Evolutionary search still spent 36,000,000 hands to PPO's 500,000** — seventy-two times as many
— and is 127 BB/100 further behind. That comparison survives both the panel change and the
re-measurement on an independent solver, and is the firm result.

### Three claims the panel upgrade overturned

Figures in this section are the **v2 (Python-trained) panel's**, kept as the record of what that
upgrade changed. The live table above is the native panel's re-measurement.

| claim | measured against the 4k panel | against the 250k panel |
|---|---|---|
| PPO beats the solver at 8M | +36.4 ± 13 | **−72.0**, t = −10 |
| More training helps | ladder rises | **flat**: −79.7, −73.5, −72.0 |
| Evolution learned nothing transferable | +33.8 ± 37, no change | **+50.0 ± 20, improved** |

None were bad measurements. They were correct readings against an opponent too weak to
distinguish anything, and the two errors point in **opposite directions** for one reason: an
under-trained solver is far more exploitative than a converged one. The 4k agent beat random by
+383.6 and always-call by +719.6, where the 250k agent manages +245.9 and +603.4. That
exploitation flattered PPO's relative position and buried evolution's improvement underneath it.

It is the same equilibrium-versus-exploitation trade this project has now measured four times,
and the fourth occasion on which **changing the instrument overturned a finding rather than new
data doing it**.

**On evolution's fitness.** The finding that its ranking signal cannot be selected on stands —
repeatability is r = +0.12 at the real budget, and shared cards do not help. But "fifty
generations were largely drift" was too strong: selection on that weak signal still produced
**+43.9 ± 20 BB/100**, measurable once the opponent stopped drowning it out. A noisy ranking and a
real improvement are compatible; the earlier phrasing denied the second.

---

## Now — the next thing to do

**The list, Sunday 20 September, 16:50 IST.** Semi-final tonight 23:30 against v003 (v7b,
timer armed and dry-run); the final about 02:30 Monday against Blueprint or Fold-ver-3; season
7 opens Tuesday 05:30, entries close Monday 23:59 UTC.

*Today, bot off until 23:15:* done: the instrument tests, the reads-on duel, the histogram
abstraction, the council's fixes, the corrected-dealer re-runs, **the commit** (`328bf66`;
the 2.2 GB of real solves the ladders link to are now gitignored), lane T3 (below), and
**Monday's burst script written and dry-run** (`~/pokerbot-scratch/chipzen/burst.sh`,
dry-run passed 19:28 with the bot connected inbound-only) but **not armed: Monday's timers
are set only when asked** (19:50, on instruction). It plays the set named in
`~/pokerbot-scratch/chipzen/burst_set`, currently v5f; to burst v5d instead, change that
file's three lines (dir `ladder169l_v5c`, the v5d label, `--deep-primary --stack-cap`). To
arm: `nohup ~/pokerbot-scratch/chipzen/burst.sh "2026-09-21 05:29" > ~/pokerbot-scratch/chipzen/burst_mon.log 2>&1 &`.
Left: scout whoever is registered for season 7.

**Sunday 20 September, 19:35 IST: the tapered third raise (v5f) ties v5d.** Lane T3's three
deep rungs (`(4, 2, 1)`: four sizes for the open, 2×pot or all-in for the re-raise, all-in for
the third raise; 20M warm, 2.7 to 3.2 h each on 2 threads) assembled as `ladder169l_v5f`.
Against v5d on the corrected dealer: **50.0 ± 2.0% of 600 arena matches** and +6.2 ± 8.9
chips a hand at 100bb. What differs is the rule hands: v5d fell to the rule 339 times against
v5f (every 4-bet shove is off its tree) and v5f 114 times against v5d, and it made no
difference to the score. Gates: cross-tree against the one-raise rung +104, +135 and +167
BB/100 at 50/70/100bb, three seeds; the (2, 2) rung on the same corrected gate reads +197 at
100bb, with the one-raise side missing 26% of its decisions (11% against v5f). **The
cross-tree gate at deep stacks is saturated by the one-raise side's forced calls on a miss
and no longer reads convergence**; it still says neither set loses to the one-raise
strategy, which is all a go-live gate needs. Replay on the v5d record: 103 new-set misses
against 44, but these are translation artefacts (the logged histories were mapped onto the
cap-2 tree, whose ½-pot and pot re-raises the tapered tree does not have; live, v5f maps
opponents' raises onto its own sizes), and agreement with the played action is 0.57 to 0.66
against the baseline's 0.65 to 0.70. So v5f has passed the gate and the replay and is the candidate for
Monday's burst, when it is armed; a tie in the duel plus the closed third-raise hole is the case for it, and
twenty matches will not separate it from v5d either, so season 7's first-week set is chosen
on the burst's decomposition (rule hands and preflop jams), not its headline.

*Tonight and overnight:* the semi, decomposed after; **the final's timer is armed** (20:51):
`arm_final.sh` polls the fixture list from 23:50 every five minutes, and when the final is
listed (Monday, about 02:30 IST) hands its slot to `fixture.sh` with a 15-minute lead and the
set in `fixture_set` (v7b). Dry-run 20:44 against a fake listing three minutes out: polled,
parsed, connected, stopped. Gives up at 06:00 if nothing is listed (a lost semi). Log:
`~/pokerbot-scratch/chipzen/arm_final.log`. The final; enter season 7 after it.

*Monday:* v5d's second burst; pool it with today's (+15 ± 35, 11 of 20) and choose season 7's
set, one label, unchanged through the week without a burst; cap-3 deep rungs training.

*This week, each duel-gated then burst-gated, one label at a time:* cap-3 at 50bb and above
(the third-raise hole: 29 rule hands at −1,470 in v5d's burst); 20 postflop classes at the deep
rungs (deep is the weaker half of every set); read thresholds sized to the scout's samples,
gated on the replay; the river-vs-shove check on the next two bursts, the river re-solver only
if it still leaks; Slumbot at 100bb once; the second laptop for the lanes.

*Running, lane T3:* the tapered `(4, 2, 1)` deep rungs (50/70/100bb, 20M warm, 2 threads each)
to `ladder169l_v5f`, then their duel against v5d (600 arena matches, 6,000 hands at 100bb).
Started 16:07; at 16:43 the measured rate says the solves end about 19:30 IST and the duel
about an hour after. Watch: `tail -c 300 ~/pokerbot-scratch/cap2/exp_t421_cap2_100bb.log`.

**Sunday 20 September, 16:50 IST: the histogram abstraction is trainable, and the council
found five things.** `abstraction/histogram.py` (equity histograms over sampled runouts, EMD,
k-means under EMD) is wired into `CardAbstraction` as `--strength histogram` with
`--hist-bins/--hist-runouts/--hist-opponents`, mirrored in `native/src/equity.hpp` and
`nolimit_game.hpp` (the trainer and the play-time lookup both use the native histogram; the
Python one is 30 ms a lookup, too slow for the river re-solver), pinned by
`tests/test_histogram.py`, and smoke-trained (66 and KQs on 9-4-2 land in classes 4 and 2 of
20). Three review agents then read it and the two instruments. What they found, all applied:
the C++ segfaulted on zero bins, runouts or opponents (validated now); the texture stride used
the scalar centroid count in histogram mode; fewer situations than buckets left dead classes.
**In the duel's dealer, six defects** (an all-in seat asked to act, an illegal check facing a
bet, an un-offered raise, a sub-minimum raise, a short all-in raise reopening the minimum, and
a call for less not closing the street), and then one of my fixes: the refund for a call-for-less
tested `min(stack)`, so a shove by the seat that had committed more was refunded before the
opponent was asked and the hand went on as if it had never happened. The reviewer's probe
(2,415 chip-creation failures) caught it; it now reads clean on every scripted matchup, and
the fixed test is on the *short-committed* seat's stack. Before today's fix the same block
(from 01:46) ended the street on any shove made as the second or later action, giving the
opponent a free showdown for the smaller commitment; so **every duel from 01:46 to 16:30 was
on a dealer that mishandled shoves over a bet**, symmetric enough to keep the mirror even but
not to be trusted for a comparison. Re-run on the corrected dealer (each about a minute now):
v5d against v7b+cap **61.5 ± 2.4% of 400 arena matches** without reads (was 57.2) and
**55.3 ± 2.0% of 600** with reads (was 53.7); v5e against v5d 48.7 ± 2.0% (was 50.2, still
nothing); the mirror 48.2 ± 2.0%. At a fixed 100bb over 6,000 duplicate deals v5d against
v7b+cap is **+0.6 ± 9.9 chips a hand, even** (the old dealer had read the one-raise set 12 to
22 behind there), and at 25bb +10.0 ± 5.4; so the cap-2 primary's edge in an arena match comes
from the escalating-blind phases, not from deep play. Every decision made on the old numbers
stands; the river re-solver's 52.0 ± 5.0% is not re-run yet (an hour, after the final). Lane
T3's duel is on the corrected dealer. **The stack cap now decides by the stored width, not the
stack**: a facing node's two-wide entry is fold/call whatever the reason, and the engine's
stack is not the arena's (the reviewer showed both directions of disagreement in the arena;
on the v5d record it is one decision of 1,668, 45 misses to 44). Same rule in the replay's
lookup and the river solver's reach; `play_pickles` now refuses a pickle without its stack
and blinds rather than playing it at 200/2.

*Sunday afternoon, measured:* the reads-on duel, v5d 53.7 ± 2.0% of 600 matches against v7b+cap
(57.2 without reads; same direction). **The river re-solver in the duel** (`cfr/river.py`,
`--river-solve`, 8 s budget, 1,752 solves, 0 failures): v5d+river against v5d **52.0 ± 5.0% of
100 matches**, 63 min. Inside noise; the literature's largest gain does not show at this size
against our own bot (whose river play comes from the same blueprint ranges the solver assumes;
against a real opponent the ranges are wrong in the solver's favour, which is the case the
papers measure). Costs 40 s a match to test; a 400-match run (4 h) is the honest next step
and belongs on the second laptop, not before the final. Per-item literature check in
`docs/research/2026-09-17-cap2-convergence.md`: cap-3 becomes a tapered `(4, 2, 1)` schedule
(Pluribus and Libratus give later raises one or two sizes, not a full menu); the card
abstraction change is the feature (EMD over equity histograms, or OCHS) before the count;
translation and the solver recipe are already what Pluribus uses.

*Closed, not on the list:* iterations, finer short rungs (v5e 50.2 ± 2.0% against v5d), the
full-width solver as production (−2 and −1 against the sampled 20M solves same-tree), the
stack-cap defect (fixed, `--stack-cap`), the three gate defects, the maniac read, the
river-shove override.

**Season 3 (page pasted):** PoetAndCoder (the house LLM bot) champion over Blueprint; wsp 4-1
lost the semi to Poet; half the fixtures were walkovers (three registered bots never showed).
**Season 2 (page pasted):** qwentom-leap (house) champion over wsp; five of eight entrants
were house bots. **Across seasons 2 to 5:** champions qwentom-leap and Poet (house bots, when
the field was mostly house bots), then bigboy2 and mellyy (both cyn007's); **wsp reached two
finals and two semis in four seasons and never won**, top-three in every round-robin; **Blueprint
reached two finals and a semi** from 3-2, 1-3 and 2-2; the top seed won three of four (S2, S3,
S4) and lost a semi once (S5). Same timetable every season: quarters Sat 18:00 UTC, semis Sun
18:00 and 18:10 (or 18:30), final Sun 21:00 UTC.

**Season 4 (page pasted):** bigboy2, by cyn007 (mellyy's builder), 4-0 in the round-robin and
3-0 in the playoffs, beat Blueprint in the final; wsp 4-0 lost the semi to Blueprint, which had
been 1-3; mr_hide reached a semi. Same slot pattern (quarters Sat 18:00 UTC, semis Sun 18:00
and 18:10, final Sun 21:00 UTC). Across seasons 4 and 5: the top seed won once and lost a semi
once; Blueprint reached a final and a semi from 1-3 and 2-2; wsp is top-two in the round-robin
every season and has never won it; the same builder has won both seasons with different bots.

**Sunday 20 September, 10:55 IST: the 10bb and 6bb rungs do not change matches.** v5e (v5d
plus lane SR's cap-2 rungs at 10 and 6bb, `ladder169l_v5e/`) against v5d: **50.2 ± 2.0% of 600
arena matches**; at fixed 10bb +2.2 ± 2.4, at 6bb −2.2 ± 1.7. The gate had said cap-2 10bb beats
one-raise 10bb by +14.5 and 6bb by +2.8, but the nearest-rung rule already sends a 10bb hand to
the 12bb cap-2 rung and a 6bb hand to the 5bb one-raise, and those play those depths as well as
a rung built for them. v5d's misses in the 6bb duel (932 of 9,289, the 5bb one-raise rung being
re-raised, answered by the rule at zero cost) confirm the short end is push-or-fold and nothing
there moves the result. **v5e closed; the ladder's short end stays as it is.**

**Sunday 20 September, 10:50 IST: v5d's burst, run by hand after the machine slept through
05:29.** 09:59 to 10:42, **20 matches, 11 won, +15 ± 35 chips/hand, all Blueprint**, showdowns
51 to 50. Decomposed against the earlier versions on Blueprint hands (`chipzen_decompose.py`):

| | v6 | v7 | v7b | **v5d** |
|---|---|---|---|---|
| all | −32 ± 60 | +103 ± 51 | +101 ± 44 | **+80 ± 53** |
| deep | −40 ± 56 | +51 ± 49 | +74 ± 40 | **−22 ± 67** |
| short | −17 ± 139 | +170 ± 99 | +136 ± 85 | **+204 ± 83** |
| we jammed preflop | 15 at −2,545 | 2 | 3 | **17 at +650 ± 512** |
| called a river shove | 4 at −4,044 | 3 at −2,450 | 4 at −2,719 | **5 at +6,020 ± 3,168** |
| rule decided | 24 at −2,152 | 4 | 2 | 29 at −1,470 ± 892 |

So: v5d is not v6 (its 17 jams netted +650 each where v6's 15 lost 2,545; its river calls won),
it is level with v7b overall inside the noise (+80 ± 53 against +101 ± 44), better short
(+204 against +136) and worse deep (−22 against +74, about 1.2 SE), and the rule decided 29
hands at −1,470, all third raises, which is where a cap-2 primary has no node and v7b's
companion structure never reaches. **Not a clear arena win for v5d, not a loss**; one burst at
±35 cannot separate two sets that the duel puts 15 chips apart. Decision: **tonight stays v7b**
(gated twice in the arena, and a fixture is not the place to break a tie), and **season 7 opens
with a second v5d burst on Monday 05:29** before the choice; if it reads like this one again,
the pooled two bursts decide, with the deep-stack rule hands as the thing to look at (a cap-3
tree at 50bb and above would remove them).

**Sunday 20 September, 02:15 IST: the duel plays arena matches now, and the answer is
v5d.** `chipzen_duel.py --arena-matches N`: 10,000 chips each, the arena's blind schedule
as read from every logged match (100, 150, 200, 300, 400, 600, 800, 1,000, 1,200 every 20
hands), button alternating, to a bust, A in each seat alternately, match win rate ± SE. A
dealer fix on the way: a call for less than the bet closes the street and returns the excess,
as the engine does. Zero check: a mirror wins 51.3 ± 2.9% of 300 matches at 52 hands a match
(the real fixtures have run 3 to 94). **v5d beats v7b+cap 57.2 ± 2.5% of 400 matches** (2.9
SE from even), with v7b's one-raise primary handing 8,142 decisions to the companion and v5d
handing none; **v7b vs v7 51.0 ± 2.9%** (the companion upgrade is invisible against a bot that
never re-raises, as the fixed-depth duel also said). So the layout question is answered on
both instruments: cap-2 primary at every depth, with the 20M rungs and the stack cap, beats
the one-raise primary with companions, by about 15 chips a hand at 100bb and by 57 to 43 in
matches. **Monday's burst is v5d**, and if it reads near v7b's +42 against Blueprint or
better it is season 7's set. Tonight stays v7b: gated, and a duel is a burst's worth of
evidence, not a fixture's.

**Sunday 20 September, 02:05 IST: the duel instrument, and its first answers.**
`scripts/chipzen_duel.py`: two whole bot configurations (`ArenaPlayer` each, built as
`chipzen_run.py` builds them) through `decide()` under a dealer that speaks the arena's
conventions, duplicate deals with seats swapped, chips per hand ± SE, both sides' miss,
companion and rule counts. Zero check: a mirror reads +3.8 ± 11.3 over 2,000 deals at 100bb.
**v7b vs v7 at 100bb: +0.1 ± 8.9 over 3,000 deals, zero misses and zero companion calls on
either side**: two one-raise primaries never re-raise each other, so the companions are never
asked and the sets are identical in that matchup; v7b's upgrade shows only against opponents
who re-raise. **v7b vs v5c** (the same seven 20M rungs with cap-2 as primary everywhere; the
question the week could not answer): **−18.1 ± 13.6 at 100bb and −5.0 ± 7.4 at 25bb** over
3,000 deals each, with v7b's one-raise primary missing 18% of its decisions (every re-raise)
and the companion answering all of them, v5c missing none. So cap-2 primary is ahead by about
1.3 SE at 100bb and within noise at 25bb; two more seeds at 6,000 deals: **−22.5 ± 10.0 and −12.5 ± 9.9; pooled over three seeds and
15,000 deals, −17.5 ± 6.1, about 2.9 SE. Cap-2 primary beats one-raise-primary-with-companions
at 100bb.** No reads on either side. That is the answer the week wanted: the companion
arrangement gives up about 17 chips a hand at 100bb to letting the cap-2 solve play the whole
hand, presumably because a one-raise primary never three-bets and never check-raises, and the
companion inherits lines it did not choose. The arena stack-cap fix is built behind a flag
(`ArenaPlayer(stack_cap=True)`, `--stack-cap`; `_shim` carries `your_stack`; 28 player tests
pass) and lane DL3 duels it: each layout with and without the fix, then v7b+cap against v5d
(cap-2 primary with the fix), the Monday burst candidate. **Lane DL3 (01:41):** the fix against no fix, same layout,
4,000 deals each: v7b +6.1 ± 8.2 at 100bb, **+14.9 ± 5.6 at 25bb**; v5c −6.1 ± 11.4 at 100bb,
+5.4 ± 5.1 at 25bb. With both fixed, **v7b+cap vs v5d at 100bb −14.8 ± 10.0** over 6,000 deals,
the same direction as unfixed. Note the miss column: 0 misses on every side once the cap is
honoured except the one-raise primary's re-raise misses, so the fix is real and was answering
the arena's "2% of decisions fall to the rule" (which the review reported as 33 of 1,438 in
v6's burst). Reading: the fix is a small gain that grows short (stack-capped nodes are the
all-in-facing ones and there are more of them short), never a loss; and cap-2 primary leads
one-raise-with-companions by about 15 at 100bb whether or not either is fixed. **Monday's
burst: v5d** (cap-2 primary everywhere, 20M rungs, stack cap on), label "v5d", under the
usual rule: near or above v7b's +42 against Blueprint it becomes season 7's set, near v6's −54
it does not. Dry-run the burst script before arming. Semi-final tonight is v7b regardless (gated, and v5c is v6's layout,
which lost its burst; a duel win is a burst's worth of evidence, not a fixture's).

**Saturday 19 September, 23:45 IST: quarter-final won, mellyy, 32 hands, +10,000, v7b's first
fixture.** 29 of 32 hands won on the table; mellyy folded 25 of its 56 actions and raised 16;
52 decisions, 4 misses all answered by the 20M companions, no fallback; one read fired (opened
into a folding blind). The pot that decided it, hand 22 at 50bb: K4 called an open, flopped
A-A-9, called a half-pot bet, then the opponent re-raised the turn (a 3, into 21/251/13) and
the **companion** called 1,710 and, when the river came a king, shoved and took 6,270 uncalled;
four companion decisions in one hand, all at the re-raise lines v7 used to lose. The rest were
small: a rivered flush with J4, a Q-high flush with QT, a river bet paid by A7. **Into the
semi-final, Sunday, against the winner of v003 v wsp**; the semi slot is read by a poller
from 00:40 (`playoffs_semi.txt`) and the timer armed and dry-run when it appears.

**Saturday 19 September, 18:40 IST: lane RG2, the gates with each seat on its own tree.**
One-raise self-play +0.2 ± 0.2; full-width one-raise ties sampled one-raise (−0.6 ± 0.7, and
+0.3 ± 0.6 at 20 classes); and every cap-2 solve now **wins**: 8bb +7.1 (sampled 20M warm) and
+7.1 / +7.5 (full-width, 6 and 20 classes), 12bb +22.8 / +22.4 (20M warm / 100M), 18bb +47.8 /
+48.0 / +44.9 (10M / 20M warm / 100M), 50bb +144.9, 70bb +172.4, 100bb +197.3 (20M warm) and
+205.3 (10M). But read the miss column: the one-raise side misses **17 to 27% of its
decisions**, every time it is re-raised, and the miss policy is check/call, so most of that
margin is "a one-raise bot with no companion calls every re-raise". That is what a bare
one-raise pickle does; it is not what v7b does, whose one-raise primary hands every re-raise
to a cap-2 companion. So the single-pickle cross-tree gate cannot rank cap-2-primary against
one-raise-primary-with-companions at all, in either direction: the week's "cap-2 loses 20 to
30" was the instrument, and this "cap-2 wins 50 to 200" is the instrument again. **What it does
settle:** the cap-2 solves are not broken and not badly unconverged (full-width converged and
sampled 20M agree to a point at 8bb; 10M and 100M agree within 3 at 18bb), the prototype is
faithful, and more iterations or finer buckets are not where the strength is. **The right
instrument is a duel between bot configurations**, both seats played by `ArenaPlayer` (primary,
companions, reads) over duplicate hands at the rung's stack: v7b against v5c is the question
the arena has been asking twenty matches at a time. To build (`scripts/chipzen_duel.py`,
a synthetic arena state per decision from the engine); post-season, first item. Also for the
arena player: its `_shim` carries no stack, so `cfr_agent` there never applies the stack cap
either, and a cap-2 companion's stored fold/call entry at a capped node is rejected and falls
to the rule (about 2% of arena decisions at 100bb real stacks, the all-in-facing ones); pass
the real stack in the shim and set `stack_cap=True`, gated by a burst. Nothing changes tonight.

**Saturday 19 September, 18:15 IST: lane AB2, and a third gate defect, the biggest.** The
20-class postflop abstraction at 8bb (fit by a 3M sampled one-raise solve, chance tables of
2,400 states, full-width one-raise and cap-2 solves in 41 and 70 min): 20-class one-raise ties
the 6-class one-raise (+0.3 ± 0.6; the sampled 20-class one-raise +0.2 ± 0.6), and **20-class
cap-2 still loses, −10.4 ± 0.8 against the 6-class one-raise and −9.7 ± 0.4 against its own
20-class one-raise**. So a finer card abstraction changed nothing, which pointed back at the
instrument, and the third defect is there: **`benchmark()` applies one `raise_cap` to both
seats, default one raise, and `play_pickles` never passed the pickles' caps; every cross-tree
gate this week forbade the cap-2 solve the very re-raise it was solved with**, so it played
fold/call frequencies meant for a game with a re-raise in it and lost about 10 BB/100 to a
strategy that never wanted one. Fixed: `benchmark(raise_caps=(a, b))` narrows each seat to its
own tree (the seat facing a raise its tree lacks takes its miss policy, as a bot without a
companion would); `play_pickles` passes each pickle's cap. Lane RG2 re-runs the sixteen key
gates on it. The 16:50 table below was measured with the re-raise forbidden and is superseded.

**Saturday 19 September, 16:50 IST: the gate instrument was wrong all week, fixed, and the
week re-measured.** Two defects found by asking why the full-width cap-2 solve lost 68 BB/100 to
a solve it should dominate. (1) `play_pickles.py` never passed the rung's stack: every gate
played the benchmark's default 200 chips, so "18bb against 18bb" was two 36-chip trees playing
100bb poker. (2) `cfr_agent` reconstructs a node's action list from the history alone, so at a
node the tree had stack-capped to fold/call it rebuilt six actions, rejected the stored two-wide
entry, and played the miss policy: **34% of a cap-2 rung's keys are such nodes** (79,133 of
235,017 at 18bb); a one-raise tree's two-wide nodes match by coincidence, which is why only
cap-2 solves suffered. Both fixed in the gate path: `play_pickles` uses the rung's stack and
blinds (asserted equal for the pair) and `cfr_agent(stack_cap=True)` mirrors the trees' rule;
the arena player is untouched (its bridge is on another chip scale; a burst gates it later).
Every cross-tree number above this paragraph was measured on the broken instrument. **Lane RG,
the week on the corrected one** (check/call on a miss; misses now 0 to 0.4%):

| gate at the rung's stack | BB/100 |
|---|---|
| one-raise 18bb self-play | +0.2 ± 0.2 |
| **full-width one-raise 8bb vs sampled one-raise 8bb (the faithfulness check)** | **−0.6 ± 0.7** |
| full-width cap-2 8bb vs one-raise | −11.0 ± 0.2 |
| sampled cap-2 8bb 20M warm vs one-raise | −7.6 ± 0.1 |
| 12bb cap-2 20M warm / 100M vs one-raise | −10.5 ± 0.6 / −11.4 ± 0.8 |
| 18bb cap-2 10M / 20M warm / 100M vs one-raise | −15.5 ± 0.9 / −12.0 ± 0.4 / −11.4 ± 1.1 |
| 50bb, 70bb, 100bb cap-2 20M warm vs one-raise | −10.3 ± 1.6 / −9.1 ± 1.3 / −6.3 ± 1.9 |
| 100bb cap-2 10M (v5b's) vs one-raise | −15.3 ± 0.7 |

**What it settles.** The full-width prototype is faithful (its one-raise solve ties the sampled
one to within a point), and its cap-2 solve, which is a converged equilibrium of the abstract
cap-2 game, **still loses 11 BB/100 to the one-raise rung in the real game**. So the floor is
not the sampled solver's convergence and not iterations: it is the abstraction. With six
postflop strength classes, the extra re-raise decisions are made on information too coarse to
make them well, and a strategy that never takes them does better with real cards (the
action-abstraction pathology: a finer betting tree on the same coarse cards is more
exploitable). Warm start and pruning still buy convergence (10M → 20M warm is +3.5 at 18bb), but
the gap they close ends at about −11. **Next: the abstraction**, and the full-width solver makes
that test cheap: a 20-class postflop abstraction, one-raise and cap-2 solved full-width at 8bb,
gated against the 6-class one-raise rung with real cards (lane AB2, started 16:55).

**Saturday 19 September, 16:10 IST: two small ones closed without code, and the commit.**
`ab646c2` pins the week (329 files; the new pickles and scout caches stay out of git). **The
8bb miss rate** (9% of decisions on both sides of every 8bb gate, against 1% at 18bb): the
missed histories are lines like `21/21/21/` and `31/31/`, half-pot bets called on every street,
which in the tree's 16-chip game put both players all-in before the river, so the tree has no
river node there, while the engine's real chip accounting (and the arena's, playing a 10bb
stack on the 8bb rung) leaves chips behind and asks for one. Not an encoding bug (the native
and Python games both keep the fractional symbol when a raise happens to be all-in); it is the
coarseness of the stack rungs at the short end, already counted as `off_abstraction` in the
arena stats. It is the same on both sides of a gate, so the gates stand; the fix is finer
short rungs or per-hand stack scaling, post-season. **The maniac read** is not built: over
every hoops match on record, "called a river shove" is five hands (two at −6,818, three at
−5,738), and v5 was +224 ± 141 against hoops over 188 hands while v7 and v7b read −7 ± 143
and −187 ± 285. Five hands is not a rule; `chipzen_decompose.py --opponent hoops` is the
check to re-run when there are fifty.

**Saturday 19 September, 15:40 IST: the full-width prototype, first pass, and a retraction.**
`cfr/fullwidth.py` (vectorised CFR+ over the explicit abstract game, chance factorised per
player given the board texture, keys as the pickles) and `scripts/cfr/fullwidth_solve.py` are
built; 8bb chance tables in `results/cfr/chance/nolimit_8bb.npz`. Lane FW (14:28 to 15:15):
full-width one-raise against the sampled one-raise rung, which should tie, read **−12.0 ± 0.7**;
full-width cap-2 −70.7 ± 8.2 against the sampled one-raise and −61.6 ± 4.2 against a sampled
cap-2 (20M warm, pruned; itself −21.9 ± 4.3 against the one-raise). So the factorised abstract
game is not faithful at 8bb, where the preflop all-in is the game and the factorisation prices
AA against 72 as a strong class against a weak one on an average board. Fix: a preflop all-in
margin table between the 169 classes (`scripts/cfr/preflop_allin.py`, Python evaluator, 1,200
runouts a pair, antisymmetric by construction; `nolimit_8bb_preflop_allin.npy`), which the
solver uses for a preflop all-in instead of the factorised runout. Lane FW2 re-solves with it.
**Retracted:** I logged the native `allin_edge` sampled branch as biased; it is not. Exact and
sampled agree to 0.002 on a fixed flop, both orderings. My driver drew 12 random flops per
pair and 20 per check, and the flop-to-flop variance of an all-in margin is large (a king on
the flop turns AA against KK from +0.63 to −0.9), so the asymmetry I saw was sampling noise.
The defect row is removed.

**Saturday 19 September, 13:50 IST: lane AB is in, and the recipe stalls short of zero.** 100M
iterations, frozen 100k warm start, pruning at −300 stacks, three threads each, against the
one-raise rung (check/call on a miss): **18bb −8.0 ± 2.2** (5.4 h; cold 50M read −8.1, warm 10M
−11 to −14), +7.5 ± 3.0 against its own 20M warm solve; **12bb −3.7 ± 3.1** (3.5 h; +4.2 ± 3.9
at warm 20M), +12.2 ± 7.0 against its 20M. So the solves keep improving on their own tree and
the cross-tree gap keeps narrowing, but on a log scale it is flattening: 18bb went −35 (3M), −26
(10M), −13 (warm 10M), −8 (100M warm and pruned), and 12bb sits level with its one-raise rung at
two budgets. **Convergence of the sampled solver alone does not take a cap-2 rung past the
one-raise rung at budgets we can afford**; the 100M warm-pruned solves are the best companions
we have (they beat the 20M ones same-tree at 2.5 SE and 1.7 SE) and are candidates for a burst,
but the cap-2-primary plan needs the full-width solver, a better abstraction, or both. Post-season
order updated accordingly: the 8bb full-width prototype first.

**Saturday 19 September, 12:10 IST: the season 6 bracket (season page, pasted).** Quarters
Sat 18:00 UTC onward: **NashForge v mellyy** (18:00 = 23:30 IST), v003 v wsp, Blueprint v
PoetAndCoder, Shadow v Fold-ver-3. **Our semi-final opponent is the winner of v003 v wsp**, the
two bots with wins over the season-5 champion and finalist; the other half is Blueprint, Poet,
Shadow and Fold-ver-3. v003 is being scouted and seeded now (its row held 3 hands; it has played
five fixtures since), paced at 3 s a request. Standings: NashForge 4-1, then Blueprint, Shadow,
v003, wsp, Fold-ver-3 at 3-2 (seeded 2 to 6 in that order), Poet and mellyy 2-3.

**Saturday 19 September, 12:00 IST: season 5, read from the season page (pasted by the user).**
8 bots, 4 round-robin rounds, an 8-bot bracket (everyone qualified). Quarters Sat 18:00 to
18:30 UTC, semis Sun 18:00 and 18:10 UTC, **final Sun 21:00 UTC = 02:30 IST Monday**. The
champion, mellyy, was **1-3 in the round-robin** (lost to Maxwell, RoboPoker, OmegaBot) and won
three playoff matches; the top seed Maxwell (4-0) lost the semi to wsp (2-2); Blueprint (2-2)
reached the semi; PoetAndCoder was 1-3. So the seeding predicted nothing and the bracket was
three coin flips with a lean, which is what this week's 100-hand matches look like too. Season
5's playoff slot pattern says our semi, if we win tonight, is Sunday 23:30 or 23:40 IST and the
final 02:30 IST Monday; timers to be armed after tonight's result, each dry-run. **Season 7 is
open for entries now** (registration closes Mon 23:59 UTC = Tue 22 Sept 05:29 IST); enter after
the final.

**Saturday 19 September, 08:17 IST: lane AB, a cap-2 rung taken all the way.** 18bb and 12bb
at **100M** with the week's levers on (frozen 100k warm start, pruning at −300 stacks from 10%),
three threads each (`~/pokerbot-scratch/ladder169/laneAB.sh`, watch
`tools/exp-progress.sh ~/pokerbot-scratch/ladder169/laneAB_100m.log --watch`). Gates at the end:
cross-tree against the one-raise rung (`results/cfr/xtree/`), same-tree against the 20M warm
solve. The question is whether a finished cap-2 rung crosses zero (18bb: cold 50M −8.1, warm 10M
−13; 12bb: +4.2 at warm 20M). If it does, the post-season retrain is a known recipe and the
promotion rule (cap-2 primary at a depth once it beats the one-raise rung) has its first
candidates. Nothing from it plays this weekend.

**Saturday 19 September, 09:40 IST: the river-shove override, built, replayed, not shipped.**
v7b's losses decomposed (`review_v7b.md` in the session): 650 ordinary hands +217,286; 198 folds
−55,853 (the price of playing); 141 companion hands −42,385, 129 of them small folds to
re-raises; **7 river calls against shoves −28,088**; one fallback call at a third raise −8,775 (Q9
into KK; the rule is net positive over the record and stays). The river calls looked like the
one-raise primary's known bias, so the fix was built: `ArenaPlayer(river_shove_companion=True)`
(`--river-shove-companion` on the runner; facing an all-in on the river the cap-2 companion
answers even though the primary has a node; logged as `adjusted: "river shove: ..."`; test in
`tests/test_chipzen_player.py`), and `chipzen_replay.py --river-shove-companion` reports every
such decision with the primary's and the companion's call probability. **Over the whole record
(56 river-shove decisions with a primary node: 35 in v7/v7b's bursts, 9 in v6's, 12 in v5's)
the companion would have folded calls worth 3,842 chips of the 108,308 lost on river calls.**
The big losing calls (QJ with a straight into kings full, 78 with a straight into nines full,
A9 top pair, 98) are called at 1.00 by both; the companion folds K3 (0.53 → 0.14) and AK on a
paired board (0.49 → 0.10) but calls K8 *more* (0.47 → 0.65). So the leak is mostly coolers with
strong hands, the override buys about 4,000 chips over 2,000 hands and moves some calls the wrong
way; **not worth a label, flag stays off**, the converged cap-2 primary is still the fix. Against
mellyy, wsp, Fold-ver-3 and Poet the `never_bluffs` read already folds these.

**Saturday 19 September, 06:30 IST: v7b's burst, and v7b plays the quarter-final.** 05:29 to
06:15, 20 matches, 12 won, +27 ± 30 chips/hand; **Blueprint 12 of 18 at +42** (v7: 9 of 15 at
+29), hoops 0 of 2. Decomposed on the Blueprint hands, v7b against v7: overall +101 against +103
a hand (indistinguishable, two bursts at ±30 each); **deep +74 against +51; the companion hands,
the one thing that changed, 149 at −313 against 109 at −423**; short +136 against +170 (noise-level,
the short companions changed from tapers to 20M cap-2); river calls against shoves 4 at −2,719
(the one-raise primary's own leak, unchanged). So v7b is at least v7 overall and better exactly
where it was changed, with every gate behind it (cross-tree at every depth, replay, burst).
`fixture_set` now says v7b, flags empty; the mellyy timer reads it at 23:15. The burst's ledger
label says "(50/70/100bb)" because the script was written before the short rungs went in; the
set that played had all seven, per `ladder_paths` on `ladder169l_v5c`.

**Saturday 19 September, 05:50 IST: the bracket. Quarter-final Saturday 23:30 against mellyy**
(the 8th seed; we are the 1st at 4-1; wsp, v003, Fold-ver-3, Shadow and Blueprint are 3-2,
mellyy and PoetAndCoder 2-3, runner1 and Sleight-of-Hand out). Round 5: Fold-ver-3 beat runner1,
Sleight-of-Hand beat mellyy (84 hands, the house bot bet into a 76%-folder), Shadow beat wsp
(QQ three-bet, turn shove called by a pair and a gutshot), Blueprint beat v003 (v003 raised
three times with two pair into a made flush on a three-club board). Timer armed for mellyy on
the fixed script (connect 23:15; `fixture_set` read at connect time, so v7 or v7b is chosen after
the burst). v7b's burst started 05:29.

**Friday 18 September, 23:50 IST: PoetAndCoder won, 8 hands, +10,000, v7's first fixture.**
Connected 23:25 with empty flags (one-raise primary), paired at 23:40, over at 23:41. The
match was hand 4: K3 suited against JT, the opponent re-raised the flop, the 100bb cap-2
companion answered the turn and the river (both misses on the one-raise primary), called
3,060 and then 5,090, and the 19,900 pot came to us. Round-robin **4 and 1**, the loss the
Shadow walkover. Playoffs Saturday and Sunday, slots to be read by the poller from 00:15.

**Friday 18 September, 16:00 IST: v7b is v7 with every companion retrained warm at 20M.** Lane
AA (08:26 to 15:44, two rungs at a time on two threads) did the short cap-2 rungs the way lane Y
did the deep ones; on the check/call instrument, against the one-raise rung and against the
`(4,2)` taper each replaces as v7's companion: 35bb −18.3 ± 0.8 and **+13.5 ± 1.6**; 25bb
−22.5 ± 1.4 and **+13.2 ± 5.0, +16.0 ± 2.6** on three more seeds (about +14.6 over six); 18bb
−12.1 ± 3.6 and **+34.0 ± 1.5**; 12bb **+4.2 ± 3.9** (the first cap-2 rung not losing to its
one-raise rung) and **+21.4 ± 1.3**. All four join `results/cfr/ladder169l_v5c/`, so v7b's
companions are the seven 20M-warm cap-2 solves and no tapers (`ladder_paths` drops a taper where
a cap-2 rung exists). The burst script already points at that directory. The change under
Saturday's gate is therefore "the companions", all of them, rather than the deep three; cleaner
attribution was traded for the stronger set, deliberately. Replay of the full v7b on v7's
burst hands: `replay_v7b_full_on_v7.md`. **Tonight: v7 against PoetAndCoder**, `fixture_set`
line 3 empty; the fixture script's hard-coded `--deep-primary` (which would have played v7's
directory as v5b) is fixed and was dry-run at 08:25 (connected with empty flags, stopped after
its deadline) before re-arming. Playoff slots not listed yet; a poller reads `--fixtures` every
half hour from 00:15 and writes them to `~/pokerbot-scratch/chipzen/playoffs.txt`.

**Friday 18 September, 08:20 IST.** Round-robin after four rounds: NashForge 3-1 (the loss a
walkover, below), wsp 3-1, v003 3-1 (beat wsp and PoetAndCoder; a 2013 rating on 129 hands),
then five at 2-2; eight of ten go through. PoetAndCoder tonight 23:40 (timer armed on the fixed
script, self-checked). Our platform rating fell to 1497 after v6's burst; cosmetic for the season.

**v7's burst (05:29 to 06:49): 12 of 20, +31 ± 32 chips/hand** (`ledger.md`; Blueprint 9 of 15
at +29, mr_hide 3 of 3, hoops 0 of 2; 167 of 1,771 decisions missed the one-raise primary, the
cap-2 companion answered 160, the rule 7). Between v4's +62 and v6's −54, so inconclusive on the
headline. **Decomposed over the Blueprint hands** (the same script over v3, v4, v6, v7; chips per
decision-hand): v7 +103 overall, +51 deep, +170 short; v6 −32, −40 deep, −17 short, with 15
preflop jams at −2,545 each (most of its loss); v4 +163. **v7's whole leak is the 109 hands (16%)
where the opponent re-raised and the 10M cap-2 companion took over: −423 each, about 46,000
chips; the other 582 hands ran at +200.** v4 with the same companions: 92 hands at −501. Plus
three river calls against shoves at −2,450 (the one-raise tree's known bias: shoves look
bluff-heavier in a game nobody can re-raise). **v5b's deep play is v6's deep play** (same 10M
rungs, same primary role, measured −40 a hand over 506 hands), so reconstructed against Blueprint
v5b sits near +40 against v7's +103. Recommendation moved from v5b to **v7 for PoetAndCoder**,
with the reasoning in the session: Poet re-raises rarely (companion asked less), a station
punishes bad jams more than it rewards three-bets. The user decides; `fixture_set` says v5b
until told otherwise. Lesson, mine: decompose a burst before recommending on it; the headline
alone put v5b forward this morning and v5b forward for Shadow yesterday.

**Lane Y: the deep cap-2 rungs warm-started (frozen 100k) at 20M**, two threads each, 00:24 to
06:54, on the check/call cross-tree gate against the one-raise rung, before and after:
50bb −21.1 ± 3.6 → **−14.2 ± 2.4**; 70bb −18.5 ± 0.8 → **−8.5 ± 1.4**; 100bb −12.8 ± 2.4 →
**−7.9 ± 1.7**. Same-tree 20M-warm against 10M: +6.1 ± 2.2, +2.8 ± 0.9, +4.7 ± 1.3. Every rung
better, all but 50bb past three standard errors. Assembled as `results/cfr/ladder169l_v5c/`
(v5b's files with the three 20M rungs), which serves two candidates: **v7b** = that directory
without `--deep-primary` (v7 with better companions, the direct fix for v7's leak) and **v5c** =
with it. **Saturday's 05:30 burst candidate: v7b**, armed 08:30 (`~/pokerbot-scratch/chipzen/v7b_burst.sh`,
log `v7b_burst.log`; same shape as the v7 burst script, which has run twice). Its replay on v7's
own burst hands (`replay_v7b_on_v7.md`): the primary's lines identical (0% differ, same primary);
of the 167 primary misses the 20M companions answer 85 (the replay cannot ask the tapers), and on
those lines the KQ hand that shoved 12,075 into aces becomes a fold to the three-bet (0.98), while
AQ still calls the three-bet (0.86). Pruning: built (`MCCFR::set_pruning`, `--prune-after`,
`--prune-stacks`; Kuhn converges with it on, off is the old path, 4 tests). **Lane Z measured it
at the Pluribus threshold (−30,000 stacks) and it pruned nothing that mattered**: 903,739 action
visits skipped of roughly 10^10, 4,056 s against 4,085 s unpruned (0.406 vs 0.409 ms/it), so no
speed gain; the gates read −14.3 ± 3.0 pruned against −21.2 ± 3.2 cold, which with 0.015% of
visits skipped is run-to-run variance (the pruning coin also shifts the random stream), not an
effect. Under the linear discount our cumulative regrets never reach that magnitude; the
threshold has to be scaled to the run (a fraction of the current iteration times the stack) and
re-measured. **Lane Z2 (15:44 to 16:41), thresholds our regrets reach:** at −300 stacks, 157.5M visits
skipped (about 1.5%), **2,685 s against the unpruned 4,085 s, 0.268 vs 0.409 ms/it, a third
faster**, gate −18.2 ± 5.3 against cold's −21.2 ± 3.2 (no measured cost); at −3,000 stacks,
42M skipped, 3,256 s, gate −13.7 ± 2.1. Same seed, same three threads, same side-by-side
arrangement as lane Z, so the wall times are comparable within the noise of a shared machine.
So pruning at −300 stacks is worth about 1.5x on the sampled solver at no strength cost on this
rung; default stays off until it is re-measured on a deep rung post-season.

**Friday 18 September, 00:10 IST: the Shadow fixture was lost by walkover, and it was my
script.** `fixture.sh` computed its stop window with `date -d "$SLOT +40 min"`, which GNU date
rejects; the function returned an empty string, every comparison against it read as "already
past", and the only guard left was "lobby quiet three minutes", which at 23:40 to 23:43 it was
because the match had not started. The script stopped the bot at 23:43; the fixture opened at
23:50 to an empty lobby. Noticed 23:58, reconnected at once, too late: Shadow is gone from
`--fixtures`. Fixed: `date -d "$SLOT 40 minutes"`, an arm-time self-check that refuses to arm if
the arithmetic returns empty or is not monotonic, the window and deadline overridable
(`STOP_AFTER`, `DEADLINE`, `STATUS_AFTER`) so the script can be dry-run against a slot minutes
away, which it now has been. Lesson, into the standing rules: **a timer script is exercised end
to end against a fake slot before it is armed**; a syntax check is not a test. Record: 3 and 1
in the round-robin (the loss a walkover, not a match). The message to the organisers is the
user's call.

**State on Thursday 17 September, 09:05 IST.** Three fixtures of three won (runner1, mellyy,
v003). Standings after three rounds, from the platform's match records: **NashForge 3-0, wsp
3-0**, Fold-ver-3 2-1, v003 2-1, Blueprint 2-1, Shadow 1-2, mellyy 1-2, PoetAndCoder 1-2 (lost to
mellyy and v003), runner1 0-3, Sleight-of-Hand 0-3. Eight of ten go to the playoffs (Sat and
Sun, three rounds), so the remaining fixtures decide seeding, not qualification. **Tonight
Shadow at 23:50 is played by v5b, unchanged** (`fixture_set` says so; `fixture.sh` connects at
23:35). Friday PoetAndCoder 23:40, same script.

**What Thursday morning measured, in the order it happened.**

1. **Lane Q (short cap-2 rungs at 10M, gated same-tree against their 3M solves):** 35bb +3.7 ±
   2.7, 25bb +12.8 ± 1.4, 18bb +8.0 ± 3.1, 12bb +15.6 ± 7.5 (`ladder169l_v6/gate_10m_vs_3m_*`).
   Only 25bb clears three standard errors. Same direction as the deep rungs.
2. **v6's burst, 05:30 to 06:10: 20 matches, all Blueprint, 7 won, −54 ± 41 chips/hand**,
   showdowns 35 won / 48 lost. v4 played the same bot 20 times at 15 won and +62. The review
   (`chipzen_review.py --opponent Blueprint --last 20`): the biggest pots were preflop stack-offs
   on the deep cap-2 rungs (44 jammed for 63bb into QQ, JJ for 97bb into AA, TT four-bet into
   KK), two of the eight worst were the fallback rule calling a third raise it has no node for
   (TT 7,750, Q5 9,450; 33 misses, 20 at three raises; Blueprint re-raised 115 times in 1,121
   hands), and the short cap-2 rungs played the small stacks worse (Q7 raised a river 2x and
   called a shove at 35bb). **v6 is closed.** Its short cap-2 rungs and the 10M ones stay out.
3. **The cross-tree gate that was never run before deep-primary was adopted:** each cap-2 rung
   against the one-raise rung at the same depth, 40k x 3 (`ladder169l_v6/xtree_*.json`). **Every
   cap-2 rung loses**: 10M short rungs 35bb −26.0 ± 2.7, 25bb −27.6 ± 1.5, 18bb −26.0 ± 0.4, 12bb
   −29.6 ± 3.1; the 10M deep rungs v5b plays tonight 100bb −19.1 ± 2.3, 70bb −23.8 ± 1.1, 50bb
   −24.6 ± 2.3; the 3M short rungs 25bb −31.4 ± 2.4, 18bb −35.1 ± 6.0. The one-raise strategy
   is a legal strategy inside the cap-2 game, so a converged cap-2 solve cannot lose to it; these
   are the measure of how unconverged the cap-2 solves are. 3M to 10M closed 4 to 9 points of a
   30-point gap.
4. **Roughly 40% of that gap is lines the cap-2 tree has never visited, not its play.** The
   miss rate reads 0.9% of decisions but that is about 4.5% of hands, and the big ones (a 2x-pot
   bet called on three streets); `play_pickles` answers a miss with a uniform random action,
   including the shove. Re-run at 25bb with check/call on a miss: −29.6 became −17.5 (one seed,
   30k hands). So the honest "cap-2 plays worse where it was trained" figure is nearer 17 than
   27, and the rest is holes, which the arena answers with the fallback rule instead (the TT and
   Q5 hands above). An earlier note in this file said the misses were negligible; that was wrong.
5. **Lane R, started 08:55** (`~/pokerbot-scratch/ladder169/laneR.sh`, watch
   `tools/exp-progress.sh ~/pokerbot-scratch/ladder169/laneR_50m.log --watch`): cap2 18bb at
   **50M** on six threads, then the cross-tree gate against the one-raise 18bb rung and a same-tree
   gate against the 10M solve. The question is whether iterations alone can close the gap in the
   time there is. Near zero: iterations are the answer, and a warm-started retrain (cap-2 nodes
   initialised from the one-raise pickle at the histories they share; needs a native entry point
   and a Kuhn test, about half a day of code, then 8 to 10 h of training on six threads for the
   ladder) is worth building. Still around −15: the problem is elsewhere (sizes, averaging, the
   abstraction under a re-raise) and the one-raise-primary v7 is the playoff bot. The chess bot
   shares the machine, so the ETA the trainer prints is the honest one.
6. **wsp and Fold-ver-3 seeded** into `opponents.json` from the scout cache (wsp 2,157 hands, 0
   river bluffs of 161; Fold-ver-3 1,803 hands, 0 of 164), so "river bet believed" fires against
   both from hand one. Neither is a station, a folder to opens or a folder to three-bets by the
   thresholds, so nothing else fires. **wsp vs mellyy, read from the platform record** (103 hands,
   wsp 67 of them): mellyy folded 61 of 94 preflop, wsp opened 43 buttons (min-raise, 3x once the
   blinds rose), called mellyy's three-bets and folded the flop when it missed (9 of 15), barely
   bluffed, and the match was one preflop pot: AJ called a 4,777 three-bet from KT, board A-K-x,
   10,754. Against us the blind-stealing runs into the solver's big-blind defence, and the river
   read covers the rest. No new rule.
7. **The platform rate-limited us** (`RATE_001`, blocked 15 min, 60 violations) after the index
   refresh plus follow-ups at 00:30; the bot was off. Anything that walks the API now goes at one
   request every 3 to 4 s (`scratchpad/seed_top_half.py` shows the pacing).

**Thursday afternoon: lanes R, S and T.** Lane R, the 18bb cap-2 rung at **50M** (six threads,
3 h): **−12.7 ± 0.8** against the one-raise rung (3M −35.1, 10M −26.0), +2.9 ± 0.2 against its
own 10M on the same tree. The gap closes on a log scale, 8 to 13 points per tripling, no floor
seen; zero is somewhere around 150M to 250M for a short rung. The tree was fully reached from 4M
on (235k infosets, flat), and check/call-on-miss now moves the number by one point where at 10M
it moved twelve, so what remains is play at reached nodes, not holes. **The cap-2 solves are
unfinished, not broken; finishing them cold is days of machine time.**
**Warm start built** (`MCCFR::warm_start`, `train_nolimit.py --warm-start PICKLE --warm-weight N
--warm-scale C`; regrets at a node are seeded from a coarser game's strategy when the node is
first created, the average is not; `key_from_string` on both games; Kuhn keeps −1/18 from a
converged prior and recovers from a wrong one under linear; golden test untouched; 15 native
tests pass). Lane S, 18bb at 10M warm from `nolimit_18bb` (70,756 of 71,208 entries landed):
**−21.9 ± 1.0** against the one-raise rung, cold 10M −26.0, so worth about 6M cold iterations,
**a 1.6x speed-up**. Lane T, heavier priors: weight 5M −21.5 ± 3.7, scale 10 −25.4 ± 3.1, no
better. The plain proportional prior is the limit, not its weight; the Brown and Sandholm form
(regrets from each node's counterfactual values) is the next step and is post-season work.
**Thursday evening: the warm start is a real lever after all, at a light setting.** A second
form, `--warm-mode frozen` (Brown and Sandholm's substitute regrets, sampled: every node plays
the one-raise prior for N iterations while regrets accumulate, then regret matching takes over),
was worse than cold at N = 1M and 3M (−30.6, −29.2 against −26.0) and much better at N = 100k
(−16.4). Replicated on the new instrument (`tools/xtree-gate.sh`: cross-tree against the
one-raise rung, check/call on a miss, both miss rates in the JSON): frozen 100k at three seeds
−11.4 ± 1.4, −13.7 ± 2.2, −14.1 ± 2.2; cold 10M at two seeds −21.6 ± 2.0, −17.8 ± 3.6; cold 50M
−8.1 ± 2.7. **About 3x in iterations.** A long frozen phase measures regret against an opponent
who never re-raises and stores wrong lessons about aggression; a short one gives the direction
without the bias (the paper's "T matches the prior's quality"). Two instrument lessons:
random-on-miss inflated every gap (cold 10M read −26.0 there, −21.6 here), and single training
runs vary about 4 points seed to seed, so a solver claim needs two seeds. Full account and
sources: `docs/research/2026-09-17-cap2-convergence.md`. Also built: `scripts/cfr/chance_tables.py`
(the abstract game's chance player as bucket-transition and showdown tables, from a million
deals through the rung's own abstraction; `results/cfr/chance/nolimit_18bb.npz`;
`tests/test_chance_tables.py`), the first piece of the full-width solver. Post-season order:
warm-started 20M retrain of every cap-2 rung gated at two seeds (a night), replay, bursts; the
full-width prototype at 8bb in parallel. Nothing from this goes into the playoffs.
**v7 built and replayed** (`results/cfr/ladder169l_v7/`, v5b's rungs by symlink, played without
`--deep-primary`; `chipzen_replay.py` gained `--baseline-deep-primary` and `--companions`, which
answers the one-raise primary's misses with the cap-2 companion as the bot would):
`replay_v7_on_v5.md`, `replay_v7_on_v6.md`. On re-raises v7 plays exactly v5b (same companion
pickle); everywhere else it is the one-raise solver, most-likely action differing on 57% of
preflop and 48% of turn decisions against Blueprint, the TT/JJ/44 stack-offs becoming calls.
**A one-raise tree cannot re-raise**: v7 never three-bets, never raises a bet, never check-raises;
its only three-bet is the `folds_to_three_bet` read. Unmeasured cost; Friday's burst measures it.

**Friday's 05:30 burst is v7's gate** (armed 21:45: `~/pokerbot-scratch/chipzen/v7_burst.sh`, log `v7_burst.log`; starts v7 with the queue at 05:29, stops after 20 matches or 11:30): one-raise primary at every depth (no `--deep-primary`),
cap-2 as the companion that answers re-raises, one label, replay pass first. It has to sit between
v6's −54 and v4's +62 against Blueprint; near v4 or above it plays the playoffs, near v6 and v5b
does. The cross-tree gate has a blind spot the arena does not: the one-raise agent never
re-raises, so it never tests what the one-raise rung does when re-raised, which is the case
deep-primary was adopted for and which v4 won 15 of 20 with. Assemble v7 today while the bot is
off; `fixture_set` stays on v5b for Shadow.

**Thursday 00:10 IST.** NashForge is entered in Chipzen season 6 as a
remote bot from this machine, **three fixtures of three won** (runner1, mellyy, and v003 at
00:01 Thursday: three hands, +10,000, A5s called a turn shove with top pair and the nut flush
draw against AT and rivered two pair; 0 misses). The lobby-hours limit blocks the rated queue
but **not a season fixture**, which was the open question. v5b played it: the 169-class linear ladder (`results/cfr/ladder169l_10m/`, v5's rungs
with the 50, 70 and 100bb cap-2 solvers retrained at 10M iterations, which beat the 3M ones by
+3.0, +3.6 and +9.4 BB/100 on the same tree), `(4,2)` companions at 12 to 35bb, sequential
triggers, scouted reads. The bot is **out of the lobby** until `fixture_v003.sh` reconnects it
at 23:40 with inbound only: the free tier allows 8 lobby hours a day (resets 05:30 IST) and today
used 10.6. Thursday 05:30 quota burst is **v6**'s gate (`ladder169l_v6/`: v5b plus cap-2 rungs at
35, 25, 18, 12bb). Then Shadow Thu 23:50, PoetAndCoder Fri 23:40, playoffs Sat and Sun.
**v6 is assembled with the 10M rungs and has its replay pass**
(`results/chipzen/replay_v6.md`, re-run 22:53 on the set as it stands): 2,559 logged decisions,
baseline misses 143 against 141 logged, new-set misses **126**, so the short cap-2 rungs reach
17 of the lines v5's tree did not, which the 10M rungs alone did not (143 against 143).
Preflop most-likely action differs on 46%, postflop 18 to 24%. Both remaining fixtures are scripted: `~/pokerbot-scratch/chipzen/fixture.sh` is armed for
Shadow (connect 23:35 Thu, slot 23:50, log `fixture_shadow.log`) and PoetAndCoder (connect 23:25
Fri, slot 23:40, `fixture_poet.log`); each connects inbound-only, prints the lobby at +5 min,
and stops after the match. **The set it plays is read at connect time from
`~/pokerbot-scratch/chipzen/fixture_set`** (line 1 ladder dir, line 2 label), currently v5b, so
the morning's v6-or-v5b call is one edit to that file. **Lane Q, started 00:12 Thursday** (`~/pokerbot-scratch/ladder169/laneQ.sh`, watch
`tools/exp-progress.sh ~/pokerbot-scratch/ladder169/laneQ_10m.log --watch`): v6's four short
cap-2 rungs (35, 25, 18, 12bb) retrained at 10M, same recipe and seed, two threads each, then
sequential gates against the 3M rung on the same tree into
`ladder169l_v6/gate_10m_vs_3m_cap2_*.json`. Why: the deep rungs gained +3.0 to +9.4 from the
same step, and these are the depths where most fixture hands are played once the blinds rise.
Decision rule as before: a rung over three standard errors is symlinked into `ladder169l_v6`
(`results/cfr/experiments/cap2_<rung>_10m.*`) and `fixture_set` points at v6 for Shadow. The
native trainer has no checkpoint, so a Windows restart loses any unfinished rung. Thursday
morning is scripted too:
`~/pokerbot-scratch/chipzen/v6_burst.sh` (armed 22:54, log `v6_burst.log`) stops v5b from
01:00 once the lobby has been quiet for three minutes, starts v6 with `--queue` at 05:29, and
stops it after 20 matches or at 11:30, whichever is first, between matches, so at least two of
the day's 8 lobby hours are left for Shadow. None of the scripts survives a Windows restart in the
03:00 to 09:00 window; if the machine restarts, start v6 by hand at 05:30 with the command in
the script. A fixture drops off `chipzen_run.py --fixtures` the moment it opens, and the platform paired
us about a minute after the slot; a 0-active reading on the minute is normal.

**What today settled.** Iterations are the lever and the four solver flags (CRN, exact
terminals, current-when-empty, average-from) are not: same-recipe gate +0.12 ± 1.46, 10M gate
+9.4 ± 1.0. The native solver now runs on threads (`--threads N`, 4.0x at four, golden-identical
at one), and a rebuild no longer kills running trainers, so a full 16-rung retrain fits in about
three hours. Slumbot, 10,000 hands on the 200bb contender: −815 ± 357 mbb/hand, no better than
folding; 41% of it in the 4% of hands with a lookup miss, the rest at river showdowns from the
big blind. Post-season work, not this week's. Uncommitted since 4cb6900: everything from the
C++ sitting on (items 1, 2, 4 to 10, 12, threads), the Slumbot report fix, the ledger, this file.
Ledger: `results/chipzen/ledger.md`.

**Standing rules for the rest of the season.** One change per `--label`; nothing goes live
without a same-tree gate of more than three standard errors and a replay pass; the bot sits in
the lobby only for the quota burst and the fixture windows; one heavy job at a time beside the
bot unless `free -m` shows more than 3 GB available; no coding 09:00 to 12:00 on a day the user
says so.

**Read first: `docs/research/2026-09-15-what-moves-the-bot.md`**, the synthesis of four reviews
run overnight on 14 to 15 September, with the four full reports beside it. The cause of the
lossless preflop's loss is the solver's averaging (unweighted, per-visit discount that
collapsed to vanilla at rarely reached nodes, exact uniform for never-averaged nodes), fixed
that night: `--update-rule linear` on the trainer and a cumulative discount in `cfr/updates.py`
and `native/src/mccfr.hpp`. **Wednesday 08:40 IST: mellyy won too; the calibration said what it needed to.** Fixture 2:
NashForge beat mellyy, 94 hands, +10,000, 77 of 94 hands won; blind opens fired 5 times for +900,
the three-bet twice for −250; 3 misses, slowest 3.7 ms. **Two of two.** The night job ran the
always-fold calibration and then the fixed player's 10,000 hands (at 6,000 by 08:19, done about
12:05, then the bot returns for its quota). Calibration: only the 500 big-blind hands completed,
because `HandState.facing_bet` did not know the small blind owes half a blind before any action
(fixed, tested); on those 500 the raw column read −840 mbb/hand against an expectation of about
−840 for big-blind-only hands, so **the raw column is honest**, while the baseline-differenced
column read +418 ± 1,077: **useless, and never to be quoted**. The calibration is re-running with
the fix (`results/slumbot/calibration_always_fold_1k.json`; raw must read −750 over both seats).
**v6 is assembled** in `results/cfr/ladder169l_v6/` (v5's 16 rungs plus cap-2 at 35, 25, 18,
12bb); its replay waits for the Slumbot run to free the memory, then it takes Thursday's 05:30
quota as its gate. Playoff picture from round 1: wsp, Fold-ver-3, mellyy and one of PoetAndCoder,
v003 or us.
**Wednesday 12:51 IST: v5's quota burst is in, 13 of 20.** 524 hands, +60,000 chips, +115 ± 84
chips/hand, showdowns 86 won / 43 lost: mr_hide 6 of 8 (+233/hand), hoops 4 of 6 (+107),
r0ckGarden 3 of 6 (0). Rating 1617 → 1601 ± 63 over the burst despite the chips, because the
house bots sit far below us and a loss costs several wins; the season is decided by fixtures, so
this number is not acted on. The two mr_hide losses were both cap-2 coverage: a third raise on
the turn (K4s called TT's shove through the fallback at 2.8 to 1) and 16 misses in 39 hands, 7 of
them at zero raises on the 70bb rung. That is what the v7 recipe (lane N) and v6's short cap-2
rungs are for, not a new rule. The bot stays up as v5 for v003 at Thursday 00:00.
**Wednesday 12:55 IST: the v7 gate is a tie, so v5's recipe stands.** Lane N trained the cap-2
100bb rung with all four flagged solver changes on (CRN, exact terminals, current-when-empty,
average from 0.1; `results/cfr/experiments/cap2_100bb_v7.*`) and played it against v5's rung on
the same tree, 40k x 3: **+0.12 ± 1.46 BB/100** (`ladder169l/gate_v7_vs_v5_cap2_100bb.json`).
Both reached the same 2.26M information sets, so none of the four changes widens coverage, which
is what the arena misses need; they change what is written at a node, not which nodes exist.
A same-recipe head-to-head is also nearly blind to this kind of change by construction (two
near-equilibria score about zero against each other), so a tie here says "not worse", not
"no effect"; the honest test of these flags is exploitability or the Slumbot column, later.
**Decision: no retrain tonight.** v5 plays v003 at 00:00, v6 (short cap-2 rungs) takes the
05:30 quota as its gate. The flags stay off by default. Lane N's 2,224 s for 3M is not a timing
result either; v5's rung trained beside three other lanes.
**Wednesday 14:27 IST: lane O, the coverage lever, queued behind the Slumbot run.**
`~/pokerbot-scratch/ladder169/laneO.sh` (detached with nohup) waits for `slumbot_measure.py` to
exit, then retrains v5's three deep cap-2 rungs with the same recipe and seed at **10M
iterations instead of 3M** (`results/cfr/experiments/cap2_{100,70,50}bb_10m.pkl`), verifying
each pickle loads and gating each same-tree against the v5 rung
(`ladder169l/gate_10m_vs_v5_<rung>.json`, 40k x 3). Why this and not the flags: the v7 tie
showed the flags do not add nodes, while the 169-class progression climbed steadily with
iterations to 3M and the mr_hide losses were unreached nodes. Watch:
`tools/exp-progress.sh --watch`. **Decision rule:** a rung whose gate wins by more than three
standard errors replaces v5's in `ladder169l_v6` for Thursday's 05:30 burst and for Shadow; if
the 100bb gate is in before 23:00 and wins that clearly it can also go live for v003 under a
new label, otherwise v003 is played by v5 unchanged. A tie means iterations are not the lever
either and the deep-rung work stops for the season.
Wednesday 16:40 IST: lane O's sequential loop was replaced by lane P (`laneP.sh`, same log): the
trainer is single-threaded and the machine was otherwise idle, so the 70bb and 50bb rungs now
train beside the 100bb one instead of after it, three trainers at about 0.5 GB each beside the
1 GB bot. All three gates should land this evening instead of after 02:00.
**Wednesday 17:00 IST: item 11, threads, is done.** The native solver takes `--threads N` (see the
defect table); one thread is bit-identical to before, four gave 4.0x on the golden game, and
`native/build.sh` now installs by rename, so a rebuild no longer kills a running trainer (the
three 10M trainers kept running through this one; the guard that refused to build is gone).
The whole 16-rung retrain that took two lanes ten hours on Tuesday would take about three hours
on six threads. That also changes the arithmetic of the v7 flags: lane N's recipe was 2.5x
faster per iteration than v5's on the same rung on a quiet machine (0.74 vs 1.9 ms/it), most
likely common random numbers sparing the bucket lookups, and threads multiply that. Nothing goes
live from this before Thursday; what it buys is that tonight's decision can be followed by a
full retrain of whichever recipe wins, on threads, in time for the playoffs.
**Wednesday 21:35 IST: the 100bb gate wins, +9.4 ± 1.0 BB/100 to 10M over v5's 3M** (seeds
7.4, 10.4, 10.4; `ladder169l/gate_10m_vs_v5_cap2_100bb.json`; 2,312,269 information sets against
2,263,275, 22,445 s at 2.24 ms/it beside two other trainers). Nine standard errors, so by the
rule above it goes in. Iterations are the lever, and the v7 flags were not. Assembled
`results/cfr/ladder169l_10m/`: symlinks to v5's rungs with `cap2_100bb.*` pointing at the 10M
solve, the 70bb and 50bb rungs to follow the same way if their gates (about 22:00 and 22:30)
win. Then the replay check, and the bot restarts as **v5b: v5 with 10M deep cap-2 rungs** before
23:30 for v003, one change under its own label. v6 for Thursday 05:30 takes the same rungs.
**Wednesday 22:40 IST: all three deep rungs win; v5b assembled; a new platform limit.** 50bb
+3.0 ± 0.7, 70bb +3.6 ± 0.7 (4 and 5 standard errors; `gate_10m_vs_v5_cap2_{50,70}bb.json`), so
`ladder169l_10m` carries all three 10M rungs. Replay (`results/chipzen/replay_10m.md`): the same
143 misses as the v5 set on 2,559 logged decisions, so the 10M solves do not add coverage on the
lines actually played; they play the reached nodes better (most likely action differs on 25% of
preflop and 11 to 12% of postflop decisions). The bot was started as **v5b** at 22:35, reached
the lobby, and was stopped again, because the platform now enforces **lobby_hours_per_day, 8 h
on the free tier, resets 00:00 UTC (05:30 IST)**; we hit it at 20:02 (the queue has returned 429
every 22 s since) and were at 10.6 h. Whether an over-limit bot can still receive its fixture is
unknown, so exposure is cut: `~/pokerbot-scratch/chipzen/fixture_v003.sh` reconnects at 23:40
with `--accept-inbound` only (no `--queue`) and prints the lobby status at 23:45. From Thursday
the bot must not sit in the lobby outside the quota burst and the fixture windows, or the 8 hours
run out before the evening's match. The 05:30 burst is v6's gate as planned, and v6 should take
the 10M rungs too, so assemble it as v5b plus the short cap-2 rungs before then.
**Wednesday 15:20 IST: the 10,000-hand Slumbot run is in: −815 ± 357 mbb/hand.**
`results/slumbot/m1_cap2_200bb_fallback.json` (9,999 hands, one illegal-bet protocol error, 532
min of play, seed 20260916, the fixed player throughout: 6,000 hands before the 09:00 pause and
3,999 after, the two segments agree at −70 ± 44 and −98 ± 60 chips/hand). That is the raw
column, the one the calibration validated; the differenced column read +130 and is not quoted.
The fallback did not move it: the pre-fix player's 5,498-hand partial read −790 ± 540 on the
same strategy. Split (`m1_cap2_200bb_fallback_split.md`): hands with a lookup miss are 4% of
hands and 41% of the loss at −7,960 mbb each (stack-offs), and 168 of the 325 misses were at
**zero raises on the street**, the same shape as the mr_hide losses: histories the 3M-iteration
tree never visited. Hands without a miss still lose −499 ± 284, almost all of it at river
showdowns (−7,040 per showdown) and from the big blind (−1,368 vs −261 on the button). So
against a bot this strong the 200bb cap-2 contender has two problems: coverage (lane O is the
test) and river play at showdown (the river solver, item 13, post-season). The report crashed
once on the checkpoint's string keys (`miss_depths`), fixed, with `--report-partial` added so a
run that finishes its hands and dies in the report is written from the checkpoint instead of
replayed. For the season nothing changes: Slumbot is 200bb unlimited-raise against a far
stronger opponent than any fixture; the arena is 100bb.

**Wednesday 00:40 IST: runner1 won, a fifth read in for mellyy.** Fixture 1: NashForge beat
runner1, 78 hands, +10,000; 21 bluffs withheld, one river bet believed, 10 misses, slowest
decision 166 ms. Round 1 elsewhere went with the ratings (Fold-ver-3 over Blueprint, v003 over
Shadow, wsp over Sleight-of-Hand, mellyy over PoetAndCoder); Blueprint and the house bot
Sleight-of-Hand are in the field. Added `Profiles.folds_to_three_bet` (25 of 29 for mellyy, 0.75
over 25 as the trigger): facing an open at 30bb or deeper, a fold from the solver becomes a
half-pot three-bet, which replaces an action worth zero with one that shows a profit at any fold
rate above two thirds. Fires for mellyy alone. Bot restarted 00:36 with it. Remote-track note:
our rated queue only pairs with Blueprint and RoboPoker, so our rating is capped near 1650
whatever we do; the container upload (flat table plus the C++ equity path) is what puts a copy in
the upload pool.

**Tuesday 20:45 IST: tonight's order, by the user's call.** After the 01:50 fixture ends (from
02:00, three quiet minutes with no match active) the bot stops, the always-fold calibration runs
(1,000 hands), then the fixed player's 10,000 hands (`results/slumbot/m1_cap2_200bb_fallback.json`,
about 9 hours, checkpointed), and then the bot restarts as v5 and takes its queue quota, around
noon Wednesday. Timed job: `~/pokerbot-scratch/slumbot/handover_night.log`. The Slumbot run
crosses the 03:00 to 09:00 Windows restart window with the bot off; a restart costs only the last
checkpoint, resumed by hand. The old player's run pauses at 22:45 and is not resumed; its partial
at about 5,600 hands is the record of the random-guess player.

**Tuesday 20:30 IST: the Slumbot loss is the random guess on a miss, not the solver.** At 3,000
hands of the contender the raw figure was −1,255 ± 758 mbb/hand, but split by lookup
(`scripts/slumbot_split.py results/slumbot/m1_cap2_200bb.partial.json`): the 2,864 hands without
a miss were **−416 ± 484, not separated from zero**, while the 135 hands with a miss lost 19,059
each and carried 68 percent of the loss (a third raise the tree lacks: 69 hands at −33,174; river
misses: 39 hands at −72,538). The Slumbot player took the panel agent's uniform random action on a
miss, a shove one time in six, in exactly the re-raised pots; the arena player never did.
`fallback_choice` (the arena's hand-strength rule) is now shared with `slumbot/player.py`
(`--no-fallback` keeps the old behaviour for a measurement of the solver alone), tested. The
current run keeps the old player until the 22:45 pause as the record of it; the morning job runs
the always-fold calibration (`slumbot_pilot.py --policy fold`, raw must read −750) and then
10,000 hands of the fixed player on `results/slumbot/m1_cap2_200bb_fallback.json`. **The
−997 ± 396 on record is a measurement of a random agent at its misses**, which the project's own
history said to look for.

**Tuesday 18:35 IST: the audit of the bot against the frontier is done.** Two reports
(`docs/research/2026-09-15-frontier-audit.md`, `2026-09-15-solver-engineering-audit.md`) and the
plan they produce, `docs/research/2026-09-15-two-week-push.md`: seven correctness-preserving
engineering changes (about 30x per night together, including a flat strategy table that turns the
2.4 GB ladder into 200 MB), five convergence-preserving solver changes, then the gated strategy
changes, then Slumbot. Starts Thursday daytime at the earliest; nothing rebuilds native while the
season runs.

**Tuesday 17:55 IST: the 20-bucket gate drew (−0.5 ± 1.2 BB/100 on the cap-2 100bb tree, 20
buckets without texture against v5's six with texture; no ladder retrain), so the night is the
Slumbot 10,000-hand run on the contender.** The contender's pickle is 3.2 GB in a process and the
bot 2.4 GB, which is the memory-kill state, so they alternate by timed jobs
(`~/pokerbot-scratch/slumbot/handover_*.log`, `~/pokerbot-scratch/chipzen/v5_timed_start.log`):
Slumbot alone 17:47 to 22:45 (paused by kill, checkpoint every 500 hands), the bot alone from 23:00
through the 00:10 and 01:50 fixtures and the 05:30 queue burst, Slumbot resumed from 07:00 once no
match is active until it finishes (about 14:00 Wednesday), then the bot restarted as v5. Watch:
`tools/slumbot-progress.sh ~/pokerbot-scratch/slumbot/m1_cap2_200bb.log`. The v6 set
(`results/cfr/ladder169l_short/`, cap-2 at 35, 25, 18, 12bb) is complete; on the push-or-fold check
its calls against a shove agree with the equilibrium on 91 to 94 percent of hands and its small blind
limps about half instead of min-raising nine in ten.

**Tuesday 17:10 IST: v5 is up now (16:58) rather than at 23:00; the Slumbot 10,000-hand run is
deferred.** Rule for the overnight core: improvement first, measurement when there is a question.
If the 20-bucket gate (`gate_b20_vs_v5_cap2_100bb.json`, about 17:40) wins, the night trains the
20-bucket ladder; if it loses, nothing else is ready and the idle core runs Slumbot instead
(`scripts/slumbot_measure.py --hands 10000 --strategy results/cfr/contender/cap2_200bb.pkl --out
results/slumbot/m1_cap2_200bb.json --resume`). The paper can quote the miss-rate gate (4.1 against
11.9 percent) and the record figure honestly either way.

**Tuesday 17:05 IST: v5's start is armed for 23:00** (a timed job, `~/pokerbot-scratch/chipzen/
v5_timed_start.log`, with a lobby check at 23:45). The short cap-2 rungs at 35, 25 and 18bb are
trained (`results/cfr/ladder169l_short/`, 12bb finishing); on the push-or-fold check they limp
about half of small-blind hands and raise 40 percent instead of min-raising 90, and their calls
against a shove agree with the equilibrium on 91 to 94 percent of hands
(`results/cfr/pushfold_check_short_cap2.md`). **v6 = v5 plus those four rungs copied into
ladder169l**, gated by Thursday's 05:30 queue burst under its own label, for Thursday night.
Wednesday's 05:30 burst is v5's first live test.

**Tuesday 16:10 IST: v5 beats v4 at every rung** (`results/cfr/ladder169l/h2h_*.json`, same
tree per rung, 40,000 hands x 3 seeds, BB/100 to v5): cap-2 100bb +6.5 ± 0.5, 70bb +5.6 ± 1.5,
50bb +4.9 ± 1.4; one-raise 35bb +33.7 ± 2.7, 25bb +47.1 ± 2.4, 18bb +51.8 ± 3.3, 12bb +53.8 ± 9.3,
8bb +21.8 ± 3.8, 5bb +101.1 ± 9.3. The short rungs are where the difference is: v4's were 250k
vanilla iterations on six Chen classes, v5's are 3M linear on 169, and the push-or-fold check says
v4 called shoves 13 to 19 points too wide there. Half of every match is played on those rungs.

**Tuesday 15:50 IST: v5 verified and parked; the afternoon's runs.** The ladder169l set is
complete (16 rungs), the replay of the logs passed (the same 202 misses as logged), and v5 was
started once with its full flags, loaded everything, warmed up in 0.24 s, read the scouted
profiles and reached the lobby; it is stopped and **restarts at 23:00 for the 00:10 fixture**
(`tools/chipzen-run.sh --accept-inbound --queue --ladder-dir results/cfr/ladder169l
--deep-primary --sequential-triggers --scout-reads --label "v5: ..."`). Push-or-fold check
(`scripts/cfr/pushfold_check.py`, `results/cfr/pushfold_check.md`): the new 5bb rung is within
0.012 bb/hand of the exact equilibrium and the big blind's calling ranges are within a point or
two at every depth, where the old set called 13 to 19 points too wide; the small-blind side
min-raises nearly every hand because the one-raise tree has no re-jam, which is what the short
cap-2 rungs fix. A fourth scouted read, PoetAndCoder's sizing tell (`Profiles.big_bets_are_value`,
0 of 463 big bets air against 363 of 960 small), is in behind the same flag. Running: lane K, cap-2
short rungs into `results/cfr/ladder169l_short/` for a gated v6 (about 17:30); lane L, the
20-bucket postflop rung and its gate (`gate_b20_vs_v5_cap2_100bb.json`, about 18:30); lane M, v5
against v4 rung by rung (`results/cfr/ladder169l/h2h_*.json`); then the 10,000-hand Slumbot run
on the contender, chained behind lane K (`tools/slumbot-progress.sh
~/pokerbot-scratch/slumbot/m1_cap2_200bb.log`), about 12 h. The rating trace records after every
match (`scripts/chipzen_rating.py`). The bot is off until 23:00 by request; quota spent.

**Tuesday 13:10 IST: the bridge was mis-reading every call, and it is fixed.** An audit of the
arena path (`docs/research/2026-09-15-season6-levers.md`) found `chipzen/bridge.py` treating a
call's amount as a bet level where the arena sends the increment (3,128 of 3,128 logged calls).
Pot undercounted in 60 percent of decisions, wrong history key in 23 percent, effective stack
shrinking inside a hand, most of the logged misses and fallbacks. Fixed with a real hand pinned
(`tests/test_chipzen_bridge.py`), plus seven short-stack technicalities (raise clamp, rejection
fallback, mid-match re-dial, short blind post, pot-odds fold, legality guard, bluff rule facing
a bet). **Every figure before v5 was measured with the old bridge.** Two scouted reads added
behind `--scout-reads` (`Profiles.folds_blind`, `never_bluffs`): mellyy's blind is opened for
the minimum, runner1's river bets are believed from 20bb. Three research reports in
`docs/research/` (format, opponents, synthesis). **v5 flags:** `--ladder-dir
results/cfr/ladder169l --deep-primary --sequential-triggers --scout-reads --accept-inbound
--queue`, label "v5: 169-class linear ladder, bridge call fix, shove rule from 20bb, scouted
reads". After the swap: cap-2 on the short rungs, then the PoetAndCoder sizing response.

**Tuesday 12:40 IST: fixtures and scouting.** It was a Windows Update restart at 06:59, not
sleep (KB5129195; active hours 09:00 to 03:00 allow restarts overnight, which is the user's
setting to change). Fixtures: Wed 00:10 runner1, Wed 01:50 mellyy, Thu 00:00 v003, Thu 23:50
Shadow, Fri 23:40 PoetAndCoder, 30 s clock. None is in our logs; `scripts/chipzen_scout.py`
profiled them from the platform's own hand histories (validated on Blueprint, mr_hide, hoops)
and seeded `opponents.json`; see `docs/arena-plan.md` for the reads. v4's burst, read against
the revealed cards: the shove rule cost about 184,000 chips at short stacks and now fires only
from 20bb (`SHOVE_RULE_MIN_BB`). **v5 = ladder169l + that fix + seeded profiles +
`--sequential-triggers`**, when the lanes finish (about 14:40).

**Tuesday 15 September, 09:55 IST. The swap gate passed, then the laptop slept.** The 169-class
linear cap-2 100bb rung beat the live cap2_100bb by **+6.5 ± 0.5 BB/100** over 40,000 hands x 3
seeds (`results/cfr/ladder169l/gate_cap2_100bb.json`, 06:42). v4's quota burst from 05:40:
**24 matches, 18 won, +71 ± 26 chips/hand**, 20 of them against Blueprint at +62. The laptop
slept at about 06:59 (WSL booted again 09:46), which killed the bot and both ladder lanes, so
rungs in progress restarted from scratch. Bot relaunched on v4 at 09:52; the ladder resumed in
three lanes (cap-2 70 and 50; one-raise 50, 35, 25; one-raise 18, 12, 8, 5 then companions),
`tools/ladder-progress.sh ladder169l`. Estimated complete about 14:30 from the measured
rates. **Then, in order:** replay the logs through `ladder169l`
(`scripts/chipzen_replay.py --ladder-dir results/cfr/ladder169l`), restart the bot as v5 on
`--ladder-dir results/cfr/ladder169l --deep-primary`, before the 23:30 fixtures and never
during a match; then the 10,000-hand Slumbot run on the contender, one heavy job at a time.
The machine must not sleep tonight.

**04:49 IST: crossed at 3M, and the Slumbot miss rate gate passes.** 169 linear against 6
linear at 3M on the one-raise tree: **+1.4 ± 0.9** (seeds −0.4, +2.4, +2.2), so the trend
−15.8, −5.7, −3.1, +1.4 has crossed, thinly. The 200bb cap-2 contender
(`results/cfr/contender/cap2_200bb.pkl`, 4.2M infosets, 3M iterations) played 850 of 1,000
Slumbot hands at a **4.2 percent lookup miss rate against 11.9** for the one-raise 200bb
solver: the deeper tree removes two thirds of the misses, which is the contender plan's gate.
Do not read that run's win rate. Two lanes are retraining the whole ladder as
`results/cfr/ladder169l/` (169 classes, linear, 3M per rung, the same recipe otherwise;
`tools/ladder-progress.sh ladder169l`): lane H is the cap-2 rungs with the swap gate after
the 100bb one (`gate_cap2_100bb.json`, about 07:00), lane I the one-raise rungs and
companions, about 12:00. **Swap only if the cap-2 gate wins**, with a new label, before the
23:30 fixtures. After the lanes: the 10,000-hand Slumbot run on the contender
(`scripts/slumbot_measure.py --strategy results/cfr/contender/cap2_200bb.pkl --out
results/slumbot/m1_cap2_200bb.json`, about 12 h), one heavy job at a time.

**02:53 IST: the clean test.** Six-class under linear as the opponent: **169 linear loses
−3.1 ± 1.6**, and 6 linear against 6 vanilla is +2.1 ± 2.4, not separated. So the earlier
+5.4 was the rule helping the 169-class solver converge, not the abstraction winning. The gap
at equal budget is −15.8 (250k), −5.7 (1M vanilla), −3.1 (1M linear): closing, not crossed.
No ladder retrain. Lane G runs both at 3M under linear (`gate_linear169_vs_linear6_3m.json`,
about 04:20); if that crosses, the retrain is worth it, and if not, the preflop lever waits
for the exact preflop all-in evaluation and the skip-early-averaging trick from the
convergence review.

**02:28 IST: linear averaging flips the preflop result.** On the one-raise 100bb tree at 1M
iterations each, the 169-class solver under `--update-rule linear` beats the 169-class vanilla
one by **+6.4 ± 2.7** and the six-class vanilla one by **+5.4 ± 2.4** BB/100
(`results/cfr/ladder169/gate_linear169_*.json`), where last night 169 vanilla lost to 6 vanilla
by 5.7 ± 1.5. Shove-node jaggedness 0.32 to 0.23, not yet converged. Confound: the six-class
opponent was vanilla; the clean test (six-class linear, then 169 linear against it and 6 linear
against 6 vanilla) is lane F, `gate_linear169_vs_linear6_1m.json` and
`gate_linear6_vs_vanilla6_1m.json`. If 169 linear still wins, the ladder is retrained under
linear with 169 classes and gated on the cap-2 tree before any swap.

**02:04 IST: the harness killed every background lane for low memory** (the bot's 2.4 GB plus a
1 GB trainer plus the test suite), and the contender's pickle was truncated mid-write. Relaunched
at 02:08 with the native module already rebuilt and its 8 tests passing: the contender retrain
finishes about 04:20, its Slumbot run about 05:35; the linear experiment about 02:40. One
heavy job at a time while the bot is live. Three lanes were queued (`~/pokerbot-scratch/ladder169/lane*.log`,
`tools/ladder-progress.sh ladder169`): the 200bb cap-2 contender for Slumbot
(`results/cfr/contender/`), a 1,000-hand Slumbot miss-rate run on it
(`tools/slumbot-progress.sh ~/pokerbot-scratch/slumbot/contender_pilot.log`), and the
169-class one-raise rung at 1M under linear with two play-offs
(`results/cfr/ladder169/gate_linear169_*.json`). The Slumbot bridge now reads the schedule from
the pickle and counts misses by raise depth (`slumbot/bridge.py`, `slumbot/player.py`). The
lane-A 70bb and 50bb rungs of `ladder169` were stopped: they carried the old discount.

**Written 15 September, 00:10 to 00:40 IST, all behind flags and all off by default**, so the
live bot and every panel figure are unchanged until one is switched on and gated:

| piece | flag | where | tests |
|---|---|---|---|
| Postflop purification (argmax instead of sampling) | `--purify postflop` on `chipzen_run.py`, `slumbot_measure.py`, `slumbot_pilot.py` | `evaluation.benchmark.cfr_agent(purify=)` | `test_benchmark.py` |
| Slumbot loss split by miss, street, position | runs from now on write `hand_records`; `scripts/slumbot_split.py <result.json>` | `slumbot/player.py` `begin_hand`/`hand_record` | `test_slumbot_bridge.py` |
| Sequential exploit triggers (fire from 40 bets when the interval excludes the baseline) | `--sequential-triggers` | `chipzen/opponents.py` | `test_chipzen_opponents.py` |
| Bankroll cap on exploits (only while net against that opponent is not negative) | `--exploit-bankroll` | same | same |
| Per-history opponent action counts, the raw material for a data-biased response | always collected now (`by_history` in `results/chipzen/opponents.json`) | same | same |
| **River endgame solving on the exact hand** (vector CFR+, blueprint ranges, live chips) | `--river-solve [--river-budget 8]` | `cfr/river.py`, hook in `chipzen/player.py` | `test_river.py` |
| Re-solve logged rivers and compare with the play | `scripts/river_solve.py --last 20 [--opponent X]` | writes `results/chipzen/river_resolve.md` | |

The river solver builds the 1,081 hands in about 1.3 s and runs 400 iterations in about 3 s;
the decision record carries `river: {iterations, ms, strategy}` when it fires and the blueprint's
answer stands if it fails or overruns. A first look at four logged Blueprint rivers agreed with
the play on two and folded ace-queen high to a 41 percent bet where the play called and won;
that is a reading against the blueprint's own betting range, not against Blueprint's. None of
this is measured. The gate for each is the same as ever: 40,000 hands on the same tree, or the
arena ledger under its own label. Not built: the overnight data-biased response solve itself
(the counts for it are now collected).

**Measured Monday night, 14 September: the lossless preflop loses the same-tree gate, so the
bot stays on v4.** The cause of the big Blueprint losses was traced to the preflop abstraction
rather than the fallback: six Chen classes put KQo, T9s and 77 in one bucket with TT and AQ, and
at the 70bb rung that bucket calls a three-bet shove 97 percent of the time. The fallback rule
answered 32 of v3's 1,367 decisions and one of the eight most expensive hands on record.
`CardAbstraction(preflop_buckets=169)` now keeps every starting hand its own class
(`abstraction/buckets.py`, native table widened to 16 bits, `--preflop-buckets 169` on the
trainer, `PREFLOP_BUCKETS=169` on the tool scripts), and a full ladder was retrained on the
`ladder200t` recipe into `results/cfr/ladder169/` (`tools/ladder-progress.sh ladder169`). The
gate is `play_pickles` at 40,000 hands x 3 seeds against the 200t solver on the same tree, so
the only difference is the preflop abstraction. BB/100 to the 169-class solver:

| play-off, 100bb | 169 vs 6 |
|---|---|
| cap-2, 3M iterations, **the swap gate** | **−4.4 ± 1.8** (every seed below zero) |
| one-raise, 1M vs 1M | −5.7 ± 1.5 |
| one-raise, 250k vs 250k | −15.8 ± 3.8 |
| one-raise, 1M vs the live 250k rung | +15.2 ± 4.4 (iterations, not abstraction) |

The gap closes with iterations and has not crossed at any budget tried, so the rule set before
the run stands: no swap. `scripts/chipzen_replay.py` re-asks every logged decision of a ladder
that has not played (`results/chipzen/replay.md`), and at the 100bb cap-2 rung the lossless
solver does fold the hands that lost: Q9o to a three-bet, 68s to a two-times open, KTs to a shove
two thirds of the time. So the mechanism is real and the head-to-head still penalises it, which
is the equilibrium-against-exploitation trade this project has now measured five times: the
six-class opponent's shoving range carries the bluffs an equilibrium has and Blueprint does not.
The instrument that could settle it is the arena, and at 20 matches a day and ±31 chips a hand
it cannot. The 70bb and 50bb cap-2 rungs finish about 03:45; re-run the replay then for the KQ
hands, which sat at the 70bb rung. `results/cfr/experiments/nolimit_100bb_{169,6}_1m.pkl` are
the density-test solvers.

### After the season: the open defects, in the order to fix them

Found by the 15 September audits (`docs/research/2026-09-15-solver-engineering-audit.md`,
`2026-09-15-frontier-audit.md`, the arena-path audit in `2026-09-15-season6-levers.md`). The
sixteen defects fixed that day are recorded in `docs/arena-plan.md`; these are the ones still
open. Every solver item needs a native rebuild, which kills any running training, so none of them
starts before Friday's fixture. Guard the equality items with a native golden test: 2,000 cap-2
iterations at a fixed seed, `average_strategy()` byte-identical before and after.

| # | defect | where | fix | effort | gate |
|---|---|---|---|---|---|
| 1 | **done 16 Sept behind a flag**: `--current-when-empty` exports regret matching's current strategy where the average is empty (`strategy_for_export`); test pins that only uniform averages change. Gated 16 Sept in the v7 bundle: tie, +0.12 ± 1.46 BB/100 on the same tree; stays off | | | | |
| 2 | **done 16 Sept**: `average_strategy_flat` in the bindings (three arrays via nanobind ndarrays), the trainer builds the pickle's dict as views and writes the flat pair beside it; golden identical, flat equals map entry for entry, end-to-end verified on a tiny run | | | | |
| 3 | **done 16 Sept, ladders converted** (ladder169l, ladder169l_v6, contender: 3.2 GB to 263 MB): `cfr/flat.py` (`FlatStrategy`, `load_strategy`), `scripts/cfr/flatten_strategy.py`, `tests/test_flat.py` pins the chip series identical; the three loaders prefer a flat pair newer than its pickle. Convert the ladders (`flatten_strategy.py results/cfr/ladder169l/*.pkl`, one pickle in memory at a time) when the machine is free, then restart the bot on them | every `saved["strategy"]` site | sorted `uint64` keys, `int32` offsets, one `float32` array, behind a `Mapping` shim with `.get` | 6 to 8 h | equality: shim reproduces the dict entry for entry, `benchmark()` chip series identical at a fixed seed |
| 4 | **done 16 Sept**: `street_actions` and `who_folded` return views; golden output identical; the same cap-2 solve 1.646 to 1.501 ms per iteration with the bot and a Slumbot run sharing the machine | | | | |
| 5 | **done 16 Sept**: refetch removed, golden output identical. The reserve was tried and taken out (1.62 with, 1.65 without, no difference). Speed effect of the refetch itself unmeasured: the audit's 1.43 ms baseline was a six-class-preflop tree, and the 169-class one times at 1.62; a proper A/B against the pre-change module is part of the Thursday sitting | | | | |
| 6 | **done 16 Sept** (memo cap 4,096; golden output identical; `cache_size` still unbound) | | | | |
| 7 | **done 16 Sept**: 64-bit packed keys (bucket in the top byte, 18 history symbols at 3 bits), decoded on export; golden identical. Timing inconclusive under a load average of 4 to 6 with the bot and Slumbot running (1.66 to 1.72 against 1.50 measured earlier at lower load); A/B on a quiet machine still owed | | | | |
| 8 | **done 16 Sept behind a flag**: `--common-random-numbers` (one nine-card deal per iteration, revealed street by street, shared by both traversers; `set_common_random_numbers` on the solver), off by default so the golden output stands; shape test passes. Gate: a same-tree head-to-head against the same recipe without it, 16 Sept v7 bundle: tie, stays off | | | | |
| 9 | **done 16 Sept behind a flag**: `--exact-terminals` scores flop and turn all-ins over every runout (990 or 44); test agrees with 40,000 sampled runouts within 0.02 on three boards; preflop all-ins still sampled (a table later). Gated 16 Sept in the v7 bundle: tie, +0.12 ± 1.46 BB/100 on the same tree; stays off | | | | |
| 10 | **done 16 Sept as an option**: `--average-from 0.1` on the trainer (`set_average_from` in the native solver, mirrored in `cfr/mccfr.py`), default 0 so the golden output is unchanged; Kuhn reaches −1/18 with the first quarter skipped. Use it in the next retrain, which is then gated as a path change | | | | |
| 11 | **done 16 Sept behind a flag**: `--threads N` on the trainer (`MCCFR::train(iterations, threads)`): a 256-shard node table locked per shard for insertion, a one-byte spinlock per node for the update, per-worker game copy and random stream, iterations handed out by an atomic counter. One thread is the exact old path (golden test: 0 mismatches). Measured on the golden 20bb cap-2 game beside three running trainers: 0.234 ms/it at 1 thread, 0.058 at 4 (4.0x); Kuhn converges at 4 threads; same-iteration head-to-heads are inside the seed-to-seed noise of ±10 BB/100 (−10.1 ± 4.5 and +9.2 ± 1.4 at two seeds) and 4x the iterations in the same wall time wins +29.2 ± 6.7 (`results/cfr/experiments/threads/`). Not deterministic above one thread. Pre-sized open addressing was not needed | | | | |
| 12 | **done 16 Sept**: a per-decision memo in `decide` and a bounded memo across decisions in `ArenaPlayer._bucket` (the same cards come back every street), seeded per key as the lookup is; rule tests pass | `benchmark.py:196-198`, `chipzen/player.py:341-347` | memoise per decision | 1 h | equality |
| 13 | **memo done 16 Sept** (`HandSet.build` and the per-board bucket arrays memoised, river tests pass, warm build 0 ms); the tree build outside the budget and the incidence matmul remain | `cfr/river.py:360-373,430-432` | memoise by board; move the build inside the budget; an incidence matmul in `showdown` | 1 to 2 h | equality |
| 14 | **done 16 Sept**: always-fold read −699 ± 21 mbb/hand over 1,000 hands against an expectation of −700 (Slumbot folds its small blind a fifth of the time), so the raw column is honest; the baseline-differenced column read −646 ± 1,193 and is retired | | |
| 15 | nothing restarts the bot after a Windows reboot (the 06:59 outage) | Windows | a Task Scheduler entry at logon that starts WSL and `tools/chipzen-run.sh` | 1 h | none |

**The golden test exists (16 Sept):** `scripts/cfr/make_golden.py` wrote
`tests/golden/native_cap2_20bb_seed7_2000.json` (46,664 information sets, seed 7, 2,000
iterations, linear) with the module as it stood before any solver change, and
`tests/test_native.py` re-solves and requires every entry identical. Re-baseline with `--force`
only after a deliberate path change has passed Kuhn and Leduc. Reframed effort for the C++
items, from the day's actuals: 2 at 20 min, 4 at 30, 5 and 6 and 10 at 5 each, 7 at 1 h, 1 at 15
min plus its gate, 8 at 1.5 h, 9 at 1 h plus the table, 11 at half a day; items 1 to 10 are one
sitting of about four hours, the first window with nothing training, Thursday daytime.

Order: 2 and 3 first (they end the memory juggling and make the ladder a few hundred MB), then
4 to 7 and 12 to 13 as one equality-tested batch, then 8, 9, 10 with the convergence tests, then
11, then 1 with its gate, and 14 and 15 whenever the network and the Windows side are free.

### After the defects: the baseline plan, in order

What the solver is given to work with, once the defect list above makes a night worth about
30x today's iterations. Each step has the gate that can read it; the frontier comparison
(`docs/research/2026-09-15-frontier-audit.md`) says two weeks of this moves the Slumbot loss from
about −1,000 to a few hundred, and that a win needs steps 1 to 3 together, which is the month.

1. **Train to convergence.** A cap-2 rung at 60M iterations in a night rather than 3M in two
   hours. The lossless preflop's thin nodes (50/50 facing a shove) and the 20-bucket draw were
   density problems, and this is where that stops being true. Gate: same-tree head-to-head,
   40,000 hands x 3 seeds.
2. **Resolution postflop.** Fifty to 200 imperfect-recall buckets with the 169 preflop, river
   equity by enumerating the 990 opponent hands and flop equity from a table rather than 200
   samples. Six buckets is why queen-nine and queen-ten are one hand. Retrains the ladder;
   gates each step.
3. **Search at play time.** The river solver (`cfr/river.py`, built) with Modicum's tweaks and
   ported to C++ so 2,000 iterations fit in a second, then the turn solved to the end with its
   44 rivers. Modicum's turn solver was worth 22 mbb/hand against Slumbot, more than its
   blueprint. Keep it unsafe (at 200 buckets unsafe beats max-margin; the estimate variants
   need per-hand values a coarse blueprint cannot supply). Gate: on against off on the same
   tree, then its own arena label.
4. **Purification postflop and the current-strategy fallback**, built or an hour away, both
   gated: small gains that compensate for an unconverged average.
5. **Measure honestly.** The always-fold calibration of Slumbot's baseline column, then a
   chance-only AIVAT from the blueprint's values, so the external number carries an interval a
   change can cross. Without it nothing above can be ranked against Slumbot.
6. **Only then the tree**: a third raise or opponent-only sizes, chosen from the
   translation-distance histogram in the Slumbot logs, because the cost of few sizes is what
   the turn solver removes on the streets it covers.
7. **On top, for the arena**: the data-biased response per opponent from the scouted counts,
   capped by what it has won. The 2000 rating is exploitation the ledger can measure, built on a
   baseline that no longer gives chips away.

### The week, in order

1. **Tuesday afternoon:** `venv/bin/python scripts/chipzen_run.py --fixtures` for the round's
   times. Read the ledger: v4 against v3 and v2 on chips per hand; revert to v3 flags only if v4
   is clearly worse (both are one restart, see the commands below).
2. **Tuesday to Friday, from 23:15 IST:** machine awake, bot connected (it reconnects on its
   own after sleep; confirm with the progress reader before 23:30). Round-robin fixtures start
   23:30 IST (18:00 UTC), ten minutes apart, 30-second clock, 10,000 chips at 50/100, blinds up
   every 20 hands. The platform waits about 90 s for a remote bot, then walkover.
3. **After each round:** `scripts/chipzen_review.py` and `scripts/chipzen_ledger.py`; the biggest
   losing hands are the diagnosis. Change one thing at a time and restart with a new `--label`.
4. **Wednesday:** Tuesday's round into the paper and slides
   (`scripts/phase2/make_figures.py`, `make_springer.py`, `make_latex.py`, `make_slides.py`);
   rehearse the demo (bot in the lobby, `tools/chipzen-progress.sh --watch`, a house-bot match
   via `tools/chipzen-run.sh --house-bot --once`, the review). Package the code: tag the commit,
   zip `results/chipzen/matches`.
5. **Thursday 18 September:** fold Wednesday's round in, submit (`docs/NashForge_LNCS.docx`,
   `docs/latex/nashforge.pdf`, `docs/NashForge_Phase2.pptx`), demo. Plan and rubric:
   `docs/submission-plan.md`, `docs/course/assignment-brief.pdf`.
6. **Saturday and Sunday:** playoffs, if we qualify; times from `--fixtures`.

### Commands

    tools/chipzen-run.sh --accept-inbound --queue --ladder-dir results/cfr/ladder200t --deep-primary --label "v4: ..."
    tools/chipzen-run.sh stop                     # never during a match: progress reader shows 0 active
    tools/chipzen-progress.sh --watch
    venv/bin/python scripts/chipzen_run.py --fixtures
    venv/bin/python scripts/chipzen_ledger.py     # win rate and chips/hand per version
    venv/bin/python scripts/chipzen_review.py     # the expensive hands, off-tree rate, action mix
    tools/chipzen-run.sh --house-bot --once       # one unrated practice match (uses the daily quota of 20)

Free tier: 20 challenge or queue matches a day, reset 05:30 IST; season fixtures do not count.
Every match log is stamped with the version; `results/chipzen/epochs.json` labels the older ones.

### After the season, in this order (rewritten 19 September)

- **Read `docs/arena-plan.md`** for the drawbacks and what each fix did; **`docs/chipzen.md`**
  for the platform; `docs/research/2026-09-17-cap2-convergence.md` for the solver findings.
- **The full-width solver on the explicit abstract game** (`cfr/fullwidth.py`), gated at 8bb
  first: its one-raise solve must tie the sampled one-raise rung (the faithfulness check), then
  its cap-2 solve against the same rung is the question lane AB could not answer. If the
  factorised chance is not faithful past the preflop all-in table, joint chance is the next
  build. Then the C++ port, if it passes.
- **The abstraction**, if the full-width solve says the floor is the buckets: more postflop
  strength classes, one rung retrained warm and pruned, gated cross-tree against a one-raise
  rung on the same new abstraction.
- **Promotion by the rule, rung by rung:** a cap-2 rung becomes primary at its depth when it
  beats its one-raise rung on `tools/xtree-gate.sh` at two seeds, then replay, then a burst.
  12bb is level already.
- **Companions:** the 100M warm-pruned solves beat the 20M ones same-tree; a burst under its own
  label is the arena test. The maniac read (fold one pair to a river shove when the opponent's
  raise share is over half), gated on the replay.
- **Pruning at −300 stacks on by default** once re-measured on a deep rung; warm start frozen
  100k as the standard start. Iterations beyond 100M are not a lever (lane AB).
- The container upload (a second rated record, run on their machines) and the Slumbot
  re-measurement on whichever solver wins the above; bet sizes (`NUM_ACTIONS`) last.

### What was learned this week, briefly

- The arena found the abstraction's weakest point in a day: deep-stacked re-raised pots. A
  one-raise solver answers every re-raise with a substitute; the cap-2 solver removed that.
- The bot loses in one of two ways against strong bots: calling too much against a fold-or-raise
  bot (Blueprint), or bluffing into a bot that never folds (mr_hide). Both now have a measured
  trigger in `chipzen/opponents.py`.
- Two operational failures cost a day each and are fixed: a lobby socket that died in the
  laptop's sleep but read as connected (silence watchdog), and rebuilding the native module
  under a running training (SIGBUS; `native/build.sh` now refuses).

---

## Earlier: the Slumbot steps and the abstraction findings

**Both Slumbot steps are done, and the answer is that neither lever moved the number.**
Path A completed on 10 September: a 200bb solver trained to 250,000 iterations
(`results/cfr/nolimit_strategy_200bb_250k.pkl`, 3h30m, 23,970 information sets) and measured
against Slumbot over 9,999 hands (`results/slumbot/m1_200bb_250k.json`, 739 min).

| solver | stack depth | vs Slumbot | miss rate |
|---|---|---|---|
| 4,000 iterations | 100bb | −1750.2 ± 524 | 8.7% |
| 150,000 iterations | 100bb | −986.6 ± 374 | 10.4% |
| 250,000, corrected game | 200bb | **−997.8 ± 396** | 11.9% |

The difference between the last two is **−11.2 mbb/hand against a combined interval of ±545**,
which is not separated. Three improvements went into that gap and none of them showed: the all-in
fix, another 100,000 iterations, and matching Slumbot's stack depth. The 200bb retrain was still
worth doing, because the agent is no longer handicapping itself and the figure is now the honest
one, but it did not buy anything.

**What this says about where to go next.** The training lever is spent and the depth lever is
spent, so the binding constraint is the action abstraction: one raise per street and six card
buckets, against an opponent with an unrestricted betting tree. The rising miss rate is the same
message from another direction, 8.7 to 10.4 to 11.9 percent, because deeper stacks and a better
solver reach more nodes the abstraction cannot express.

**1. Card buckets: settled 11 September, and six is right at every budget tested.**
Six against twenty, wall-clock budgets over a 128-fold range, three seeds, played head to head
(`results/cfr/bucket_sweep_long.json`, `scripts/cfr/bucket_sweep.py`). Chips per hand to six:

| budget | 6 vs 20 | iterations, 6 / 20 |
|---|---|---|
| 40s | +3.307 ± 1.159 | 1,567 / 1,683 |
| 160s | +2.499 ± 0.473 | 5,242 / 5,900 |
| 640s | +1.372 ± 0.536 | 18,092 / 20,433 |
| 1280s | +1.423 ± 0.404 | 34,775 / 38,133 |
| 2560s | +0.497 ± 0.317 | 66,183 / 75,050 |
| 5120s | **+0.624 ± 0.259** | 134,500 / 145,442 |

**The gap declines and then plateaus around +0.5 to +0.6, still separated from zero.** The earlier
three-arm ladder stopped at 1280s with the gap falling by a factor of four, which read as an
approaching crossing. It is not one. At big blind 2 the residual is about 31 BB/100, so it is a
real edge rather than a rounding artefact. Fifty buckets was dropped after the first sweep: it lost
to twenty at every rung with no closing trend.

**Twenty buckets was not short of time.** It is cheaper per iteration at every rung and bought 7 to
13 percent more traversals at equal wall-clock, so the budget axis favoured the finer arm and it
still lost. Its disadvantage is the partition, not the compute. The docstring's worry that
wall-clock would unfairly penalise a finer abstraction was backwards, and is corrected there.

**Scope.** The top rung is 134,500 iterations against the shipped solver's 250,000, so this is 55
percent of production budget, not beyond it. The plateau across the last three rungs carries the
conclusion rather than arrival at production scale. Two of eighteen matchups trained under a load
imbalance, both in seed 0's top rungs, worst 1.4.

**So the card abstraction is not the lever, and the raise cap is the only untested dimension left.**

**1b. The card abstraction is noise-limited, and this qualifies 1. Measured 11 September.**

| | |
|---|---|
| equity estimate sd at 40 samples | **0.0667** |
| distance between adjacent bucket centroids | 0.101 to 0.170 |
| situations that change bucket on a re-roll at the same 40 samples | **42%** |

At 200 samples the sd falls to 0.0307 and at 1,000 to 0.0134.

**The noise in the estimate is about half the gap between adjacent buckets.** So
a large fraction of hands are placed by Monte Carlo error rather than by hand
strength, and that is a property of the estimator, not of the partition.

**Read the bucket sweep in that light.** Fifty buckets spaces centroids roughly
0.02 apart against noise of 0.067, more than three bucket widths, so assignment
at fifty was close to random. The sweep therefore measured **how many buckets our
equity estimator can resolve**, not how many buckets are worth having. Six won
because six is near the limit of what a 0.067 error can distinguish. Do not
quote it as "six buckets is correct" without that condition.

**What to do about it.** The 4.3x speedup means 200 samples now costs about what
40 cost before, so the precision is affordable. Whether it produces a better
solver is empirical and has the same shape as everything else here: train at 40
and at 200 on equal wall-clock and play them off. It changes the abstraction, so
it bundles with a retrain rather than going in quietly, and it must not be
bundled with the taper or a win will not be attributable.

**1c. Speed, 11 September: 32.4 -> 7.47 ms/iteration, 4.3x.** Two changes, both
committed and verified answer-for-answer. `score_hand_7` replaced an uncompiled
evaluator that was 68% of runtime across 6.4 million calls per 2,000 iterations;
the rollout's sampling moved inside the compiled loop. Four other routes were
tried and reverted, recorded in `4dfd175` so they are not tried again: suit
isomorphism, caching `_street_actions`, scoring showdowns, and dropping
`equity_samples`. The last of those turned out to point the wrong way entirely,
which is finding 1b.

The 250,000-iteration solver is now about 50 minutes rather than 3h30m, and a
5,120-second budget buys roughly 580,000 iterations rather than 134,500.

**2. The memory growth: found and fixed, 11 September.** `games/nolimit.py` memoised
`bucket_for` in `_bucket_cache` with no ceiling. Keyed on (hole, board) it spans roughly
1,326 × 2.1 million, so it never saturates: 2,800,227 entries and 491 MB by 60,000 iterations,
which is what put a 1280-second ceiling on the first sweep.

Capping it at `BUCKET_CACHE_LIMIT = 500_000` costs **5.2 percent** of iteration speed and removes
**90 percent** of the growth (18.50 to 19.47 ms/it; +721.1 MB to +72.6 MB over 60,000 iterations).
Clearing is safe rather than merely cheap: `bucket_for` seeds its generator from `hash(key)`, so it
is a pure function of hole and board and the memo only ever saved recomputation.
`test_nolimit.py` pins that property and pins that the cap binds.

Three diagnostics were needed because the first two were blind. An object-count histogram showed
nothing growing, because `gc.get_objects()` returns only GC-tracked containers and a dict of
untracked string keys and numeric values is one object whose count never moves. `malloc_trim`
recovered nothing, ruling out freed-but-unreturned pages. Measuring container **lengths** rather
than counting objects found it immediately.

**3. Raise cap 2, if anything external is to improve.****3. Raise cap 2, if anything external is to improve.** This is the untested lever and it is the
one the evidence now points at. It is also expensive: lifting the cap multiplies the betting tree,
and `check_raise_cap.py` already found that lifting it *widened* the internal gap, so this is a
question rather than a plan. Measure the tree size first and decide from that, because a run that
does not fit in memory is how this project lost six hours before.

**4. Two solvers, and the panel still does not move.** `nolimit_strategy.pkl` remains the
100bb 250k solver that every Phase 4 figure was measured against. The 200bb solver is used by the
Slumbot bridge only, through `--strategy`, and is never promoted. Internal comparison is at 100bb,
the external number is at 200bb, and each figure says which.

**5. Phase 5 — six-max.** After heads-up. Needs the `play_match` stack-drift fix, and the CFR
agent cannot serve as a benchmark there, so the panel loses its only opponent from outside the
lineage.

---

## Withdrawn, 8 September: the Phase 4 intransitivity

**It was the panel.** The August finding — that the three families could not be ranked — rested
on two edges taken against the 4,000-iteration solver: PPO level with it (+10.4) while it beat
the evolved genome by +370.1, against a measured PPO-vs-genome edge of only +23.9.

Re-measured on the converged panel, three seeds at 40,000 hands each:

| edge | BB/100 to the first named |
|---|---|
| CFR vs PPO (2M) | +73.5 |
| CFR vs evolution | +200.9 |
| **PPO vs evolution** | **+96.5** — per seed +75.2, +273.3, −58.9, spread 332.2 |

Transitivity predicts +127.4 for the third edge and it measured +96.5 ± 96.5 (SE across seeds).
**The shortfall is a quarter of its own error bar.** Nothing to explain.

The mechanism claimed in August goes with it. "PPO has eliminated the all-in" was stated against
a solver that jammed on 15.0% of decisions; a converged solver jams on **1.6%**, PPO on 0.2%.
The two now raise at 54.3% and 54.9% and PPO's raises are the larger, yet it takes +397.3 off a
calling station to the solver's +603.4. The difference is in *which spots*, which counting cannot
see. Open, not explained.

**Still true:** the two baselines cannot rank agents (see below), so do not quote a ranking taken
from a random or always-call column. That is a weaker claim than the withdrawn one and it is the
one the data supports.

Reproduce: `venv/bin/python scripts/diagnostics/check_intransitivity.py --hands 40000 --seeds 0 1 2`

---

## Closed, 2 September: the solver was under-trained, and it was worth half the gap

The solver that then held `nolimit_strategy.pkl` — now kept as `nolimit_strategy_4k.pkl` —
had **4,000 iterations**, about two minutes of
training at the crossover's measured 32 iterations/second. Retraining the same abstraction for
**150,000** iterations (2h56m) and re-measuring:

| | vs Slumbot | vs the 4k solver | vs random | vs always-call |
|---|---|---|---|---|
| 4,000 iterations | −1750 ± 524 | — | +377.2 | +722.9 |
| **150,000 iterations** | **−987 ± 374** | **+185.0 ± 13** | +280.1 | +827.7 |

**Training was the binding constraint, not the abstraction.** It halved the Slumbot gap and wins
the head-to-head by fourteen standard errors.

**Three things this turned up, all worth keeping:**

**Internal strength overstates external gain by ~2.4x.** +185 ± 13 BB/100 internally became
+76 ± 64 against Slumbot. Beating your own previous agent is evidence about a third party, not a
measurement of one.

**The baselines still cannot rank.** The 150k solver is decisively stronger yet scores *worse*
against random (+280.1 against +377.2). Ranking these two by their random score would have picked
the weaker agent. The baselines rank badly on their own; that much survived the
withdrawal above.

**~~`train_nolimit.py`'s evaluation disagrees with `evaluation.benchmark`.~~ Resolved 8
September** — see [`docs/training-plan.md`](docs/training-plan.md). The cause was
`cfr/play.py`'s `always_call_policy`, which indexed by position in the legal-action list rather
than by abstract action: with nothing to call the list is `[1,2,3,4,5]`, so index 1 is action 2,
**raise half pot**. The "calling station" raised every time checking was free. Every "vs always
call" figure the trainer printed was against a semi-aggressive opponent.

Fixed. The same solver now scores +605.0 through benchmark and +609.9 through `play_hands` — a
gap of 4.8 BB/100, inside noise, against 232.4 before. **The trainer's evaluation is trustworthy
again.**

Found on the way, and also fixed: the traversal game produced decision nodes after an all-in was
called, asking a check/call from players with no chips. Those filler actions extended the
information-set key, so the same hand keyed differently than in the engine. 250,000 iterations
now reach 23,470 information sets rather than 25,154 — the spurious nodes gone. A solver was
retrained for 4h48m expecting this to close the evaluation gap; it did not, and the widening gap
is what led to the baseline bug. `results/cfr/nolimit_strategy_v2_250k.pkl` is the first solver
trained on a game that matches the engine.

### That lever is now spent

At the time this read "more iterations, not less abstraction", and it was right — 4,000 → 150,000
was worth +185 ± 13. It has since been measured to exhaustion: **150,000 → 250,000 bought
+12.3 ± 7**, and information sets reached saturated. On the corrected game 250,000 iterations
reach 23,470 of 49,200, down from 25,154 before the all-in fix removed the spurious nodes.

Roughly half the abstraction is unreachable in practice under this betting tree, so further
iterations refine a fixed set rather than finding new ones. The next gain has to come from
somewhere else — which is why the Now section leads with 200bb.

Two things to fix before any longer run:

- **`train_nolimit.py` prints nothing during training and saves only at the end.** A 500,000
  iteration attempt ran six hours, reached ~4.9 GB, and was killed with nothing written. It needs
  a progress line and periodic checkpointing.
- **Memory, not time, is the ceiling.** The abstraction's table is 4.7 MB; the solver's
  bookkeeping reached 4.9 GB. 150,000 iterations peaked around 1.6 GB, so roughly 250,000 is what
  this machine can hold.

---

## Fixed 2–3 September: the two betting implementations, and what it cost

`training/fitness.py` sized a pot-fraction raise off the pot *before* the call where
`games/nolimit.py` sized it *after* — the standard convention — so every raise in the engine was
about 20% smaller than the same abstract action in the game the solver trains in. Fixed;
`tests/test_betting_equivalence.py` now asserts agreement across the enumerated betting tree
instead of characterising a gap.

PPO trains through that function, so all three seeds were retrained at 8M hands and re-measured.
**The Phase 3 finding survives** — the 2M rung against the CFR agent moved from +394.2 to +393.9 —
but **the seed spreads widened five- to six-fold** (2M vs CFR: 32.5 → 181.8). The number barely
moved; the confidence in it dropped a lot, and the cause is not established. See
[`docs/training-plan.md`](docs/training-plan.md).

**Cost:** `scripts/train_ppo.py` hardcodes its output directory, so the retrain overwrote the
August checkpoints. The pre-fix numbers survive as records; the agents behind them do not.

### Still to do, in order

1. ~~Retrain evolutionary search.~~ **Will not be done.** `preflight_training.py` refuses, and it
   is right: repeatability is r = +0.12 at the real 6,000-hand budget, and giving every genome the
   same cards does not help (spearman +0.01). The genomes are near-indistinguishable, so selection
   sorts noise and three hours would buy nothing. Phase 4's evolution row stays on the old raise
   convention and is marked as such.
2. ~~Re-run Phase 4 once evolution is refitted.~~ The precondition cannot be met — item 1 closed
   evolution as never-to-be-refitted. Phase 4 was re-run without it, on the corrected sizing and
   the six-seed PPO data; evolution's row carries † and stays on the old convention.
3. ~~Re-run Slumbot because the raise fix changed the agent.~~ That reason was wrong — the
   Slumbot pipeline never imports `training/fitness.py`, and `slumbot/bridge.py` already sized its
   raises off the pot after the call. Declining on those grounds was right at the time, and the
   grounds have since changed: **−987 ± 374 is stale now**, because the all-in fix means the
   current solver plays a game the old one did not. See the Now section above.
4. ~~Widen the seed count.~~ **Done** — six seeds, `results/ppo/phase3_endpoint_6seed.json`.

---

## After that

**Phase 5 — six-max.** After heads-up is complete. Note the CFR agent cannot serve as a
benchmark there, so the panel loses its only opponent from outside the lineage. Also needs the
`play_match` stack-drift fix described in [`docs/training-plan.md`](docs/training-plan.md).

---

## Closed — do not reopen without new information

- **Exploitability via LBR.** Four defects and three valuation models in, it still cannot beat a
  converged strategy. Stopped deliberately; the reasoning is in `BACKLOG.md` item 1.
- **Re-running the exploitability crossover.** Superseded by the head-to-head result, which
  answered the same question conclusively in four hours.

---

## The solvers on disk

The arena sets, newest first. Each rung is `<name>.pkl` plus a `.flat.npz`/`.flat.pkl` pair (the
flat tables the bot loads; `cfr/flat.py`), and a `.json` stamp with the recipe.

| set | what | role |
|---|---|---|
| `results/cfr/ladder169l_10m/` | v5's rungs; 50/70/100bb cap-2 at 10M (symlinks into `experiments/`) | **v5b, live for v003** |
| `results/cfr/ladder169l_v6/` | v5b plus cap-2 at 35/25/18/12bb (`ladder169l_short/`) | v6, gated Thursday 05:30 |
| `results/cfr/ladder169l/` | 169-class linear, 3M per rung, texture, 200 samples | v5 (won runner1, mellyy, 13 of 20 house) |
| `results/cfr/ladder200t/` | six Chen classes, vanilla, texture | v3/v4; beaten by v5 at every rung |
| `results/cfr/contender/cap2_200bb.*` | 200bb cap-2, 3M, 169 linear | the Slumbot instrument (−815 ± 357) |
| `results/cfr/experiments/` | cap2_100bb_v7 (four flags; tie), *_10m (the wins), b20, 1M/3M tests, `threads/` | evidence, see the gates |

Gates live beside the sets they judge (`ladder169l/gate_*.json`, `h2h_*.json`). The solver
pickles and flat tables are **not tracked** (hundreds of MB each); the JSON stamps and gates
are. The older single solvers (`nolimit_strategy*.pkl`, the Phase 4 panel opponent at 250k) are
unchanged and still tracked; `nolimit_strategy.pkl` is the corrected 250k one.

---

## Picking this up cold

```bash
venv/bin/python -m pytest -q            # expect 233 passed; collection alone takes ~5 min
venv/bin/python scripts/audit_observation.py   # the 19-feature observation, both table sizes
venv/bin/python scripts/make_figures.py        # rebuilds every figure from the repo alone
venv/bin/python -m gui.main                    # play the CFR agent, through the benchmark's own loop
```

Two conventions worth knowing before starting a long run:

**Checkpoint at 10% of the run**, via `evaluation.checkpoint_every`. Ten saves whatever the
unit.

**Never checkpoint into `/tmp`.** WSL wipes it on restart, and doing so cost 49 minutes of
training on 14 August. Use `~/pokerbot-scratch` or `results/`.

And the habit that matters more than either: **before trusting a number, check its error bar
against the spread of the thing it is measuring.** Three separate results in this project have
looked like findings and been noise, and each was caught by a check that already existed rather
than by a new one.

---

## A note on the history rewrite

On 20 August every commit reachable from `main` was re-hashed, to strip `Co-Authored-By`
trailers. File contents were unaffected — verified by comparing all 104 commit trees against
the pre-rewrite history, with no mismatches — but **every SHA quoted before that date is
dead**. Three references in tracked files were remapped; if an old SHA turns up in a note
elsewhere, resolve it by subject against the current `main` rather than trying to check it out.
