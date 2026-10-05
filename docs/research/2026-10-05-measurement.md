# Review: deciding which version is better, faster and more reliably

Written 5 October 2026 from a literature search and a read-only look at the match logs
(`results/chipzen/matches/`, 545 files, 27,826 logged hands). Nothing was run. Anything
marked inference is the reviewer's arithmetic, not a published result.

## 1. How the current measurements mislead, and by how much

**A burst is decided by a handful of all-ins.** Today's burst was -19 ± 68 chips/hand over
572 decision hands, so the whole deficit is about 10,900 chips, while the three worst hands
cost about 22,800 between them. Remove those three and the burst is clearly positive. If ±68
is a standard error, the per-hand standard deviation is about 1,600 chips (inference), and
most of it is runout luck on stacks that went in. A heavy tail also makes the ± itself
unstable: the next burst's error bar depends on whether it happened to contain big pots.

**Inference: a 20-match headline cannot separate versions that differ by a realistic amount.**
At a per-hand standard deviation of 1,100 to 1,600 chips, resolving a 50 chips/hand
difference at two standard errors needs about 3,000 hands, roughly 100 matches or five days of
quota, for one version. Match win rate is worse: ±11 points per burst means the difference
between two versions carries about ±16, so a true 10-point gap needs about ten bursts each.
The "believe a set after 2 or 3 bursts" rule is the right instinct, but by itself it only
catches large effects.

**Peeking inflates the error rate.** Deciding after each burst whether to keep, revert or
continue is a sequential test run with a fixed-sample threshold. Armitage, McPherson and Rowe
showed that testing at 5 percent after each of 5 looks gives a false-positive rate of about
14 percent, and after 10 looks about 19 percent. That is documented. Reading eight
decomposition rows per burst adds a second multiplicity: if the rows were independent, about
one burst in three would show some row past two standard errors by chance (inference; they are
correlated, so the true figure is lower but not small).

**Version is confounded with opponent mix.** Each burst meets whoever the matchmaker serves,
and authors rewrite their bots (the `profile-since` commit exists because of one). Two
versions measured on different days against different opponents are not a paired comparison.
This is inference, but it is the same failure as comparing learning curves against different
panels.

**Copies are fitted to marginals, and the exploits key on conditionals.** `fit_archetype.py`
matches eight frequencies (VPIP, PFR, three-bet, fold to bet, and so on). A real bot that folds
40 percent to bets folds particular hands on particular boards; a scripted copy that folds 40
percent folds whatever its rule says. An exploiter tuned against the copy learns the copy's
correlations, which is why copies flatter exploiters (inference, consistent with v5x beating
every fermat1 copy). The fermat1 evidence itself is two real matches: a 60 percent favourite
loses both 16 percent of the time, so it is a warning, not a measurement. The larger point is
that a duel's ±0.3 to 0.5 points is sampling error against the copy, and the model error of
the copy is unmeasured and almost certainly bigger. Dronev4 fitted from 145 hands has
fit uncertainty on every column of several points; `target(..., bootstrap=seed)` already
exists to show it and is the cheap first look.

**Instrumentation bugs dominate when they happen.** The decomposition bug moved every row by
+100 to +190 chips/hand, larger than any version effect we have measured; two independent
computations of the same number (stack difference against payouts) is the defence. The replay
counts only the first divergence and the platform rating carries about ±60 after 100 matches,
so neither is read as strength.

Published context for scale. Libratus played 120,000 hands with mirrored deals and won by 147
mbb/game. DeepStack played about 44,000 hands; AIVAT with its own value network cut the
standard deviation by 85 percent and put 486 mbb/g more than 20 standard deviations from zero,
where the raw 492 mbb/g was about four. Pluribus played 10,000 hands and still needed AIVAT to
report 48 ± 25 mbb/game. Teams with full control of the deal still treated tens of thousands
of hands as the minimum, and the ones with fewer hands leaned on variance reduction.

## 2. One thing the logs make possible

Every round result logs the winner's cards, and showdowns log both. So the opponent's cards
are known on every showdown and on every hand we folded (7,574 of the 23,951 hands containing a
fold), but not on hands the opponent folded. Every all-in that was called reached showdown, so
both hands are known exactly where the variance is largest.

## 3. Instruments, ranked by error removed per engineering day

**1. All-in equity adjustment, then AIVAT, on the arena logs.** First step, half a day: for
every hand where the stacks went in before the river, replace the realised result with
equity times the pot, computed from both known hands over the remaining board. This is an
exact chance control variate, a special case of AIVAT's chance correction, and it is unbiased.
It removes the runout luck on precisely the 7,600-chip hands. Second step, three to five days:
full AIVAT using the blueprint's values for each of our hands at each public state, plus our
own action probabilities from the solver that decided (the logs carry solver, history and
legal mask, which the replay already shows is enough for a lookup). Effect on a 20-match burst:
documented reductions are more than 10x in hands needed (Burch et al.), an 85 percent cut in
standard deviation for DeepStack, and a median 54x variance cut for weak LLM agents (Li et al.,
2026). Our value function is a coarser blueprint, stacks vary, and opponent cards are hidden
on hands they folded, so inference: expect the ±68 to fall to somewhere between 20 and 35
chips/hand, and possibly more after the all-in step alone. The first step can be measured on
the 545 logged matches before anything is built further. One rule from Kim and Sandholm
(2026): the value function is fixed before the data it scores is seen, or the variance can be
tuned away and the test p-hacked. So freeze it per season and record its hash in the ledger.

