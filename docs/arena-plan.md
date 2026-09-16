# Dealing with the arena drawbacks

Written 13 September 2026, after three exhibition wins on Chipzen and the review
in `results/chipzen/review.md`. The drawbacks are listed in `docs/chipzen.md`;
this is what to do about each, in the order that pays, with what each costs.

One fact shapes the whole plan: **the entry is a remote bot, so it is not
frozen.** The process runs here, and it can be stopped and restarted with a
better solver between fixtures, as long as no match is in progress. So nothing
has to be perfect by Tuesday; it has to be tested before it goes in.

## 1. Off-tree re-raises: the one that leaks chips

The one-raise solver has no entry for a re-raise. 9 percent of decisions across
three matches, 22 percent against the bot that three-bet, all in the big pots.

**Tonight, no risk.** Deep-tree `(4, 2)` companions at every depth the ladder
has, not only 25, 50 and 100bb: 70, 35, 18 and 12 are training now, about seven
minutes each. Below 12bb a re-raise is a shove, which the one-raise tree already
has. This turns nearly every off-tree decision into an equilibrium answer from
a solver of the right depth, instead of the hand-strength rule.

**Properly: the contender plan** (`docs/contender-plan.md`), a deeper main tree
gated on the Slumbot miss rate. It is not swapped in for the arena on the
strength of the gate alone, because the deeper tree exploits weak opponents far
less (+202 against +647 BB/100 off a calling station) and the arena field is
weak. The arena record decides that swap, and only once there are enough rated
matches to read.

## 2. Bucket noise: the one that misreads hands

42 percent of hands land in the wrong strength class because the equity
estimate uses 40 samples. At 200 samples the standard deviation falls from
0.0667 to 0.0307 and the misreads to roughly a tenth of hands.

**The experiment first, tomorrow.** Train the 100bb one-raise solver at 200
samples on the native path (about six minutes instead of seventy seconds) and
play it against the shipped 40-sample solver over 40,000 hands, same tree, so
the head-to-head is clean at about ±13 BB/100. This is `NEXT.md` item 1b, and
it has been waiting for exactly this reason: it changes the abstraction, so it
has to win on its own before anything is retrained on it.

**If it wins: retrain the ladder and the companions at 200 samples**, about
three hours in the background, and swap them in between fixtures. Play-time
bucketing follows the pickle's own sample count, so the bot and its solver stay
consistent. If it does not win, nothing changes and the finding is recorded.

The precomputed equity table (`docs/optimisation-plan.md`) is the better
version of this fix, but the native solver computes equity itself and would
need the table lookup ported into C++. That is a day, and it waits for the
200-sample result to say whether precision moves the needle at all.

## 3. Three bet sizes

Deferred, and deliberately. Widening `NUM_ACTIONS` touches ten files,
invalidates every PPO and evolution checkpoint, and cannot be measured by
anything cheaper than Slumbot's ±400. The arena's field does not punish three
sizes; Slumbot might. It is the last lever, after 1 and 2.

## 4. No opponent model

The arena's own argument is that this is where the field is beaten, and the
bot has none. The honest position is that a bad exploit loses to a good bot and
we cannot yet tell which opponents are which. **What to do now is collect**: the
decision logs already record every opponent action, and after a week of rated
matches `scripts/chipzen_review.py` can say per opponent how often they fold to
a bet, re-raise, or shove. A first exploit, once the numbers exist, would be a
single adjustment with a measured trigger, for example raising the bluff
frequency against an opponent whose fold-to-bet is above a threshold over at
least a hundred hands. Not before.

## 5. The depth ladder's steps

Ten rungs, nearest in ratio. Finer rungs cost a minute each and could go in
tonight, but the review shows no chips lost to a rung boundary yet, so this
waits for evidence. If a lost hand ever traces to a 60bb hand played by the
50bb rung, add 60.

## 6. Unrated

Only the platform's other remote bots can give a rated record, and both
ignored API challenges. The queue is joined automatically whenever the bot is
idle, inbound challenges are accepted, and the rest is the dashboard: a ranked
challenge to `Blueprint` or `RoboPoker`, and tonight's 22:30 remote bracket.

## What was done on the evening of 13 September

After three rated losses to `mr_hide` (nine of eleven showdowns lost), four
fixes, all in the code and tested, with the solvers they need training:

1. **The companion no longer shoves with a middling hand.** Its `(4, 2)` tree
   has only two-times-pot and all-in for a re-raise, so its every raise was a
   shove; now a companion shove with anything below the top strength class is
   taken as a call. (`chipzen/player.py`, `shoves_softened` in the stats.)
2. **A full-size raise-cap-2 solver** (every size on the re-raise) at 100bb,
   200 samples, three million iterations: `results/cfr/ladder200/cap2_100bb.pkl`,
   390,456 information sets, 2h12m native (2.64 ms/iteration with the machine
   shared), +240.5 BB/100 against random and +204.2 against always-call, the
   latter a third of the one-raise solver's +647, which is the exploitation
   given up for knowing what a re-raise means. `--deep-primary` plays it as the
   main solver at its depth; texture-aware copies at 100, 70 and 50bb follow.
