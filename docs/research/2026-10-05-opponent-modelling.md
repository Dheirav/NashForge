# Opponent profiles: getting reads right on small, shifting samples

Written 5 October 2026 from `chipzen/opponents.py`, the two 15 September research notes,
`~/pokerbot-scratch/profiles-clean/report.md` and a literature search. Nothing was run. Where a
claim comes from a paper it is cited; where it is my own inference it says so.

## 1. What is wrong with the current rules

**Several rules put the threshold at the null itself (inference, from the code).** `never_calls`
fires when the point call share over 40 answers is below `CALL_FLOOR` = 0.5, and an equilibrium-ish
bot sits near 0.5. A bot that truly calls half the time therefore fires the read about half the time
by sampling noise alone. That is exactly the Dronev4 case (calls 46 to 48 percent), and moving the
floor to 35 percent fixed the symptom rather than the cause. `fold_to_bet`, `folds_blind`,
`folds_to_three_bet`, `never_bluffs` and `never_three_bets` are the same shape: a minimum count, then
a point rate against a threshold, with no account of how far the rate sits from the threshold
relative to its noise.

**The bounds that do exist are Wald intervals.** Wald collapses to zero width at a rate of 0 or 1,
which is where most reads live ("never bluffs", "never three-bets"), and it is known to undercover
badly for small n and extreme p (Brown, Cai and DasGupta 2001). A Wilson or Beta-posterior interval
fixes that at no cost.

**Counts are not independent trials (inference).** Bets inside one match share the opponent's
version, the blind level and our own strategy, so they are clustered. With roughly 15 bets per match
and even a modest within-match correlation of 0.1, the variance is inflated by about 1 + 14 x 0.1 =
2.4, which means Dronev4's 105 bets from 7 matches carry closer to the information of 45 independent
bets. The effective sample is nearer to matches than to bets.

**Many reads on many bots (inference).** Eight yes/no reads and three floors across about 37 bots is
around 400 checks per rebuild. Even a rule with a true 2.5 percent false-fire rate per check would be
expected to fire about 10 wrong reads somewhere in the file, and the point-rate rules above are far
looser than 2.5 percent near their thresholds. Most false fires land on bots we never meet, which is
why this has been cheap so far, but the one that lands on a finalist costs real chips.

**A true frequency can still license the wrong action.** Shadow's never-calls read lost 19,896
chips over 12 firings. The read assumes that a bot which rarely calls has raises that mean it. The
15 September analysis measured Shadow's concordance at 0.60, raising flop bets with mean equity 0.50:
its actions barely depend on its hand. So the frequency could be right and the inference from it
still wrong. Reads should be checked against hand strength at showdown, not only against
frequencies, because that is what the action they trigger depends on.

**How much the double counting mattered.** Duplicating counts by a factor k shrinks every interval by
the square root of k. wsp was 5.3 times inflated (30,892 against 5,865), so its intervals were 2.3
times too narrow; Blueprint 4.0 times, so 2 times too narrow. That turned borderline reads into
confident ones, and the clean rebuild changed 61 reads and thresholds across 37 bots, including
Shadow's never-calls (the expensive one) and folds_blind flips on HRT, Shadow and lil-bot-v2. So the
inflation changed decisions, not only confidence. For the opponents left this season the clean
report finds no yes/no read change on PoetAndCoder, Blueprint or Dronev4; PoetAndCoder's river
bluff-catch floor moves from 0.288 to 0.31. The damage was done earlier in the season and is mostly
behind us, but the same rules on the next season's field would repeat it.

## 2. Options, ranked by value per day

### Option 1. Beta and Dirichlet posteriors with a population prior (1 day)

Replace each rate with a posterior. For each read, fit a Beta prior across all profiled bots by
method of moments (empirical Bayes, as in Efron and Morris's batting averages, where shrinking to the
league mean was about three times more efficient than raw averages), and for `by_history` use a
Dirichlet per public history whose mean is the population's action mix at that history. A bot with
105 bets is pulled most of the way to the field; one with 5,000 is barely moved. Count by match, or
discount bets by the design effect, so clustering is respected. Fire a read when the posterior
probability that the rate is past the threshold exceeds, say, 0.95, rather than a point rate.

This is what Southey et al. (2005) do in Bayes' Bluff, with a prior over strategies updated by
observed play; Ganzfried and Sandholm's DBBR (2011) uses a Dirichlet prior centred on the equilibrium
with a pseudo-count of about 5. The population prior is my substitution: our field is not near
equilibrium, so the field's mix is the better centre.

Measurement: offline, no chips. Split each bot's matches by date, fit on the first half, score the
log loss of predicting the second half's actions under the raw rate, the Wald rule and the
posterior. Then list every read that flips against the clean file, and run a decision audit over
logged hands: how many decisions each flipped read would have changed, and what those hands went on
to win or lose at showdown.

### Option 2. A gate per read: false-discovery budget and copy A/B before enabling (half a day, plus duels)