**2. A sequential stopping rule for bursts.** One day. Before a version plays, write down
H0 (no better than the incumbent) and H1 (for example +40 chips/hand after adjustment), then
after each burst update an always-valid statistic: Wald's SPRT if the per-hand variance is
treated as known, or a mixture SPRT or confidence sequence (Johari et al.; Waudby-Smith and
Ramdas) if not. Fishtest decides Stockfish patches exactly this way, with fixed bounds and a
paired-game model. This does not shrink one burst's error; it makes the decision honest under
daily peeking and, because an SPRT stops early on clear cases, typically needs about half the
fixed-sample size on average. It turns "two or three bursts" into a rule that says when to stop
and what the error rate is. Combined with instrument 1, inference: most version decisions
would close in one or two bursts instead of being guessed after three.

**3. A copy-validation table.** One to two days, mostly reusing existing duel outputs. For
every opponent with a copy and at least 10 real matches against us, record what the copy
predicted (chips/hand and match win for the set we actually played) beside what the real
matches gave, with the real standard error. Then compute z = (real minus predicted) divided by
the real SE. If copies are calibrated, those z scores look like a standard normal; a mean below
zero is the flattery bias, and its size is the model error to add to every duel's ±0.3. Fit on
matches before a date and test on matches after it, so the copy is not scored on the hands it
was fitted to, and use the existing bootstrap to give each copy a fit spread. This is a
posterior predictive check in Gelman's sense. It does not shrink a burst's error, but it tells
us how many arena bursts a 20,000-match duel is worth, which today is unknown and probably
close to zero for strong opponents.

**4. A Bradley-Terry ladder with partial pooling.** One to two days. Model each match result
(or AIVAT chips) as version strength minus opponent strength, with each version's strength
drawn around its parent's because every label changes one thing. TrueSkill is the online
version of the same idea. This handles opponent mix, since a version that met harder opponents
is credited for it, and shrinks a noisy new label toward its parent until the data moves it.
It does not reduce a single burst's noise, but it stops the opponent pool from being read as a
version effect, and it gives the "is v7b better than v7" question one posterior instead of two
headlines.

**5. Off-policy evaluation of a new set on logged hands.** Three to five days, and currently
blocked. Bowling et al. (2008) evaluate a different strategy from logged play by importance
weighting our action probabilities, with variance-reducing tricks that use what the opponent
could have held. It needs the logged policy to put probability on whatever the new set would
do. The live set is purified (`purify: all`, most probable action everywhere), so on any
divergence the weight is zero and the estimate is undefined. Inference: if this matters, play
a small exploration share (say 5 percent sampled from the full mixed strategy) on rated
matches, which costs a little strength and buys an unbiased estimate of every candidate set on
every logged hand. Until then the replay is the right tool and it only reports agreement.

Left out: duplicate deals are impossible on the arena (we do not control the deck), and LBR,
the cross-tree gate and Slumbot answer "is it broken", not "is it better against this pool", so
they stay as gates.

## Recommended order

All-in adjustment on the existing logs first, because it is half a day and it alone tells us
how much of the burst error was runout luck. Then the sequential rule, so the next version is
decided by a written stopping rule rather than a headline. Then the copy-validation table,
before any further exploit set is built on a copy. Full AIVAT and the pooled ladder after
the playoffs. Off-policy evaluation only if we accept an exploration share.

## References

- Burch, Schmid, Moravčík, Bowling. AIVAT (AAAI 2018). https://arxiv.org/abs/1612.06915
- Moravčík et al. DeepStack (Science 2017), AIVAT 85 percent standard deviation cut. https://arxiv.org/abs/1701.01724
- Brown, Sandholm. Libratus (Science 2018). https://www.science.org/doi/10.1126/science.aao1733
- Brown, Sandholm. Pluribus (Science 2019). https://www.science.org/doi/10.1126/science.aay2400
- Kim, Sandholm. Heuristic pathologies in the AIVAT family (2026). https://arxiv.org/abs/2605.14261
- Li, Chen, Huang. AV-AIVAT, anytime-valid stopping (2026). https://arxiv.org/abs/2608.06362
- Zinkevich, Bowling, Bard, Kan, Billings. Optimal unbiased estimators (DIVAT line, ICML 2006). https://dl.acm.org/doi/10.1145/1143844.1143974
- White, Bowling. MIVAT (IJCAI 2009). https://mlanthology.org/ijcai/2009/white2009ijcai-learning/
- Bowling, Johanson, Burch, Szafron. Strategy evaluation with importance sampling (ICML 2008). https://dl.acm.org/doi/abs/10.1145/1390156.1390166
- Johari, Koomen, Pekelis, Walsh. Always valid inference (Operations Research 2022). https://dl.acm.org/doi/10.1287/opre.2021.2135
- Ramdas, Grünwald, Vovk, Shafer. Safe anytime-valid inference (Statistical Science 2023). https://arxiv.org/abs/2210.01948
- Fishtest mathematics (SPRT, pentanomial pairs). https://official-stockfish.github.io/docs/fishtest-wiki/Fishtest-Mathematics.html
- Armitage, McPherson, Rowe. Repeated significance tests (JRSS A 1969). https://doi.org/10.2307/2343787
- Herbrich, Minka, Graepel. TrueSkill (NeurIPS 2006). https://www.microsoft.com/en-us/research/publication/trueskilltm-a-bayesian-skill-rating-system/
- Gelman, Meng, Stern. Posterior predictive assessment (Statistica Sinica 1996). https://www3.stat.sinica.edu.tw/statistica/j6n4/j6n41/j6n41.htm
