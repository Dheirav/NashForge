# Do our copies predict the bots they copy?

5 October 2026, written during the final against Blueprint. Tool: `scripts/copy_validate.py`, tests in
`tests/test_copy_validate.py`, full output in `results/chipzen/copy_validate.md` (with `--detail`) and
`results/chipzen/copy_validate.json`. Everything here comes from the cached scout data on disk: no duels,
no platform calls, no ladder loaded.

## Why this was needed

We pick sets by playing copies: scripted archetypes whose parameters were fitted to a real bot's
scouted frequencies. Fermat1 showed the risk. v5x beat every fermat1 copy, while the real fermat1 beat
our upload bot in both real matches. Until now nobody had checked whether a copy predicts its bot on
hands it was not fitted to, and some copies come from very few hands (Dronev4's from 145).

## Method

**Split by date.** A bot's cached matches (`scout/index.json`, at most its latest 120, and for Blueprint
only those after the 29 Sept rewrite in `profile_since.json`) are sorted by time. The earlier half fits
the copy and the later half tests it. Never interleaved, so a bot drifting over time shows up as error.

**Score the copy at the bot's own decisions.** At every decision the real bot made in a held-out hand,
the archetype's chance of folding, calling or raising is computed exactly from that state, with
`archetypes.action_probabilities` (the archetype's own mirror of `decide`) averaged over eight draws of
its 200-runout equity, so the copy's own noise is included. A statistic's prediction is the sum of those
chances over the nodes that count towards it. That sum is the compensator of the real count: if the bot
really were the archetype, real minus predicted has mean zero for every statistic, including path
statistics like showdown rate. The test file checks this directly. With the generating parameters,
all 15 statistics come out within 1.1 standard errors.

This route was chosen over simulation for two reasons. It is exact and costs seconds (the whole table
runs in 80 s at 270 MB). It also uses the bot's real opponents, while the fit in `fit_archetype.py`
measures the copy playing v5i, which is a different opponent and needs the 4 GB ladder.

**The fit** is `fit_archetype.search` and `distance` over `fit_archetype.COLUMNS`, imported rather than
copied. The search loop was moved out of `main` into `search(start, want, measure_fn, ...)` so a
different measurement can drive it; `fit_archetype.py` behaves exactly as before. The measurement here is
the replay on the training matches, started from the five shapes `tools/panel/choose.py` uses, keeping the
closest.

**Scaling.** Each error is divided by the held-out estimate's standard error, clustered by match because
bots play opponents differently, with a binomial floor. The fidelity score is the RMS of those z-scores,
capped at 10 per statistic. About 1 means the held-out sample cannot tell the copy from the bot.
*Fitted* is the eight columns the fit matches. *Unfitted* is fold to three-bet, raise share by street,
first postflop bet size over the pot, and the share of those bets that are 0.7 pot or more.

**Stability.** The same z-scores between the first and second half of the held-out matches show how much
the bot moved on its own. A copy is flagged "off" when its fitted RMS is over 2 and over 1.5 times the
bot's stability. A bot whose own halves differ by more than 2 is flagged unstable instead.

**Deployed copies.** These are the copies the 2 Oct division duels played, the ones that picked
v5xRR3: `division/fit_<bot>_<base>.md` from `division/run.log`, and `blueprint/fit_new_station.md`. They
are scored on the same held-out matches. Their fits may have seen some of those matches (Blueprint's
used hands from 30 Sept), and that can only flatter them.

## The table

| bot | matches fit / held | held hands | bot stability | refit copy: fitted / unfitted | deployed copy: fitted / unfitted | verdict |
|---|---|---|---|---|---|---|
| Blueprint (since rewrite) | 60 / 60 | 2,792 | 1.1 | 1.7 / 5.2 | **3.8** / 8.1 | refit holds; deployed off |
| Blueprint, fit before rewrite, scored after | 60 / 60 | 2,432 | 1.1 | **7.1** / 5.5 | | copy off |
| Dronev4 | 4 / 3 | 65 | | | 1.2 in-sample on all 7 matches | too few matches |
| fermat1 | 12 / 12 | 598 | 1.3 | **2.2** / 5.1 | **3.2** / 6.0 | both off (thin) |
| PoetAndCoder | 60 / 60 | 1,106 | 0.8 | 1.0 / 7.5 | **4.1** / 9.4 | refit holds; deployed off |
| melly | 32 / 33 | 2,051 | 0.8 | 1.1 / 8.2 | **2.4** / 8.2 | refit holds; deployed off |
| mellyy | 27 / 27 | 2,065 | 0.5 | 1.4 / 6.3 | none | refit holds |
| Shadow | 46 / 46 | 885 | 0.8 | 1.5 / 5.5 | **4.0** / 7.7 | refit holds; deployed off |
| wsp | 60 / 60 | 3,697 | 1.1 | **2.6** / 9.3 | **6.7** / 6.6 | both off |
| RiverReasonBot | 9 / 9 | 316 | 0.6 | 1.9 / 5.4 | **2.3** / 3.1 | refit holds; deployed off (thin) |

Of the 25 other bots with 20 or more cached matches, the refit copy holds for 18 and is off for 7
(hoops 3.0, Fold-ver-3 2.8, r0ckGarden 3.0, RockyPoker 4.8, PluriBot 2.7, LazerTank 2.0, and mr_hide 4.4,
which is also unstable at 2.2). Of the other deployed copies, only v003's holds (1.1). Mimaima699-Pro
(4.3), lil-bot-v2 (4.6), HRT (3.4) and RoboPoker (2.4) are all off. "Thin" means under 600 held-out hands.

## What this shows

**The bots are stable, and the deployed copies are not them.** Every named bot's two held-out halves agree
to within 1.3 standard errors RMS, so these bots do not drift much over a few days. In contrast, the
deployed copy is off for every named bot that has one, at 2.3 to 6.7. Because the bot is stable, the error
belongs to the copy. The same family refitted on earlier matches by replay holds for six of the eight that could be
validated (1.0 to 1.9), which shows the archetype *can* match these columns. The deployed fit misses them because
it matched the bot's field frequencies with the copy playing v5i, and a bot's PFR or fold-to-bet depends
on who it is playing.

**Two things no copy does, refitted or deployed: size bets and bet postflop.** The archetype's first bet
is always two thirds of the pot plus a big blind, so 84 to 99 percent of its bets are 0.7 pot or more.
The bots are far from that. Blueprint's big-bet share is 23 percent, fermat1's 2, melly's and wsp's 0.
At the other end, Shadow, PluriBot and LazerTank bet over the pot (1.2 to 1.3). Postflop aggression is
not fitted at all, and the deployed copies are passive where the bots are not. The flop raise share is
5 percent against Blueprint's 23, 11 against PoetAndCoder's 47, 31 against Shadow's 71, and 6 against
melly's 36. Fold to three-bet is the other big miss. PoetAndCoder folds to a three-bet 0 percent of the
time (30 faced), while both its copies fold 68 to 70 percent, and wsp folds 37 percent against its
copies' 97 to 100.

**The stability check catches a real change.** A Blueprint copy fitted before the 29 Sept rewrite and
scored after it is off at 7.1 (capped stats), which shows the instrument detects a rewritten bot. It
also shows why `profile_since` matters: a copy older than an author's rewrite is a different bot.

## Which copies can be trusted

- **For preflop and fold-to-bet frequencies:** the refit copies of Blueprint, PoetAndCoder, melly,
  mellyy, Shadow and RiverReasonBot (the last thin, at 316 held-out hands). No deployed copy, except
  v003's.
- **For anything that depends on postflop betting or sizing:** none. For every named bot, both copies'
  unfitted RMS is 3.1 to 9.4, and that is structural (fixed sizing, unfitted aggression), not a sampling problem.
- **Dronev4 cannot be validated.** Seven cached matches and 150 hands. In-sample, the deployed copy matches
  its fitted columns at 1.2, but only because the errors are huge. VPIP is 69 against the copy's 57 and
  flop raise share 68 against 36 (z = 5.5 even in-sample).
- **fermat1 and wsp:** both copies are off. Fermat1's copy misses showdown rate (12 against 6 for the
  refit, 21 for the deployed) and sizing (fermat1 bets 0.47 pot).