Two parts. First, treat the read file as a family of tests and control false discoveries
(Benjamini and Hochberg 1995): rank the reads by posterior tail probability and allow, say, one
expected false fire across the file. Second, a read is enabled for an opponent only after an A/B on
its copy: copy duels of 10,000 to 20,000 matches with the read on and off, ±0.3 to 0.5 points. A
read that does not move the copy by more than its interval stays off.

Caveat (inference): the copies are fitted from the same scouted hands as the profile (Dronev4's from
145 hands), so a copy duel cannot show that a read is wrong about the real bot, only that the action
it triggers pays against the behaviour we believe. That is why the decision audit from option 1
comes first and an arena burst of 20 matches (±11 points) comes last, read decomposed by
`scripts/chipzen_decompose.py` and believed only after two or three bursts.

### Option 3. Automatic change-point detection in place of the manual cutoff (1 day)

Run Bayesian online changepoint detection (Adams and MacKay 2007) or a two-sided CUSUM (Page 1954)
per bot, on match-level summaries inside fixed preflop situations: small-blind open rate at a given
depth, fold to a flop bet, river bet rate. Fixed situations matter, because the Shadow drift scare
came from pooling different preflop spots. When the run-length posterior puts most of its mass after
a date, propose a `profile_since.json` entry for a human to accept; do not let it rewrite the file on
its own the night of a match.

Measurement: a backtest. It should find Blueprint's 29 September rewrite (small blind 35 percent to
over 90) within a handful of matches, raise no alarm on Shadow, and the false-alarm rate across the
other bots per month of matches should be counted. All offline.

### Option 4. Data-biased response fed by the by_history counts (3 to 5 days, overnight compute)

Use the counts directly instead of turning them into yes/no rules. DBR (Johanson and Bowling 2009)
solves a game where the opponent is pinned to its observed frequencies at each information set with
a weight that rises with the count there, and is free elsewhere; it performed well across
observation quantities, where frequentist best response was brittle and restricted Nash needed far
more data. Feeding it the option 1 posteriors rather than raw counts is my addition, and it addresses
DBBR's reported failure in unvisited nodes, where the prior filled in badly.

Cost: per-opponent solves overnight, warm-started from the blueprint, one file per opponent, and the
memory budget allows one heavy job at a time. Measurement: copy duels of 10,000 to 20,000 matches
against both the blueprint and the current rule set, plus an exploitability check on each response,
then bursts. Worth it only for opponents met repeatedly.

### Option 5. Portfolio with online selection (2 days on top of option 4)

Implicit modelling (Bard et al. 2013), the approach behind the later Hyperborean entries, keeps a
few robust responses and picks among them online with a bandit, which needs no per-opponent model at
match time. With 50-hand matches, there are too few hands for the bandit to learn inside a match, so
it would have to learn across matches per opponent name. Later, if at all.

## 3. Recommendation

Do nothing to the live set before tonight's final. Afterwards, option 1 and option 2 together are
about two days and change nothing structural: they replace thresholds with posteriors and put a gate
in front of each read. Option 3 removes a manual step that has already been needed once. Option 4 is
the real step from rules to a model, and it should wait until the counts feeding it are trusted,
which is what options 1 and 3 buy.

## References

- Southey et al., Bayes' Bluff: Opponent Modelling in Poker, UAI 2005. https://poker.cs.ualberta.ca/publications/UAI05.pdf
- Johanson and Bowling, Data Biased Robust Counter Strategies, AISTATS 2009. https://proceedings.mlr.press/v5/johanson09a.html
- Johanson, Zinkevich and Bowling, Computing Robust Counter-Strategies, NIPS 2007. https://poker.cs.ualberta.ca/publications/NIPS07-rnash.pdf
- Ganzfried and Sandholm, Game Theory-Based Opponent Modeling in Large Imperfect-Information Games, AAMAS 2011. https://dl.acm.org/doi/10.5555/2031678.2031693
- Ganzfried and Sandholm, Safe Opponent Exploitation, 2015. https://www.cs.cmu.edu/~sandholm/safeExploitation.teac15.pdf
- Ganzfried and Sun, Bayesian Opponent Exploitation in Imperfect-Information Games, 2016. https://arxiv.org/abs/1603.03491
- Bard et al., Online Implicit Agent Modelling, AAMAS 2013. https://poker.cs.ualberta.ca/publications/AAMAS13-modelling.pdf
- Adams and MacKay, Bayesian Online Changepoint Detection, 2007. https://arxiv.org/abs/0710.3742
- Page, Continuous Inspection Schemes (CUSUM), Biometrika 1954. https://doi.org/10.1093/biomet/41.1-2.100
- Benjamini and Hochberg, Controlling the False Discovery Rate, JRSS B 1995. https://rss.onlinelibrary.wiley.com/doi/10.1111/j.2517-6161.1995.tb02031.x
- Brown, Cai and DasGupta, Interval Estimation for a Binomial Proportion, Statistical Science 2001. https://doi.org/10.1214/ss/1009213286
- Efron and Morris, Data Analysis Using Stein's Estimator and its Generalizations, JASA 1975; field test in Brown 2008. https://projecteuclid.org/journals/annals-of-applied-statistics/volume-2/issue-1/In-season-prediction-of-batting-averages--A-field-test/10.1214/07-AOAS138.pdf