3. **Board texture in the bucket.** `abstraction.buckets.board_texture` classes a
   board by flush (two or fewer, three, four or more of a suit) and by four ranks
   within five; the postflop bucket becomes strength plus six times that class.
   Mirrored in the native core (`Abstraction::board_texture`) and pinned equal on
   3,000 random boards by `tests/test_native.py`. Off by default; the panel is
   untouched. A texture-aware ladder is training into `results/cfr/ladder200t/`
   (`--ladder-dir results/cfr/ladder200t` to play it).
4. **A measured opponent profile.** `chipzen/opponents.py` counts, per opponent
   and across matches, how they answer our bets. Below a 25 percent fold-to-bet
   over at least 100 bets, the bot withholds bluffs (a raise with a bottom-two
   strength class becomes a check or call); value bets are untouched. From the
   logs so far: `mr_hide` folds to 14 percent of bets over 105, `hoops` 34
   percent, so the adjustment fires against the first and not the second.

## 14 September: v3 and v4

The texture-aware, 200-sample set with cap-2 primary at 50, 70 and 100bb went
live at 02:55 as **v3**: 20 rated matches against `Blueprint` by 06:07, 13 won,
+47 ± 31 chips per hand. Then nothing until 21:00, for two reasons that are now
fixed: the laptop slept and the lobby socket died silently (a 60-second silence
watchdog reconnects; `EXT_BOT_OFFLINE` from the platform drops the lobby), and
the free tier's 20 challenge matches a day were used by 06:07 (resets 05:30
IST; season fixtures do not count).

The seven Blueprint losses were all one call of its all-in. Blueprint folds to
81 percent of bets and its raises are value; the solver's three-bet-shove nodes
are the thinnest part of its tree. **v4** adds a second measured rule in
`chipzen/opponents.py`: a fold-or-raise bot (calls under half of its non-fold
answers over 100 bets; Blueprint 0.34, the others 0.8 to 0.9) gets its
pot-sized bets called only by the top strength class; and the fallback rule no
longer calls a pot-sized bet with a middling hand. The ledger separates v2, v3
and v4.

## 14 September, later: the preflop abstraction, not the fallback

The eight most expensive hands on record are five solver decisions, two
companion decisions and one fallback; the rule path answered 32 of v3's 1,367
decisions. Reading the shipped strategy directly: KQo, T9s and 77 are one
preflop class (six k-means groups over 27 distinct Chen scores), and at 70bb
that class calls a shove after a two-times-pot open 97 percent of the time,
which is right for TT and AQ and wrong for the KQ that lost two Blueprint
stacks. Preflop has 169 hands and no reason to be clustered at all, so
`preflop_buckets=169` is now lossless, with the coarse class kept behind
`strength_of` so the player's six-class rules keep their meaning. The ladder is
retraining as `results/cfr/ladder169/` on the `ladder200t` recipe, gated by a
40,000-hand play-off per tree before it replaces v4. The v4 rules stay: a
sharper solver narrows the calling range, while Blueprint's never-bluff shove
is still an opponent property an equilibrium does not know.

**Measured, later that night.** The lossless ladder lost the same-tree gate at every
budget: −4.4 ± 1.8 BB/100 on the cap-2 100bb tree at 3M iterations, −5.7 ± 1.5 on the
one-raise tree at 1M against 1M, −15.8 ± 3.8 at 250k against 250k. The gap closes with
iterations and has not crossed. The offline replay (`scripts/chipzen_replay.py`) shows the
lossless 100bb solver folding the hands that lost, so the head-to-head is measuring the
price of tighter play against an opponent whose shoves carry bluffs, not whether the fold
was right against Blueprint. No swap; v4 stays. The set is kept for the container upload
question and for a bigger-budget retrain if the arena record ever justifies one.

## 15 September, v4's quota burst read against the revealed cards

v4 played 25 rated matches, 19 won, **+77 ± 51 chips per hand over 1,693 hands**, 15 of 20
against Blueprint at +62. The big pots turned round: 23 won for +140,822 against 11 lost for
−70,600, where v3's seven Blueprint losses had each been one all-in call. Lookup misses 6.2
percent, 100 of the 140 at two raises on the one-raise rungs below 35bb; the companions
answered 104 and the rule 36.