## What it means for the copy duels that picked v5xRR3

A duel against a copy measures our set against the copy. These numbers say how far the copy is from
the bot, not how far the win rate is from the real one. That second question needs duels, and none
were run tonight. Still, the direction of every big miss is the same: the copies are more passive
after the flop and fold more to pressure than the bots do, which is the shape an exploiter beats most
easily.

- **Blueprint 67.7.** This was played against a copy that is off at 3.8 against a stable bot. It
  three-bets 20 percent (Blueprint 12), raises preflop 28 percent (22), bets the flop 5 percent (23) and
  makes 98 percent of its bets big (23). So 67.7 is a win rate against a preflop-aggressive, postflop-passive
  bot that Blueprint is not. The 14 of 20 burst against the real rewritten Blueprint is the better evidence
  for v5xRR3 here, even at its ±.
- **Dronev4 59.5 to 69.2.** This is a copy fitted to 145 hands, and nothing here can confirm or deny it.
  Treat the never-calls fix's direction as plausible and its +10 as unmeasured.
- **PoetAndCoder 77.5.** The deployed copy is off at 4.1 against a bot with stability 0.8. It folds to
  bets 34 percent (real 24), bluffs the river 20 percent (34), bets the flop 11 percent (47) and folds
  70 percent to a three-bet the real bot never folds to. A set that wins by three-betting light or by
  value-betting into passivity is flattered by exactly these misses. We did win the semi-final, but that
  is one match.
- **fermat1.** This is the case that started the question, and the copy fails in the same direction:
  fermat1 bets small (0.47 pot, 2 percent big) and the copy always bets big, so any read keyed to bet size
  sees a different bot. That is a plausible reason v5x beat every copy and lost both real matches. It is
  not tested.

So the set choice rested on copies that are good on preflop frequency and wrong on postflop play. That
does not overturn v5xRR3, since its real bursts against Blueprint were good, but a copy-duel margin should
not be read as a margin against the bot.

## What to do after the season

1. Refit the deployed copies with the replay objective. It takes seconds and needs no ladder, so the copy
   matches the bot at the bot's own decisions rather than against v5i.
2. Add `raise_share_flop`/`turn`/`river` and `fold_to_three_bet` to `COLUMNS`. Add a bet-size parameter to
   the archetype in place of the fixed 0.66, and to `action_probabilities`'s caller, since the river oracle
   relies on the two agreeing.
3. Re-run the division duels against the refitted copies, one heavy job at a time. A set's lead on a copy
   should count only where that copy's held-out fitted RMS is under about 2.

## Limits

The replay is a one-step check. It scores the copy at states the bot actually reached against its real
opponents, so it says nothing about states only our exploiter steers into. Showdown rate is scored through
the bot's folds, which keeps it exact but makes it partly a second fold statistic. Hands without the bot's
hole cards (171 of PoetAndCoder's) and the few cached multi-seat tournament matches are left out. Stack
sizes are rebuilt from the action records, and they only affect the copy's bet-size cap and short-stack
shove.
