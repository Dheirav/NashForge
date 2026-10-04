# A stopping rule for bursts

Written 5 October 2026. Code: `evaluation/sequential.py` (the method) and `scripts/burst_verdict.py`
(the reader). Tests: `tests/test_sequential.py`, 14 tests, 13.5 s.

## The problem it fixes

We decide after every burst whether to keep a set, revert it or play another burst. That is a
sequential test, but we have been reading it with fixed-sample thresholds, and a fixed test read
repeatedly is not at its nominal level. The test file measures this directly: a two-sided z-test
at 1.96, read after each of ten 20-match bursts of a fair coin, called a winner in 19.9 percent of
2,000 runs. Five looks give about 14 percent (Armitage, McPherson and Rowe 1969). So "believe a set
after 2 or 3 bursts" was right to ask for more than one burst, but it had no stated error rate.

## The method

Every interval the script prints is a **confidence sequence**: it covers the true value at every
sample size simultaneously with probability 95 percent, rather than at one sample size fixed in
advance (Howard, Ramdas, McAuliffe and Sekhon 2021). This is the property that makes peeking free,
because a verdict that is only ever read off a time-uniform interval cannot be inflated by reading
it more often. The cost is width: at 20 matches the interval is noticeably wider than a t-interval.

**Match win rate.** A match is won or lost, so each version's rate is a Bernoulli parameter. The
interval is the set of rates not yet rejected by a beta-binomial mixture likelihood ratio (Robbins
1970; the conjugate case in Howard et al. 2021). Against 50 percent this is exactly the mixture
SPRT of Johari et al. 2017. I chose it over a betting sequence because the Bernoulli likelihood is
known exactly, so the mixture is closed form and deterministic, while betting earns its keep on
bounded data of unknown shape. The mixing prior is Beta(5, 5), fixed from simulation before any
match log was read. Any fixed prior keeps the guarantee; this one puts its mass where arena win
rates sit, and it found a true 60 percent rate in 57 percent of simulated 200-match runs, against
47 for the uniform prior.

Two versions are compared by running each sequence at 2.5 percent and differencing the intervals.
By the union bound the pair holds at 5 percent. This is conservative, but it needs no pairing or
interleaving of the two versions' matches, which matters because our bursts are played on
different days against different opponents.

**Chips per decision hand.** This uses the hedged betting confidence sequence of Waudby-Smith and
Ramdas (2024). It assumes only that a hand's net is bounded and that its conditional mean is
constant, and it adapts to the observed variance, so a run of small pots tightens it quickly while
an all-in costs what its size warrants. A sub-Gaussian bound would instead charge the all-in
variance on every hand.

**Clipping.** By default nothing is clipped. No hand can move more than the effective stack, and
at Chipzen's 10,000 starting stacks the effective stack is at most 10,000, so the bound is
±10,000 and the interval is for the true mean. `--clip 2000` gives a tighter interval, but for the
mean of the *clipped* nets, which is a different number because it discounts exactly the all-ins
that decided v6. The script prints the clip and how many hands it touched next to every chips
line. Per-hand nets are stack after minus stack before, as decompose has computed them since 2
October.

## The guarantee, and where it stops

At alpha 0.05, if the two versions are truly equal (or a version is truly at 50 percent), the
probability that the script *ever* prints a verdict, however often it is read, is at most 5
percent. The simulations in the test file confirm it:

| check (seeded) | runs | false verdicts |
|---|---|---|
| fair coin, read every 20 matches to 200 | 2,000 | 1.5% |
| fair coin, read after every match to 200 | 2,000 | 2.9% |
| two equal versions, 200 matches each | 1,000 | 0.1% |
| chips, zero mean with 3% all-ins, 600 hands | 120 | 0% |
| fixed z-test, read every 20 matches (the old way) | 2,000 | 19.9% |

A version at a true 70 percent is detected against 50 percent in 99.9 percent of runs by 200
matches, at a median of 47 matches (quartiles 31 and 70). A true 60 percent is found by 200
matches only 55 percent of the time, which is the honest size of a ten-point effect.

Three things the guarantee does not cover. First, it is about the versions on the opponents they
actually met. When two versions met different opponents, the difference interval is partly an
opponent difference, and the script says so. Second, the chips sequence assumes a constant
conditional mean, while within a match the mean shifts with depth and with an adapting opponent,
so read it as a guarantee on the average. Third, each line printed is its own test at 5 percent.
Reading four lines and acting on whichever one fires is a multiplicity again; decide in advance
which line is the decision (the match win rate difference, since the rating moves on it) and treat
the rest as context.

## How to use it after each burst

1. After a burst, run
   `venv/bin/python scripts/burst_verdict.py --label <new> <old>` (add `--opponent X` to restrict
   to one opponent).
2. If the decision line says **"A better"** or **"B better"**, act on it. That verdict is valid
   now, whenever "now" is.
3. If it says **undecided**, play another burst. Do not stop because the estimate looks good: the
   interval already accounts for that, and an undecided verdict means the evidence is not there.
4. The **"estimate: about N more"** figure assumes the future arrives at exactly the observed rate.
   It is for planning only and can be off by several times at small n, because the observed rate
   itself is noisy. It is not part of the guarantee.
5. Abandoning a comparison is always allowed. Stopping without a verdict never creates a false
   positive; only acting on an undecided line as if it were a verdict does.

## Real data, 5 October

Read from `results/chipzen/matches/` and `~/pokerbot-scratch/chipzen/matches/`, rated matches only,
outcomes from `run.log`. v5xRR3 purified: 22 matches, 16 won, 840 decision hands, against Blueprint
20, melly 1 and PoetAndCoder 1. balanced-next: 20 matches, 10 won, 572 decision hands, against
hoops 9, mr_hide 6 and r0ckGarden 5.

| comparison | estimate | 95% anytime-valid interval | verdict |
|---|---|---|---|
| v5xRR3 purified win rate vs 50% | 72.7% | 41.8% to 91.3% | undecided (estimate: about 22 more matches) |
| balanced-next win rate vs 50% | 50.0% | 22.9% to 75.8% | undecided (observed rate equals 50%) |
| v5xRR3 purified minus balanced-next, win rate | +22.7 points | -38.6 to +71.9 | undecided (estimate: about 188 more matches each) |
| v5xRR3 purified vs Blueprint only, win rate | 70.0% (14 of 20) | 38.7% to 91.3% | undecided (estimate: about 37 more matches) |
| v5xRR3 purified chips/hand, no clip | +116 | -30 to +270 | undecided (estimate: about 15 more matches) |
| balanced-next chips/hand, no clip | -19 | -230 to +190 | undecided |
| difference, chips/hand, no clip | +135 | -280 to +539 | undecided (estimate: about 156 more matches each) |
| v5xRR3 purified vs Blueprint only, chips/hand | +98 | -50 to +270 | undecided |
| difference, chips/hand, clip ±2,000 | +71 | -88 to +260 | undecided (36 and 48 hands clipped) |

Nothing is decided yet, which is the expected outcome at one burst each. The comparison between
the two versions is also confounded, because v5xRR3 purified met Blueprint in 20 of its 22
matches while balanced-next never met Blueprint at all, so its +22.7 points is partly an opponent
difference that these intervals cannot separate from the version difference. The cleanest next step is the same opponent mix
for both, and then the decision line should be read after each burst until it fires.
