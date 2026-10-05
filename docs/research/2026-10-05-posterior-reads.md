# Posterior reads: option 1 of the opponent-modelling note, built and checked offline

Written 5 October 2026 on branch `profile-posteriors`. This implements option 1 of
`2026-10-05-opponent-modelling.md` behind a switch that is off by default
(`Profiles(posteriors=True)`, `chipzen_run.py --posterior-reads`, `--posterior-reads` in a
`chipzen_duel.py` flag string). Nothing here was played on the platform: every number comes from
the scout cache, today's clean profile file and our own match logs, all read from the main tree.

Reproduce with `scripts/posterior_reads_eval.py` (`cache`, then `icc`, `predict`, `audit`,
`decisions`). The cache stage took 57 seconds for 2,649 matches and the decision audit 25 seconds.

## 1. Method

**What each read decides on.** Every read keeps its own minimum count (the sequential one where it
has one) as the "have we seen this bot" gate, and then fires on a one-sided 95 percent posterior
bound against its existing threshold, instead of the point rate or the Wald bound. The thresholds
are unchanged, so the change is only in how sure the read has to be. The minimums stay because the
posterior of an unseen bot is the prior itself, and a prior alone must never fire a read.

| read | rate | fires when |
|---|---|---|
| `never_folds` | fold to bet | upper < 0.40, from 40 bets |
| `never_calls` | calls / (calls + raises) | upper < 0.35, from 20 answers |
| `folds_blind` | fold to our open (`preflop:Ur`) | lower >= 0.70, from 100 |
| `never_three_bets` | re-raise of our open (`preflop:Ur`) | upper <= 0.04, from 120 |
| `folds_to_three_bet` | fold to our three-bet (`preflop:TrUr`) | lower >= 0.75, from 25 |
| `never_bluffs` | river bluff share | upper < 0.05, from 40 |
| `big_bets_are_value` | big-bet air, small-bet air | upper < 0.05 and lower >= 0.20, from 100 each |
| `river_bluff_floor`, `reraise_floor` | as named | returns the lower bound |
| `postflop_fold_floor` | flop and turn folds | lower bound, None if the raise share's upper bound > 0.15 |

`river_never_bluffs` is left alone. An exact zero over a hundred river bets is its own test, and
the player asks it only after `never_bluffs`, which is now on the bound.

**The posterior.** Each rate gets a Beta prior fitted from every row in the file by method of
moments (empirical Bayes). The spread of the bots' observed rates is part real difference and part
sampling noise, so the noise (the mean of mu(1 - mu) / n_eff) is subtracted, and what is left is the
between-bot variance, which gives the prior's strength. Bots are weighted equally, because the prior
is a statement about what a bot is, not about what a hand is. A bot enters the fit with at least 20
effective trials and the fit needs four bots. Strength is held between 2 and 50: the floor stops a
very mixed field from fitting a prior of nothing, which would leave the zero-count reads with the
zero-width bound Wald had, and the ceiling stops a field that happens to look alike from swamping a
real outlier. The posterior is then Beta(mu S + s / d, (1 - mu) S + (n - s) / d), with d the design
effect below.

**The within-match correction, measured rather than guessed.** The research note assumed a
correlation of 0.1. I measured it instead: the per-match counts of every cached scout match, run
through `chipzen_scout.profile` one match at a time, and the ANOVA estimate of the intraclass
correlation per bot, pooled weighted by trials.

| rate | bots | pooled rho | median rho | trials per match |
|---|---|---|---|---|
| fold to bet | 31 | 0.035 | 0.028 | 29.8 |
| call share | 31 | 0.028 | 0.027 | 18.1 |
| fold to open | 30 | 0.071 | 0.029 | 11.5 |
| re-raise of open | 31 | 0.032 | 0.027 | 11.4 |
| fold to three-bet | 20 | 0.186 | 0.199 | 3.0 |
| river bluff share | 25 | 0.017 | 0.016 | 4.8 |
| big-bet air | 14 | 0.048 | 0.031 | 5.7 |
| small-bet air | 25 | 0.018 | 0.022 | 12.0 |
| postflop fold | 30 | 0.021 | 0.025 | 12.0 |
| postflop raise | 29 | 0.042 | 0.036 | 11.8 |
| first bet after the flop (audit only) | 30 | 0.020 | 0.013 | 15.1 |

