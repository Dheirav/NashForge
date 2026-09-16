# What to do next

One page, kept current. [`BACKLOG.md`](BACKLOG.md) holds the reasoning and everything closed;
[`docs/training-plan.md`](docs/training-plan.md) holds the full phase plan and its results. This
file is only the next thing to do.

**Last updated:** 14 September 2026 · 338 tests (~7m with the machine shared; collection ~3m24s)

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

**State on Monday 14 September, 21:15 IST.** NashForge is entered in Chipzen season 6 as a
remote bot and is running on this machine as **v4** (`tools/chipzen-progress.sh`): the
texture-aware 200-sample ladder (`results/cfr/ladder200t/`) with full-size raise-cap-2 solvers
playing first at 50, 70 and 100bb, `(4,2)` companions at 12 to 35bb, and two measured opponent
rules (bluffs withheld against a bot that folds to under 25% of bets; a fold-or-raise bot's
pot-sized bet called only by the top strength class). Ledger: `results/chipzen/ledger.md`.
Everything is pushed except the v4 rules (`chipzen/opponents.py`, `chipzen/player.py`,
`tests/test_chipzen_player.py`): commit those first.

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
| 1 | a never-averaged node is exported as an exact uniform: the 50/50 facing a shove, invisible to the miss counter | `native/src/mccfr.hpp` `average_strategy` | export regret matching's current strategy where the sum is zero, or mark the entry as a miss so the companion answers | 1 h | same-tree head-to-head |
| 2 | the export builds a `std::map`, then a dict, then millions of numpy arrays: a 1 GB spike on every write, the memory-kill state twice on 15 Sept | `bindings.cpp:131-136`, `train_nolimit.py:180` | stream to flat arrays | 1.5 h | equality |
| 3 | **done 16 Sept, ladders converted** (ladder169l, ladder169l_v6, contender: 3.2 GB to 263 MB): `cfr/flat.py` (`FlatStrategy`, `load_strategy`), `scripts/cfr/flatten_strategy.py`, `tests/test_flat.py` pins the chip series identical; the three loaders prefer a flat pair newer than its pickle. Convert the ladders (`flatten_strategy.py results/cfr/ladder169l/*.pkl`, one pickle in memory at a time) when the machine is free, then restart the bot on them | every `saved["strategy"]` site | sorted `uint64` keys, `int32` offsets, one `float32` array, behind a `Mapping` shim with `.get` | 6 to 8 h | equality: shim reproduces the dict entry for entry, `benchmark()` chip series identical at a fixed seed |
| 4 | `street_actions` builds a string 4,052 times per iteration; `utility` and `who_folded` copy substrings 210 times | `nolimit.hpp:94-97`, `nolimit_game.hpp:152,185` | `string_view` or a cached street-start index in `State` | 2 h | equality |
| 5 | **done 16 Sept**: refetch removed, golden output identical. The reserve was tried and taken out (1.62 with, 1.65 without, no difference). Speed effect of the refetch itself unmeasured: the audit's 1.43 ms baseline was a six-class-preflop tree, and the 169-class one times at 1.62; a proper A/B against the pre-change module is part of the Thursday sitting | | | | |
| 6 | **done 16 Sept** (memo cap 4,096; golden output identical; `cache_size` still unbound) | | | | |
| 7 | packed keys: 20-char strings hashed per visit | `nolimit_game.hpp:176-178` | `(bucket << 56) \| code` in a `uint64`, 3 bits per symbol, 50 bits of history | 3 h | equality (bijective) |
| 8 | every traverser branch deals its own board: about 91 runouts per iteration, variance, 5x of wasted time | `mccfr.hpp:173-174`, `nolimit_game.hpp:112-148` | one deal per iteration, prefixes revealed | 4 to 6 h | Kuhn −1/18, Leduc exploitability, one same-tree head-to-head |
| 9 | an all-in is scored by one sampled runout: the dominant noise at the shove nodes | `nolimit.hpp:117`, `nolimit_game.hpp:150-174` | preflop by a suit-aware 1,326 x 1,326 table (build once), turn by 44 runouts, flop by 990 | 4 h plus the table | convergence tests |
| 10 | the average accumulates from iteration 1 | `mccfr.hpp` | skip the first part of the run (Pluribus, Modicum) | 0.5 h | Kuhn and Leduc |
| 11 | one thread per solve | `mccfr.hpp` | after 7: pre-sized open-addressed table with CAS insert, per-thread RNG and game, relaxed atomic accumulation | 8 to 16 h | Kuhn with 8 threads; a head-to-head |
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

### After the season, in this order

- **Read `docs/arena-plan.md`** for the drawbacks and what each fix did; **`docs/chipzen.md`**
  for the platform; **`docs/contender-plan.md`** for the deeper tree gated on Slumbot.
- The container upload (a second rated record on the bigger ladder): drop numba from the play
  path via the C++ equity function, load only reachable rungs under 256 MB, image under 200 MB.
  The solver tables are dicts of small arrays at a few hundred bytes each; flat arrays would cut
  the 2.4 GB the v3 set uses to a fifth.
- The cap-2 solvers at 50, 70 and 100bb had 3M iterations over 1 to 2.2 million situations, so
  the rare corners (three-bet shoves) are thinly trained: more iterations there is the cheapest
  strength gain, about 2 hours per rung per 3M iterations.
- Slumbot re-measurement on the contender set (12 h), then the miss-rate gate in the contender
  plan; bet sizes (`NUM_ACTIONS`) last.

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

Four now, and which one is `nolimit_strategy.pkl` has changed, so a figure without a named solver
cannot be placed.

| file | iterations | game | role |
|---|---|---|---|
| `nolimit_strategy.pkl` | 250,000 | corrected (all-in terminates) | **the panel opponent** |
| `nolimit_strategy_v2_250k.pkl` | 250,000 | corrected | same solver, kept under its own name |
| `nolimit_strategy_250k.pkl` | 250,000 | pre-all-in-fix | superseded |
| `nolimit_strategy_150k.pkl` | 150,000 | pre-all-in-fix | produced the −987 Slumbot figure |
| `nolimit_strategy_4k.pkl` | 4,000 | pre-all-in-fix | the old panel; every pre-8-September figure |

All are tracked — `.gitignore` negates `*.pkl` under `results/`, because a solved strategy is a
result and the 4,000-iteration one was once missing from the repository entirely.

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