**The shove-call rule was wrong where it fired most.** The arena reveals the opponent's cards
after a fold, so each of the rule's 70 folds could be judged against Blueprint's actual hand:
Blueprint was behind in 31 of them and calling was better in 48, worth about **184,000 chips**
over the burst, more than v4 won. Sixty of the seventy were preflop at short stacks, where
Blueprint shoves any two cards (K9, J3, A3, K5, 22 among the revealed hands) and the rule
folded KJs at 2bb effective and 33 against 22 at 15bb. Split by effective stack, the rule
left +112,979 on the table under 10bb, +43,382 from 10 to 20bb, and was neutral from 20bb up
(+200 over 34 fires, the turn and river folds all right). The rule now fires only at 20bb and
deeper (`ArenaPlayer.SHOVE_RULE_MIN_BB`), which keeps its deep three-bet-shove purpose and
returns the short stacks to the solver, whose rungs at those depths know the calling ranges.
Fitted on 70 hands against one opponent; the 20 to 30bb boundary is within noise. The bluff
rule fired in four hands for −400 and says nothing yet.

## 15 September: the bridge read every call wrong

The arena sends a call's amount as the increment and a raise's as the level; the bridge read
both as levels. Verified on 3,128 logged calls, none of which carried the level. The pot was
undercounted in 60 percent of decisions and the solver's history key was wrong in 23 percent
(hand 4 against hoops: our pot-sized flop bet keyed as two times pot), the effective stack
shrank inside a hand and dropped the ladder a rung in 97 hands, and the inflated bet fractions
produced most of the logged misses and fallbacks. Fixed the afternoon of 15 September; the
first version that plays with the right pot is v5. Seven short-stack technicalities from the
same audit were fixed alongside, and the two scouted reads went in behind `--scout-reads`.

## 15 September: the season's opponents, scouted from the platform's own records

The platform's page shows nothing about other bots, but its API answers our token with every
match ever played and every hand of any match with both players' cards. `scripts/chipzen_scout.py`
indexes the list once (19,756 matches, cached), pulls a bot's recent matches, and counts from
its seat the same things `chipzen/opponents.py` keeps, plus entry rates, sizing and showdowns.
**Calibration against the three bots we have played:** hoops 34 percent fold-to-bet scouted
against 34 measured, Blueprint 71 against 81, mr_hide 23 against 14 to 18, and the same two
reads either way. The fixtures (`chipzen_run.py --fixtures`, opponent field fixed) and the reads:

| when (IST) | opponent | rating | record | fold to bet | call share | read | what it means |
|---|---|---|---|---|---|---|---|
| Wed 00:10 | runner1 | 1736 on 5 matches | 2 and 3 | 27% (470) | 89% | station with the sequential trigger | never raises (PFR 2%), limps 65%: value-bet, never bluff |
| Wed 01:50 | mellyy | 1929, season 5 champion | 14 and 10 | **76%** (908) | 64% | none | tight and folds to almost everything, 86% to a three-bet: the exploit is more bluffing, which no rule does |
| Thu 00:00 | v003 | unrated | none | | | | never played a hand on record |
| Thu 23:50 | Shadow | 1662, −85 bb/100 | 21 and 33 | 51% (613) | 46% | fold-or-raise | raises 41% of hands, mostly 1 to 2x pot; shove rule from 20bb |
| Fri 23:40 | PoetAndCoder | 1762, +134 bb/100 over 59,000 hands | 2,209 and 1,293 | 24% (966) | 79% | station | plays 78% of hands, folds to nothing, shows down weak hands (mean Chen 4.2) and still wins: bluffs withheld, value thin |

The scouted rows are seeded into `results/chipzen/opponents.json` marked `scouted`, and the
start-up rebuild keeps them as the prior (`Profiles.rebuild`), so the rules can fire from hand
one. Not done, on purpose: a folder exploit for mellyy, because a rule written the afternoon it
plays is how the shove rule went wrong. Our platform record for comparison: 1617, 89 and 54,
+21 bb/100 over 6,898 hands, earned against the same weak field that inflated the others.
Expected scores by rating: 0.33, 0.14, unknown, 0.44, 0.30.

## 15 September: the next levers, coded and flagged off

Four reviews (`docs/research/`) ranked what would move the bot. The pieces that could be
written in a night are in, each behind a flag and unmeasured: postflop purification
(`--purify postflop`), sequential exploit triggers and a bankroll cap
(`--sequential-triggers`, `--exploit-bankroll`), per-history opponent counts for a later
data-biased response (always on), a Slumbot loss split (`scripts/slumbot_split.py`), and
river endgame solving on the exact hand (`--river-solve`, `cfr/river.py`, with
`scripts/river_solve.py` to re-solve logged rivers). Each goes live only after its own gate.

## Order

1. Tonight: companions at every depth (running). Restart between matches.
2. Tomorrow: the 200-sample head-to-head. Retrain and swap only if it wins.
3. Tuesday 05:30 IST: the bot must be running; the machine must not sleep.
4. During the season: the contender plan against Slumbot, in parallel; the
   arena logs accumulate for the opponent question.
5. After the season: the **container upload** (a second rated record on the
   bigger ladder, run on their machines): the play path drops numba in favour
   of the C++ equity function, the process loads only the rungs a match can
   reach and is checked against the 256 MB cap (the remote bot sat at 763 MB
   after two hours on 13 September, unexplained), the image stays under 200 MB
   without llvmlite. Then bet sizes, and an exploit if the logs justify one.