The correlations are small, a third of the note's guess, but fold-to-bet runs 30 trials a match,
so its design effect 1 + (k - 1) rho is still about 2: half the bets are worth counting. Dronev4's
105 bets carry about 55 independent ones (d = 1.92), Blueprint's 8,536 about 4,200.

The profile rows do not keep a match count, so k = trials / matches needs one. A row seeded by the
scout from today on keeps `matches` in its `scout_base` (a one-line change to
`chipzen_scout.py`), and live hands on top are converted at 39 hands a match. Every row seeded
before today uses hands / 39 throughout; 39 is the measured median over bots of the mean hands per
match (pooled 39.3). This is the weak part of the correction: matches end on a bust, so hands per
match runs from about 15 (PoetAndCoder) to 50 (wsp). A short-match bot's clustering is therefore
overstated, which only widens its bounds, and a long-match bot's is understated.

**The fitted priors, on today's clean file.**

| rate | prior mean | strength |
|---|---|---|
| fold to bet | 0.394 | 10.9 |
| call share | 0.757 | 6.1 |
| fold to open | 0.383 | 4.0 |
| re-raise of open | 0.154 | 7.5 |
| fold to three-bet | 0.404 | 2.5 |
| river bluff share | 0.190 | 5.1 |
| big-bet air | 0.129 | 4.0 |
| small-bet air | 0.232 | 3.6 |
| postflop fold | 0.373 | 6.9 |
| postflop raise | 0.139 | 5.6 |
| first bet after the flop (audit only) | 0.389 | 7.7 |

Every prior is weak, between 2.5 and 11 pseudo-trials, because the field really is that varied
(fold to bet runs from 0.11 to 0.77). This means the prior matters for a bot with a few dozen
trials and is invisible for one with thousands, which is the behaviour the note asked for.

**The size-aware bluff rule.** With posteriors on, "bluff withheld" still needs `never_folds`, and
then also needs the bluff to be one the opponent does not fold to often enough:
`fold_floor_upper(name) < b / (P + b)`, where b is the chips this raise puts in (the call plus the
fraction of the pot after the call, as `to_chipzen` sizes it, capped by the chips behind) and P is
the pot already there, their bet included. Half the pot into a check needs a third, the pot a half,
twice the pot two thirds. The break-even assumes the bluff has no equity, which is the pessimistic
case. The player now logs the withheld raise (`"withheld"` in the decision record), because without
it this audit had to reload every rung that played to find out what was taken back.

## 2. Predictive check

Each bot's cached matches (since its `profile_since` date) are split by date into an earlier and a
later half. Rates are estimated on the earlier half and scored on every binary outcome in the later
half. 34 bots have at least six matches.

**Point predictions.** The raw rate is also the Wald estimator's point, so the comparison is raw
against the posterior mean. Summed over bots, per later trial:

| rate | bots | later trials | raw log loss | posterior | posterior without the correction | raw Brier | posterior Brier |
|---|---|---|---|---|---|---|---|
| fold to bet | 34 | 34,750 | 0.6339 | 0.6336 | 0.6337 | 0.2220 | 0.2218 |
| call share | 34 | 20,832 | 0.3990 | 0.3986 | 0.3985 | 0.1217 | 0.1217 |
| fold to open | 34 | 11,429 | 0.5616 | 0.5601 | 0.5604 | 0.1893 | 0.1888 |
| re-raise of open | 34 | 11,429 | 0.3049 | 0.2999 | 0.3000 | 0.0860 | 0.0858 |
| fold to three-bet | 30 | 1,595 | 0.7444 | **0.6542** | 0.6565 | 0.2289 | 0.2259 |
| river bluff share | 34 | 5,229 | 0.4654 | 0.4642 | 0.4641 | 0.1545 | 0.1547 |
| big-bet air | 27 | 4,066 | 0.1812 | 0.1826 | 0.1824 | 0.0582 | 0.0580 |
| small-bet air | 33 | 14,171 | 0.3793 | 0.3780 | 0.3779 | 0.1245 | 0.1245 |
| postflop fold | 34 | 12,712 | 0.6205 | 0.6203 | 0.6203 | 0.2141 | 0.2142 |
| postflop raise | 34 | 12,712 | 0.2491 | 0.2491 | 0.2491 | 0.0680 | 0.0679 |

