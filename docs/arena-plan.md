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

## Order

1. Tonight: companions at every depth (running). Restart between matches.
2. Tomorrow: the 200-sample head-to-head. Retrain and swap only if it wins.
3. Tuesday 05:30 IST: the bot must be running; the machine must not sleep.
4. During the season: the contender plan against Slumbot, in parallel; the
   arena logs accumulate for the opponent question.
5. After the season: bet sizes, and an exploit if the logs justify one.