Weighted by trials the two are nearly level, because the big bots dominate the sum and with
thousands of trials the posterior is the raw rate. The gain shows when each bot counts once:

| earlier-half trials of the rate | bot-rates | raw log loss | posterior |
|---|---|---|---|
| under 50 | 105 | 0.5686 | **0.4638** |
| 50 to 300 | 143 | 0.5259 | 0.5250 |
| 300 and over | 114 | 0.4613 | 0.4611 |

So the posterior is about 18 percent better where samples are small, level where they are large,
and worse nowhere that matters. Per bot, over all its rates, the posterior predicts better for 19
bots, raw for 11, and 4 are tied. Raw's wins are all at the third decimal (the largest is lil-bot-v2,
0.5273 against 0.5304, and runner1's 0.4297 against 0.4326 is a raw 0 of N predicting the later 0 of
N exactly), while the posterior's
largest are on the small bots: Fold-ver-2 0.687 to 0.549, HRT 0.520 to 0.456, RoboPoker 0.689 to
0.619, Dronev4 0.678 to 0.651. The big four (PoetAndCoder, mr_hide, hoops, Blueprint) are tied.

The design-effect correction changes the point predictions by nothing worth reading, which is
expected: it barely moves the mean. What it moves is the width of the bounds, so it matters for the
read decisions, not for the predictions.

**Read decisions.** Each rule's verdict on the earlier half, judged two ways on the later half:
its raw rate past the threshold (with at least 30 trials), and its own posterior (prior refitted on
the later rows), which calls the read confirmed when the bound is past the threshold, refuted when
the opposite bound is on the wrong side, and open otherwise. The raw judge counts 0 of 40 as
"never", which is the zero-width mistake under test, so it flatters the old rules on the never-reads.
"sequential" is the rule set the live bot plays (`--sequential-triggers --scout-reads`).

| read | rule | fired | confirmed | refuted | open | missed (later half confirms, early silent) |
|---|---|---|---|---|---|---|
| never folds | sequential | 12 | 10 | 0 | 2 | 1 |
| never folds | posterior | 11 | 10 | 0 | 1 | 1 |
| folds blind | sequential | 2 | 2 | 0 | 0 | 1 |
| folds blind | posterior | 2 | 2 | 0 | 0 | 1 |
| never three-bets | sequential | 5 | 2 | 1 (Mimaima699-Pro) | 2 | 0 |
| never three-bets | posterior | 1 | 1 | 0 | 0 | 1 |
| folds to three-bet | sequential | 2 | 0 | 1 (melly) | 1 | 0 |
| folds to three-bet | posterior | 1 | 0 | 1 (melly) | 0 | 0 |
| never bluffs | sequential | 4 | 4 | 0 | 0 | 0 |
| never bluffs | posterior | 2 | 2 | 0 | 0 | 2 (melly, runner1) |
| never calls | both | 0 | 0 | 0 | 0 | 0 |

Totals: the sequential rules fired 25 reads, of which 18 were confirmed, 2 refuted and 5 left open;
the posterior fired 17, of which 15 were confirmed, 1 refuted and 1 open. So 88 percent of the
posterior's reads held up against 72 percent, at the cost of 5 confirmed misses against 2. All three
extra misses are "never" reads on half the data, and the cause is visible: a prior mean of 0.19 for
river bluffs puts about one pseudo-bluff into a bot's count, so `never_bluffs` needs 55
zero-bluff river bets before its bound is under 5 percent, where the raw rule needed 40. On the full
file both melly and runner1 fire it again. This is the trade the posterior makes on purpose: fewer
reads, each one more often right. Whether it is the right trade depends on whether a wrong read
costs more than a missed one, and the Shadow history (19,896 chips over 12 wrong firings of
never-calls) says it usually does. These are 34 bots, so the read counts are small and the
percentages should be read as direction, not size.

`never_calls` never fires on either half under any rule, so the Dronev4 case cannot appear in this
check; it was already removed by the 0.35 floor. Under posteriors Dronev4's call-share bound is
0.61, so it would not fire even at the old 0.5 floor.

## 3. Read changes per opponent, on today's clean file

Old rules here means the live flags (`--sequential-triggers --scout-reads`). Posteriors only take
reads away; none is added.

| opponent | lost under posteriors | why |
|---|---|---|
| r0ckGarden | never three-bets | 136 of 3,731 is 3.6 percent, under 4 as a point, not on the bound |
| qwentom-leap | never three-bets | 8 of 331 |
| runner1 | never three-bets | 4 of 163 |
| melly | folds to three-bet | 143 of 182 (79 percent); the lower bound is under 75 |
| mellyy | folds to three-bet | 69 of 83; the prior's pull matters here (strength 2.5, mean 0.40) |
| riverline_v2 | folds to three-bet | 24 of 27 |
| Maxwell | never folds | 0.366 over 976 bets; the bound is 0.401 against 0.40 |
| Fold-ver-2 | never bluffs | 0 of 40 |

Separately, the bound changes which reads come from the prior and which from the clustering
correction. With the correction off, only Maxwell keeps its read (and Sleight-of-Hand_v3 gains
never-folds); with a uniform prior instead of the fitted one, only mellyy keeps its read. So most of
the changes come from using a real interval at all, not from either refinement.

**No read changes on the opponents left this season.** PoetAndCoder keeps never-folds and
big-bets-are-value, Blueprint and Dronev4 have no reads under either rule. hoops and mr_hide keep
never-folds, and that is where the size rule acts (section 4).

The floors barely move for large samples (river bluff floor, re-raise floor, within 0.01 to 0.03).
`postflop_fold_floor` now returns None for r0ckGarden, Fold-ver-3 and PoetAndCoder, because their
raise share's upper bound is over 15 percent. That floor is read only under `--aggro-reads`, which
the live bot does not run.

## 4. Decision audit on our logs

576 match logs, 2,481 decisions adjusted by one of these reads. The logs were made under whatever
profile each match had at the time, so the first comparison is against today's file under the old
rules, which is the fair baseline for "what would change if we switched".

| adjustment | logged | still made today, old rules | under posteriors |
|---|---|---|---|
| bluff withheld | 1,203 | 1,177 | about 1,067 (size rule, below) |
| shove call declined | 662 | 0 | 0 |
| opened into a folding blind | 583 | 95 | 95 |
| river bet believed | 20 | 20 | 20 |
| three-bet into a folder | 6 | 6 | 0 (melly 4, mellyy 2) |
| small bet called / big bet believed | 5 | 5 | 5 |
| their re-raise is value | 2 | 2 | 1 (r0ckGarden's goes) |

The 662 shove-call declines (650 on Blueprint, 12 on Shadow) and 488 of the folding-blind opens (all
Blueprint) do not fire today under either rule. They belong to the old Blueprint and the inflated
rows, and they are already gone.

**Bluff withheld, by size.** The logs did not record which raise was taken back, so each withholding
was looked up in the rung that played it (as `chipzen_replay.lookup` does), and the solver's raise
distribution there gives the size. 277 of mr_hide's are from logs before the version frame existed
and cannot be sized; at mr_hide's bound that makes no difference.

| opponent | fold upper bound | logged | sizes (half / pot / 2x / all-in) | released by the size rule |
|---|---|---|---|---|
| mr_hide | 0.280 | 738 | 255 / 139 / 57 / 9 (461 sized) | 2 |
| hoops | 0.376 | 367 | 222 / 108 / 33 / 4 | **100**, all half-pot bets into a check |
| Fold-ver-3 | 0.366 | 25 | 13 / 7 / 5 / 1 | 8 |
| PoetAndCoder | 0.242 | 23 | 15 / 6 / 2 / 0 | 0 |
| runner1 | 0.292 | 21 | 11 / 5 / 5 / 0 | 0 |
| lil-bot-v2 | 0.213 | 3 | 3 / 0 / 0 / 0 | 0 |
| v003 | 0.459 | 26 | not sized | 26, but the read is off today under both rules |

So the size rule does what problem 4 asked for and no more. Against hoops it gives back the 100
half-pot bluffs into a check out of 367 withholdings, while every preflop withholding stays, because
an open puts 1.5 blinds into 1.5 and needs half. Against mr_hide and PoetAndCoder it withholds what
the old rule did. In all, about 117 logged decisions out of 2,481 would have gone the other way.
What those hands would then have won is not knowable from the logs, because the opponent's answer to
a bet it never faced is not in them; that is what a copy duel is for.

**The caveat that matters most: fold rate depends on bet size.** One fold rate for every size is the
weak part of the rule. Measured on the scout cache, folds to a first bet on a street after the flop,
by size against the pot (these are other bots' bets into the scouted bot):

| bot | under 0.4 pot | 0.4 to 0.6 (half) | 0.6 to 0.85 | 0.85 to 1.2 (pot) | over 1.2 |
|---|---|---|---|---|---|
| hoops | 0.17 | 0.44 | 0.51 | 0.57 | 0.67 |
| mr_hide | 0.11 | 0.17 | 0.18 | 0.38 | 0.49 |
| PoetAndCoder | 0.15 | 0.30 | 0.36 | 0.34 (53) | 0.56 (95) |
| Fold-ver-3 | 0.60 | 0.55 | 0.68 | 0.74 | 0.88 |
| Blueprint | 0.38 (58) | 0.45 | 0.50 | 0.48 | 0.70 (67) |

Every bot folds more to bigger bets, and often by enough to change the answer. hoops folds 57
percent to pot-sized bets, which a pot bluff needs only 50 of, so the rule still withholds pot
bluffs against hoops that would have shown a profit. Fold-ver-3 folds 36.6 percent overall, because
it calls opens, and 55 to 88 percent after the flop, so the station read on it is wrong postflop. I
tried the obvious refinement, the fold rate at the decision's own spot (our first bet on a street
after the flop, from the `{street}:Ur` and `{street}:TcUr` nodes). It fixed Fold-ver-3 (13 released
instead of 8), but pooled over sizes it overstates folds to small bets, and it released about 5
half-pot bluffs against PoetAndCoder although that bot folds 30 percent to them. So I left the rule
on the overall rate, as specified, and kept the first-bet rate in `RATES` and in the audit, where it
is shown beside the rule. The fix is fold counts by our bet size, kept in `observe` and in the scout,
which no row has yet.

## 5. Tests

`tests/test_posterior_reads.py`, 24 tests, plus one in `tests/test_chipzen_player.py`:

- The prior: the mean is the field's and a wide field gives a weak prior; a field that looks alike
  hits the ceiling; a wildly mixed one is held at the floor; too few bots or too few trials gives a
  uniform prior.
- The bounds: with no row the posterior is the prior and no read fires; 0 of 40 has a bound with
  width where Wald has none; one more fold raises both bounds and one more call lowers both; more
  data at the same rate narrows the interval; the same bets clustered in fewer matches give a wider
  bound; a scouted match count is used when the row carries one.
- The reads on synthetic rows: Dronev4 (31 calls in 67 answers, 105 bets) does not fire never-calls,
  and its bound is not even under a half; Blueprint as of 14 September still does; a 23 percent folder
  over 5,000 bets fires never-folds while Maxwell's 0.366 does not; hoops fires never-folds with its
  bound between a third and a half; folds-blind (mellyy fires, a small 73 percent folder does not),
  never-three-bets (wsp fires, r0ckGarden does not), folds-to-three-bet (melly does not), never-bluffs
  (runner1 and melly fire, 0 of 40 does not), the sizing tell, the floors as posterior bounds with
  their minimums, and posteriors off matching the old Wald rule.
- The size rule: break-even of a third, a half and two thirds for half, pot and twice the pot into a
  check, a half for a half-pot raise facing a bet, capped by the chips behind; against a 36 percent
  folder a pot bluff and a shove are withheld and a half-pot bluff is not; against a 23 percent folder
  every size is withheld; through `decide` with the shipped solver, a station's bluffs are still
  withheld under posteriors and the record carries the withheld raise.

Run: `tests/test_posterior_reads.py tests/test_chipzen_opponents.py tests/test_chipzen_player.py
tests/test_opponent_brief.py tests/test_price_guard.py tests/test_aggro_reads.py`, 97 passed in 4.1
seconds. The full suite was not run.

## 6. Recommendation

Leave the live set alone for tonight's final, as the opponent-modelling note says. Nothing about
the final depends on it anyway: on PoetAndCoder, Blueprint and Dronev4 no read changes and no logged
decision would have gone differently.

After the final, the posterior is worth turning on, but through the gates, not on this note alone.
The predictive check says it is never worse and clearly better on small samples, and its reads hold
up more often (15 of 17 confirmed against 18 of 25). The decision change it makes in practice is
narrow and specific, mainly the hoops half-pot bluffs and the scouted three-bet reads on melly and
mellyy, so a copy A/B on the hoops copy (10,000 to 20,000 matches, `--posterior-reads` in one arm's
flags) is the right first measurement, then the cross-tree gate, then bursts read decomposed.

Before that, two things would make it better than the rule it replaces rather than only safer:

1. **Fold counts by our bet size**, in `observe` and in the scout's rows, so the bluff rule compares
   each size with the folds to that size. Section 4 shows this is where the remaining error is, in
   both directions.
2. **Re-seed the scouted rows** so they carry `matches`, which replaces the hands / 39 conversion
   with a real count. That needs a scout run, which is a platform call, so it is yours to start.

The note's option 2 (a false-discovery budget across the file) is cheap on top of this, because each
read now has a posterior tail probability to rank by.

## Correction, 5 Oct afternoon: folds to three-bet

The tables above were written with the posterior held against 0.75, and they show melly and mellyy losing
`folds_to_three_bet`. That was a mistake in the rule, not a finding. The read was written for mellyy (25 of 29
when first scouted). The 0.75 line already carries a margin over the 0.67 a small three-bet needs to break even,
so holding a lower bound to 0.75 counted the margin twice. Under posteriors the bound is now held to
`THREE_BET_BREAK_EVEN = 0.67`. melly (143 of 182, bound 0.725), mellyy (69 of 83, bound 0.747) and riverline_v2
keep the read, and the 6 three-bets into melly and mellyy in the decision audit no longer change.
`tests/test_posterior_reads.py` now pins melly firing, and a 20-of-28 bot near the break-even not firing.

The same check belongs on every read that has a margin built into its threshold: a bound plus a margined line
is double caution. `never_folds` (an upper bound against 0.40, the equilibrium fold share) and `never_calls`
(against 0.35) compare a bound with a reference line, not with a margined one, so they are left as they are.

## Correction, 5 Oct afternoon: every read audited for the melly kind of miss

After the three-bet correction, every read on every bot was compared across three states: the season's inflated
profiles under the old rules, the clean profiles under main's rules, and the clean profiles under posteriors. Of
18 reads switched off along the way, 12 were right to go, because the bot really plays differently (Dronev4,
LazerTank and drone call 46 to 51 percent; Shadow and lil-bot-v2 fold their blinds 60 and 52 percent; lil-bot-v2
and mellyy re-raise 19.8 and 8.7 percent; and others close to their lines). Six were the melly mistake, with the
bot's behaviour unchanged, and are fixed under posteriors:

| Bot | Read | The numbers | Cause | Fix |
|---|---|---|---|---|
| HRT | folds blind | 55 of 59 (93%) | fixed minimum of 100, set for inflated rows | `POSTERIOR_BLIND_MIN = 15` |
| HRT | folds to three-bet | 14 of 14 | fixed minimum of 25 | `POSTERIOR_THREE_BET_MIN = 10` |
| wsp | river never bluffs | 4 of 500 (0.8%) | demands exactly zero | zero, or a bound of at most `HONEST_RIVER_BOUND = 0.03` |
| Fold-ver-2 | never bluffs | 0 of 40 | bound held to the margined 0.05 | bound held to `NEVER_BLUFF_BOUND = 0.10` (a call needs about a quarter to a third bluffs) |
| r0ckGarden, qwentom-leap, runner1 | never three-bets | 3.6% of 3,731, 2.4% of 331, 2.5% of 163 | bound held to the point line 0.04 | bound held to `RARE_RAISE_BOUND = 0.06` |

The river rule is never stricter than the exact zero. A zero's bound moves with the other bots' bluff rates:
runner1's 0 of 106 sat at 2.8 percent on the file and 3.2 in a test field of heavier bluffers. So the zero stands
on its own, and the bound only adds the near-zeros. Under the fixed posteriors, only five reads differ from main's
rules on today's file: HRT's two and wsp's come back; r0ckGarden gains "never bluffs" (7.7 percent of 519, far
inside the quarter a call needs); and Maxwell loses "never folds" (37 percent, bound 0.401 against 0.40). The
tests that had pinned the misses (melly, r0ckGarden and Fold-ver-2 not firing) now pin the corrected behaviour,
and a new one pins the river rule.
