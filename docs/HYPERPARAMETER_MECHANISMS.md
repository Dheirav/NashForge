# Mechanistic Analysis of Hyperparameter Effects in Evolutionary Poker AI

**Document Type**: Research-Grade Mechanistic Interpretability  
**Version**: 1.0  
**Date**: February 28, 2026  
**Data Coverage**: Batch 1–3, ~630,000 games, 58+ unique configurations  
**Focus**: *Why* each hyperparameter produces the observed outcomes — not just what the outcomes are

---

## Preface

This document addresses a specific gap in the existing batch reports: they record *what* happens when hyperparameters are set to certain values, but do not systematically explain *why*. Understanding the mechanism behind each effect is critical for:

1. Predicting the outcome of untested configurations without running them
2. Avoiding configurations that appear reasonable but fail for non-obvious reasons
3. Designing future experiments that test mechanistic hypotheses rather than blind sweeps

Every finding in this document is grounded in either direct empirical evidence from the tournament data or in the mechanics of how the training system works (as implemented in `training/fitness.py`, `training/evolution.py`, and `training/config.py`).

---

## System Architecture Summary

Before examining individual hyperparameters, it is necessary to understand precisely what the training loop is doing, because many hyperparameter effects are only interpretable in the context of the loop's structure.

### The Training Loop

Each generation proceeds as follows:

```
For each genome in population (size p):
    For each of m matchups:
        Sample (num_players - 1) opponents from:
            - 70% from current population
            - 20% from Hall of Fame
            - 10% random (noise agents)
        Play h hands against those opponents at a 6-player table
        Record chip delta
    Fitness = BB/100 = (total_chip_delta / big_blind) × (100 / total_hands)

Sort population by fitness
Preserve top elite_fraction unchanged
Generate offspring via Gaussian mutation (σ applied to every weight)
Add immigrant_fraction random new agents
Replace bottom of population with offspring + immigrants
Update Hall of Fame if current best exceeds stored threshold
```

### The Fitness Signal

The core quantity being optimized is BB/100 — Big Blinds per 100 hands, measured across all matchups and all hands within this single generation's evaluation. This is the **only feedback signal** the evolutionary algorithm receives. An agent cannot observe its own win rates, cannot read the action history of prior generations, and has no memory across generations. All adaptation happens through the differential survival of higher-fitness genomes.

This means: **the quality of the fitness signal is the most important determinant of agent quality.** Any hyperparameter that degrades the accuracy, diversity, or representativeness of the fitness signal will produce worse agents. This principle underpins almost every mechanism described below.

---

## Part I: Matchups per Agent (m)

### What It Controls

`matchups_per_agent` (m) determines how many distinct opponent groups each agent faces per generation during fitness evaluation. With m=8 and num_players=6, each agent plays against 8 different sets of 5 opponents, accumulating h hands against each set.

### Why m=8 Outperforms m=6 (and m=7 in MultiTable)

**The fundamental issue with low m is fitness signal noise.**

When m is small, the fitness score of an agent is determined by its performance against few opponent groups. If those few groups happen to contain opponents with exploitable tell patterns — particular betting frequencies, tight/loose tendencies determined by their initialization or training history — the agent's fitness becomes a noisy estimate of its true quality as a generalist player.

Consider the extreme case of m=1: the agent's entire fitness score is determined by one set of 5 opponents. If those 5 opponents all happen to be passive callers, an agent that learned to always bluff would rank highly — not because it is a good agent, but because it happened to be evaluated against the one opponent type it can exploit. Conversely, a genuinely good agent might score poorly if its single matchup group contains opponents it is specifically weak against.

With m=8, the law of large numbers begins to operate. The agent must perform well across 8 different opponent groups drawn from the population. Random variance in opponent composition is averaged out. The resulting fitness score is a much more reliable estimate of the agent's actual strategic quality.

**Empirical evidence**:

| m | Mean Win Rate (B1/B2) | Mean Win Rate (B3 MultiTable) | Effect |
|---|---|---|---|
| 3 | 22.2% | — | Floor-level, random-equivalent |
| 6 | 50.8% | — | Baseline |
| 7 | — | 36.9% | Slightly below m=8 |
| 8 | **75.5% / 66.3%** | **38.3%** | Optimum |
| 9 | — | 32.2% | Worse than m=8 |
| 10 | 28.1% | — | Severe overfitting |

The m=3 result (22.2%) is particularly diagnostic: these agents are statistically indistinguishable from the worst performers in every batch. With only 3 matchups, the fitness signal is so noisy that selection cannot distinguish good strategies from lucky ones, and the population never converges to anything meaningful.

### Why m=9 and m=10 Are Worse Than m=8

This is counterintuitive — why would more matchups hurt?

The mechanism is what can be called **opponent overfitting within a generation**. When m is large, the agent's fitness during training is evaluated against a very broad sample of the population. At `num_players=6` with 70% population sampling, that means $m \times 5 \times 0.7 = m \times 3.5$ distinct population members are encountered per fitness evaluation.

At m=8: roughly 28 distinct opponents encountered  
At m=9: roughly 31.5 distinct opponents encountered  
At m=10: roughly 35 distinct opponents encountered

With m=10 (and m=9 to a lesser extent), the agent is effectively being evaluated against the *entire diversity of the population* in every generation. This sounds like it would be better, but it has a critical pathological effect: **it forces the winning strategy to be a generalist response to the entire population distribution, including agents that are very bad**.

If the population contains a mix of strong and weak agents, a strategy that is moderately good against everyone will outscore a strategy that is excellent against strong opponents but mediocre against bad ones. Over generations, this selection pressure systematically pushes the population toward "beaten-everything mediocrity" — strategies that hedge against all opponent types rather than exploiting weaknesses of strong opponents. The result is an agent that cannot beat anyone well because it was trained to not lose to everyone.

m=8 sits at the empirical sweet spot: enough opponents to reduce fitness noise, few enough that selection pressure still rewards quality over breadth.

### Why m=7 Outperforms m=8 in HeadsUp (Batch 3)

In the HeadsUp correlation table from Batch 3:

| m | HeadsUp Win Rate |
|---|---|
| 7 | **58.8%** |
| 8 | 45.5% |

This appears to contradict the m=8 optimality finding. The mechanism is specific to 1v1 evaluation, not a general reversal.

In HeadsUp format, the dominant strategic skills are reads on a single opponent — bet sizing relative to their tendencies, aggression frequency calibration, bluff-to-value ratios. These require learning to respond to *one specific opponent's pattern*. When the agent faces m=8 matchups during training (each against 5 population members), it is being prompted to learn multi-player dynamics (position, side pots, multi-way hand reading). The resulting agent is well-calibrated for multi-player play but has slightly diluted 1v1 precision.

With m=7, there is marginally less training signal about multi-player contexts, and the agent retains slightly more budget for specializing its decision-making to the 1v1 regime where the feature input includes fewer active-player interactions. This is a small effect (58.8% vs 45.5% is large in absolute terms, but this is because of confounders — many of the m=8 agents in B3 used h=750, which independently hurts HeadsUp; see Part II).

---

## Part II: Hands per Matchup (h)

### What It Controls

`hands_per_matchup` (h) determines how many poker hands are played against each opponent group in a single matchup. It controls the depth of evaluation against any single opponent set.

### Why h=375–500 Outperforms h=750 in Batch 3 HeadsUp

This is the most misunderstood result in the batch reports. The explanation has nothing to do with agent "maturity" across batches (since every agent trains from scratch) and everything to do with **within-matchup opponent overfitting**.

The mechanism: during a single fitness evaluation, an agent plays h hands against the same set of 5 opponents. Over 750 hands, the agent accumulates substantial statistical signal about that specific group's tendencies. If those 5 opponents have consistent biases (e.g., they tend to c-bet 70% of the time, they fold to re-raises frequently), the agent's strategy weights are reinforced in ways that improve its score against *those specific opponents* but may not generalize.

This is not gradual — it is a direct consequence of how the evolutionary fitness computation works. The fitness score (BB/100) is computed purely within the single matchup evaluation. A strategy that has learned to exploit this specific group scores higher than a strategy that plays theoretically sound poker against the group. When selection occurs, the opponent-specialized strategy is more likely to propagate its weights.

With h=375–500, no single matchup lasts long enough for the agent to confidently exploit opponent-specific tendencies. It is forced to play strategy that works out of the box against any opponent group, because it does not have enough hands to learn exploitation patterns within the evaluation window.

**Why this matters more for HeadsUp than MultiTable:**

In 1v1 poker, opponent exploitation is the dominant win condition. Reading a single opponent's patterns and adjusting is the core skill. At h=750, the agent learns opponent *A*'s tendencies over the 750-hand matchup, which trains it to be a good exploiter of *A* specifically. But when it faces *B* (an unknown opponent in the tournament), it applies A's patterns to B, which may be wrong. With h=375, it never had the chance to memorize A's patterns, so it plays more generalized strategy that happens to work against B too.

In MultiTable, there are 5 opponents per table and the dynamics are less about exploiting one person — pot odds, position, stack geometry dominate. So the opponent-memorization effect from h=750 is less harmful (the memorized patterns about one player don't carry over badly to the more complex multi-player evaluation).

**Directional summary from data**:

| h | HeadsUp WR (B3) | MultiTable WR (B3) |
|---|---|---|
| 375 | **55.9%** | 35.5% |
| 500 | 55.4% | **36.4%** |
| 750 | 41.9% | 35.8% |

h=500 is optimal for MultiTable; h=375 and h=500 are both good for HeadsUp; h=750 specifically degrades HeadsUp. This is fully consistent with the opponent-memorization mechanism.

### Why h=750 Was *Best* in Batch 1/2

Batch 1/2 used m=6 and populations from which agents were still learning basic poker strategy. At that stage, agents needed longer matchups to develop any consistent strategy signal: 375 hands was not enough to differentiate a fundamentally better agent from a lucky one when skill levels were low. h=750 at m=6 in B1/B2 was not achieving better opponent exploitation — it was achieving better fitness *accuracy* (less variance in BB/100 measurements of weak agents).

The reversal from B1/B2 to B3 is therefore not about batch-level agent maturity. It is about the **interaction between m and h**. B3 uses m=7–9 (compared to m=6 in B1/B2). With higher m, fitness accuracy is already higher (more matchups = less variance per agent). The additional accuracy from h=750 is no longer needed, and the opponent-memorization cost of h=750 becomes the dominant effect. The apparent "reversal" is actually a consistent underlying mechanism that simply manifests differently depending on m.

### The Total Evaluation Budget Law

A useful frame for thinking about m and h together is total evaluations per agent per generation:

$$E_{total} = m \times h$$

The data suggests two things:

1. **For a given $E_{total}$, more matchups (higher m) beats more hands per matchup (higher h)**  
   e.g., m=8, h=375 ($E=3000$) beats m=6, h=500 ($E=3000$) by ~25 percentage points

2. **$E_{total}$ exhibits diminishing returns beyond ~4,000**  
   m=8, h=500 ($E=4000$, **81.2%**) is marginally better than m=8, h=375 ($E=3000$, **78.7%**)  
   m=6, h=750 ($E=4500$) is worse than both

The reason variety (m) beats depth (h) at equivalent budget is precisely the opponent-memorization mechanism: spending budget on more diverse opponents generates more generalizable training signal than spending it on deeper evaluation of fewer opponents.

---

## Part III: Mutation Sigma (σ)

### What It Controls

`mutation_sigma` (σ) is the standard deviation of the Gaussian noise added to every weight in an agent's network when creating offspring:

$$\theta_{child} = \theta_{parent} + \mathcal{N}(0, \sigma^2)$$

For a network with architecture 17→64→32→6 (the standard config), there are $(17 \times 64 + 64) + (64 \times 32 + 32) + (32 \times 6 + 6) = 1,152 + 2,080 + 198 = 3,430$ parameters. Every single one receives an independent Gaussian perturbation of standard deviation σ each generation.

### Why σ=0.15 is a Catastrophic Failure

**Evidence**: σ=0.15 achieves 34.2% mean win rate across all tested configs — indistinguishable from random performance in many cases.

The mechanism is a **phase transition in evolutionary dynamics**, not a gradual performance cliff.

Consider what σ=0.15 means for a network with 3,430 parameters. The expected L2 distance between parent and child is:

$$\mathbb{E}[\|\theta_{child} - \theta_{parent}\|_2] = \sigma \sqrt{d} = 0.15 \times \sqrt{3430} \approx 0.15 \times 58.6 \approx 8.8$$

For comparison, the weights in a trained network typically have magnitudes in the range [-1, 1] per weight. The parent-child L2 distance of ~8.8 is enormous relative to the network's typical weight magnitudes. This means:

- **Hidden layer activations change fundamentally**: A single layer's output is $W\mathbf{x} + \mathbf{b}$. With weights perturbed by ~0.15 each, the layer's output distribution shifts dramatically at every forward pass.
- **Learned strategy representations are destroyed**: Whatever betting patterns, hand-strength estimates, or positional adjustments were encoded in the weights after one generation are almost entirely overwritten in the next.
- **Selection signal cannot accumulate**: The best genome at generation $t$ produces children that look essentially nothing like it at generation $t+1$. Even if a good strategy was discovered, it has almost zero probability of being preserved in slightly-modified form — the mutation step is so large that offspring explore the weight space nearly independently.

This is the population-level equivalent of an annealing temperature so high that the system is performing random walks rather than hill-climbing. Evolutionary algorithms with σ=0.15 are approximately equivalent to randomly re-initializing the population each generation. The ~34% win rate observed is exactly what you would expect from a population of well-initialized-but-untrained random networks facing a competition.

### Why σ=0.08–0.10 is Optimal

At σ=0.08:

$$\mathbb{E}[\|\theta_{child} - \theta_{parent}\|_2] = 0.08 \times 58.6 \approx 4.7$$

This is still a significant perturbation at the individual weight level, but it is small enough that:

1. **Macro structure is preserved**: The general strategy encoded in the network (e.g., "raise when pot odds are favorable") survives mutation with high probability
2. **Fine-tuning occurs**: Small changes in individual weights can shift the precise bet-sizing thresholds, fold frequency adjustments, and aggression calibration
3. **Hill-climbing is possible**: Better offspring are genuinely similar to their parents with incremental improvements, allowing the population to converge from its current position

The σ range 0.08–0.10 achieves what can be thought of as *targeted local exploration*: each offspring is a variant of the parent that shares its core strategic logic while exploring nearby strategy variants.

### Why σ=0.07 Shows the Strongest Performance in Batch 3

σ=0.07 produces $\mathbb{E}[\|\Delta\theta\|_2] \approx 4.1$, slightly less than σ=0.08's 4.7. The key is the **interaction with population size**. In Batch 3, the σ=0.07 configs use p=40. With 40 agents in the population, the existing genetic diversity (the spread of weights across all 40 agents) is already substantial. The population-level exploration does not need large per-agent mutations because the population itself covers the strategy space broadly. Each agent only needs small perturbations to fine-tune its niche.

This is formalized in the empirical formula:

$$\sigma_{optimal} \approx \frac{0.5}{\sqrt{p}}$$

At p=40: $\sigma \approx 0.5 / \sqrt{40} \approx 0.079$, which is exactly the σ=0.07–0.08 empirical optimum.  
At p=12: $\sigma \approx 0.5 / \sqrt{12} \approx 0.144$, but empirical optimum is 0.08–0.10.

The formula over-predicts optimal σ for small populations because small populations rely on HoF opponents to compensate for low diversity — the HoF introduces effective "virtual diversity" that reduces the required mutation magnitude. Without HoF, σ ≈ 0.14 would be needed for p=12; with HoF maintaining diverse opponent pressure, σ=0.08 is sufficient.

### The σ Threshold Effect is a Phase Transition

The discrete jump between σ=0.12 (acceptable, ~49%) and σ=0.15 (catastrophic, ~34%) is not a gradual degradation. The gap is 14-15 percentage points, which is disproportionately large for a 25% increase in σ. This non-linearity indicates a **qualitative change in the evolutionary dynamics** at some σ threshold between 0.12 and 0.15.

The theoretical boundary is the point at which the per-generation fitness signal can no longer overcome the mutation noise — where the best children of the best parents are, on average, no better than random children. This is analogous to the error threshold in quasispecies theory. Once σ crosses this threshold, the population can no longer maintain any genetic information across generations, and performance collapses to the baseline of randomly initialized networks facing each other.

---

## Part IV: Population Size (p)

### What It Controls

`population_size` (p) determines how many distinct neural network agents exist simultaneously in the gene pool. At each generation, fitness is evaluated for all p agents, the top `elite_fraction × p` survive unchanged, and the rest are replaced by mutated offspring.

### Why Population Size Has Low Impact When HoF is Used

**Batch 3 combined win rates by population**:

| p | Win Rate |
|---|---|
| 12 | 38.7% |
| 20 | 37.2% |
| 40 | 36.7% |

A 2-point spread across a threefold range in population size (12 vs 40) is remarkably small. This is a consequence of the Hall of Fame mechanism.

The conventional reason larger populations are better in evolutionary algorithms is **diversity**: with more agents, the population collectively explores more of the strategy space, reducing the probability of premature convergence to a local optimum. A small population (p=12) would normally converge faster and could become trapped in a suboptimal state.

The HoF opponents disrupt this logic. At every fitness evaluation, 20% of opponents are drawn from the HoF pool (which contains strategies from diverse historical training runs with different hyperparameters). This means:

- Even a population of 12 agents is always being evaluated against strategies it has never seen within its own population
- The HoF opponents prevent the "mutual exploit" failure mode (where all p=12 agents learn to beat each other but nothing else)
- The selection pressure is effectively against the HoF's strategy diversity, not only the current population's diversity

As a result, population size primarily affects training *speed* (larger populations explore more in parallel per generation) rather than final quality once HoF is active.

### Why p=12 Was Worst in Batch 1 (Without HoF)

In Batch 1, no HoF was used. p=12 without HoF: **33.8%**. p=40 without HoF: **61.6%**.

Without HoF, p=12 agents are evaluated only against each other plus 10% random agents. With 12 agents, the opponent pool is so small that:

1. After a few generations, all agents have converged to strategies that specifically counter the other 11 agents
2. The population is in a "closed loop" — strategies that beat these 11 agents are selected, without any pressure to generalize
3. When evaluated in tournament against agents from other populations (with different training histories), the p=12 agents fail because their strategies are exploit patterns against a specific 11-agent set, not general poker skill

p=40 without HoF has enough diversity that closed-loop convergence is slower and the winning strategies happen to be somewhat more general. But even p=40 without HoF produces mediocre results (~61%) compared to p=12 with HoF (~82%). This is the clearest evidence for the HoF mechanism.

### Why Large Populations Can Be *Worse* at High Generations (g200)

The catastrophic case from Batch 3: `p40_m8_h750_s0.08_g200` = **18.1%** vs `p40_m8_h750_s0.08_g50` = **48.1%** (a 30-point collapse).

The mechanism: at p=40 with HoF training over 200 generations, the population eventually converges strongly to a strategy that maximally exploits the HoF opponents. The HoF pool contains a fixed set of 3–4 champion agents from previous training runs. Over 200 generations of selection pressure, the population learns to beat those specific 4 agents extremely well. But those 4 HoF agents represent a small slice of possible opponent strategies. The result is a highly overfitted population that beats the training distribution but fails against anything new.

At p=12, this effect is weaker because the smaller population maintains less total optimization power — it can't as thoroughly exploit the HoF's specific patterns. At g=50, this effect hasn't fully developed — 50 generations is enough to learn good poker but not enough to overfit to 4 specific agents.

The dangerous intersection is: **large population × many generations × fixed HoF = HoF overfitting**. This combination has enough optimization capacity to find and memorize patterns specific to the 4 HoF agents, and enough depth to fully exploit them, before the training terminates.

---

## Part V: Generation Count (g)

### What It Controls

`num_generations` (g) is how many complete cycles of evaluate → select → mutate → replace occur. It is the total training depth.

### Why g200 Is Generally Better Than g50 (Batches 1/2)

In standard settings (p=12, m=8, h=500, σ=0.08), g200 reliably outperforms g50. The mechanism is straightforward: 50 generations are not enough for the Gaussian mutation + selection loop to fully converge on the strategy space. The population is still in the high-exploration phase — diversity is high, convergence is incomplete, and many agents are still discovering fundamental strategy improvements.

200 generations allows full convergence: the population's mean fitness plateaus, the distribution of strategies tightens around an optimum, and the best agents achieve stable coordination of all their decision components (preflop aggression, position awareness, pot geometry calibration).

The key signal is `max_fitness` approaching `mean_fitness` from the TensorBoard training logs — when these converge, the population has fully exploited the training signal. g=50 typically terminates before this convergence occurs.

### Why g200 Can Catastrophically Hurt (Batch 3)

As analyzed in Part IV: the failure mode is HoF overfitting at large populations with long matchups. The mechanism is:

- g=50: 50 rounds of selection → population has learned to beat the HoF generally but has 150 generations of remaining potential exploitation capacity unused
- g=200: 200 rounds of selection with p=40 and h=750 → the high total evaluation volume ($200 \times 40 \times 8 \times 750 = 48,000,000$ hand-equivalents) is more than sufficient to learn every pattern the 4 fixed HoF agents exhibit

The collapse is sharper when h=750 is also involved because longer matchups provide more signal per matchup for learning opponent-specific patterns. h=750 + g=200 + p=40 is a particularly high-capacity optimization regime targeting a fixed HoF, and the fixed HoF becomes the bottleneck.

### The g=100 Hypothesis

No batch has tested g=100 directly. Based on the g=50 vs g=200 data, the following prediction follows from the convergence and overfitting mechanisms:

- g=100 should match g=200 for most configurations (full convergence typically occurs between generations 80–150 for p=12, σ=0.08)
- g=100 should be significantly safer than g=200 for large-population + high-h configs (HoF overfitting requires the additional 100 generations to manifest fully)

This makes g=100 the predicted sweet spot for the next batch: enough depth to converge, insufficient depth to fully memorize the HoF.

---

## Part VI: Hall of Fame (HoF) Size and Composition

### What It Controls

The Hall of Fame stores a pool of historical elite agents that are mixed into the opponent pool during fitness evaluation (at 20% probability per opponent slot). Its composition defines the "curriculum" — the set of challenges the evolving population must learn to handle.

### Why HoF Prevents Population Collapse in Small Populations

Without HoF, p=12 achieves ~34% average win rate. With HoF (3 agents), p=12 achieves ~80–82%. This is the largest single performance lever in the system.

The mechanism is **evaluation distribution shift**. In pure self-play with p=12:

1. Generation 1: 12 random agents play each other. All have approximately equal fitness. Selection noise is high.
2. Generations 2–20: The best strategy for beating the other 11 specific agents is selected. Call it strategy $S_1$.
3. Generation 20–50: The population converges on variants of $S_1$. Selection pressure is now maximally specific to this population's distribution.
4. At tournament: The agent faces opponents with different training histories. $S_1$ is a specialized exploit against the training distribution, not general poker strategy.

With HoF available:

1. The opponent pool always includes agents from completely different training runs (e.g., `p40_m8_h375_s0.1_champion` trained with different sigma, population size, and strategy history than the current p=12 run)
2. Selection pressure is against a distribution that includes strategies the current population has never encountered
3. The winning strategy must generalize across the current population AND the diverse HoF agents — which forces development of robust, general poker strategy rather than population-specific exploits

The 20% HoF sampling rate (hardcoded in `fitness.py`) means each agent faces approximately $m \times (n_{players}-1) \times 0.2 = 8 \times 5 \times 0.2 = 8$ HoF opponents per fitness evaluation. This is insufficient to overfit to the HoF specifically, but sufficient to maintain generalization pressure.

### Why HoF Can Also Become the Bottleneck

The fixed HoF pool (4 champions stored in `hall_of_fame/champions/`) is both the solution and the long-run risk. With g=200 and p=40, agents eventually become expert exploiters of those specific 4 champions. This is the HoF overfitting described in Part V.

The solution implied by the data is **fresh HoF replenishment**: periodically adding the best agent from the *current* batch to the HoF pool, so that the training curriculum evolves alongside the agents. Currently, batch reports recommend specific agents for "continue" status precisely because they should be the candidates for HoF replenishment before Batch 4 begins.

### Why HoF Diversity of Source Matters More Than HoF Size

The current HoF contains:
```
p12_m6_h750_s0.1_g200_champion.npy  (Low sigma, deep training, small pop)
p12_m6_h750_s0.1_g50_champion.npy   (Same config, early convergence)
p12_m8_h500_s0.08_g200_champion.npy (Champion config, balanced)
p40_m8_h375_s0.1_champion.npy       (Large pop, fast training)
```

These agents represent four different regions of the hyperparameter space. An agent training against all four must learn to handle:
- Strategies from small populations (potentially exploitative)
- Strategies from large populations (potentially more conservative)
- Strategies shaped by different mutation regimes (different betting frequencies)
- Strategies from different hand-depth training (different opponent-read calibrations)

This diversity is what makes HoF work. If the HoF contained 4 agents all trained with identical hyperparameters, the "HoF advantage" would nearly disappear — the fixated 4 agents would all have similar strategic fingerprints, and the training population would quickly learn to exploit their shared patterns.

---

## Part VII: Format-Specific Hyperparameter Divergence

### The Fundamental Discovery

Batch 3 is the first batch to reveal that optimal hyperparameters genuinely differ between HeadsUp and MultiTable formats — not slightly, but enough to produce a **30-point inversion** (an agent that is #1 in MultiTable can be #59 in HeadsUp).

This is not a training artifact. It reflects a genuine difference in **what constitutes optimal poker strategy** between the two formats, and how training hyperparameters selectively develop one type of skill over the other.

### What HeadsUp Poker Rewards

In 1v1 play (HeadsUp format):

1. **Opponent modeling**: Reading the single opponent's tendencies is the most valuable skill. Correct fold/bluff calibration against this specific person wins.
2. **Aggression frequency**: HU poker is more aggressive than multi-player. The player who can correctly calibrate when to push advantage extracts maximum value.
3. **Positional exploitation**: With only two players, the button/BB dynamic dominates. Winning positional battles determines outcomes more than multi-way pot management.

### What MultiTable Poker Rewards

In 6-handed play (MultiTable format):

1. **Pot geometry**: Decisions about whether to enter multi-way pots, when to continuation-bet into multiple callers, when to give up require understanding the equity implications of 5 other players
2. **Table dynamics**: Stack depth relative to other players, position relative to multiple opponents, range-wide thinking rather than opponent-specific reading
3. **Survival and chip accumulation over time**: Tournament and multi-table scoring rewards chip accumulation across many hands, not single-opponent dominance

### Why h=750 Produces MultiTable Specialists

When h=750 is used in training, the agent plays 750 hands against each group of 5 opponents per matchup evaluation. Over 750 hands at a 6-player table, the agent learns:
- Which of the 5 training opponents enter pots frequently (and adjusts its strategy toward them)
- The stack depth dynamics as chips redistribute over time
- Multi-way pot geometry from repeated exposure

These are **multi-player skills**. The 750-hand training matchup essentially teaches the agent to navigate a long session of 6-player poker. These skills transfer well to MultiTable tournament evaluation.

However, the same agent, when placed in a 1v1 game, brings a strategy calibrated for 5 opponents and applies it to 1. The bet sizing, fold thresholds, and aggression assumptions are all calibrated for multi-player dynamics, and they perform poorly in the structurally different 1v1 game.

h=375–500 does not allow this over-specialization. The shorter matchup trains the agent to make decisions that work quickly against any group of opponents without the benefit of 750 hands of familiarity — which forces development of strategies that are robust in unfamiliar conditions, i.e., generalizable to both formats.

### Why the Same Config Scores Completely Differently Per Format

`p12_m8_h750_s0.1_g200`: HU = 9.0%, MT = 57.7%  
`p12_m8_h500_s0.09_g200`: HU = 81.3%, MT = 42.5%

These configs differ only in h (750 vs 500) and σ (0.1 vs 0.09). Yet the HeadsUp win rates differ by 72 percentage points. The sigma difference (0.09 vs 0.1) cannot account for this — the sigma correlation table shows a 10-point difference between σ=0.09 and σ=0.10 in HeadsUp. The h difference (500 vs 750) from the table shows a 14-point difference. Together they partially explain the gap, but the key is the **interaction effect**: h=750 specifically trains multi-player intuitions that are actively harmful in 1v1, producing an agent that is not just slightly worse at HeadsUp — it is playing 1v1 with an entirely wrong model of the game (expecting multi-player dynamics that don't exist).

---

## Part VIII: The m=9 "Dead Zone" — Mechanistic Explanation

Batch 3 introduced m=9 for the first time and found it is consistently the worst matchup count across every format and every metric. The mechanism synthesizes several effects described above.

### Phase 1: m=9 Destroys the Evaluation Gradient

With m=9 in a p=12 population, opponent selection at 70% population sampling draws $9 \times 5 \times 0.7 \approx 31.5$ distinct agents from a pool of 12. This means significant re-sampling of the same agents across different matchups. Two matchups will regularly include identical or nearly-identical opponents, providing redundant fitness signal rather than diverse signal.

The theoretical diversity benefit of m=9 over m=8 is minimal (31.5 vs 28 distinct opponents); the theoretical cost — diluted selection pressure per matchup — is real. Each of the 9 matchups receives less weight in determining overall fitness, so any single matchup's outcome has marginal influence. This makes the fitness landscape flatter: agents that are slightly better in a few strategic dimensions cannot pull ahead of mediocre agents because the mediocre agents are competitive in enough of the 9 matchups to average out.

### Phase 2: m=9 Amplifies Population Collapse

With m=9, the total evaluation budget per agent per generation is $m \times h$. For typical Batch 3 configs with h=375–500:

- m=9, h=375: 3,375 total evaluations
- m=9, h=500: 4,500 total evaluations
- m=9, h=750: 6,750 total evaluations

Ironically, m=9 occupies a budget zone (3,375–6,750) that is not better than m=8 at any corresponding h value. m=8, h=500 (4,000 evaluations) consistently outperforms m=9, h=375 (3,375) and m=9, h=500 (4,500). The reason is exactly the variety-versus-depth tradeoff: m=9 buys very slightly more opponent diversity than m=8 but at the cost of reduced evaluation budget per matchup, which increases within-matchup noise for shorter h values and amplifies within-matchup overfitting for longer h values.

### Phase 3: m=9 + g200 Locks in Instability

The bottom cluster in Batch 3 is almost entirely m=9 configs:

| Agent | Combined WR |
|---|---|
| p40_m9_h375_s0.1_g200 | 19.0% |
| p20_m9_h750_s0.09_g200 | 17.9% |
| p20_m9_h500_s0.09_g50 | 22.8% |

With a flat fitness landscape (from the diluted selection pressure of m=9) and 200 generations of selection, the population has high capacity to optimize for noise rather than signal. Random fluctuations in early-generation fitness scores propagate and are amplified by selection over 200 generations, producing agents that have overfit to noise from the m=9 evaluation regime. With g=50, there aren't enough generations to fully lock in the noise-optimized strategy, which is why `p20_m9_h500_s0.09_g50` at 22.8% is marginally better than the g200 equivalent at 17.9%.

---

## Part IX: Synthesis — A Unified Framework

### The Fitness Signal Quality Framework

Almost every hyperparameter effect can be unified under one principle: **the quality of the fitness signal determines the quality of the agent**.

A high-quality fitness signal has three properties:

1. **Low noise**: The BB/100 score reliably reflects true agent quality, not luck or opponent-matchup randomness. Achieved by: higher m (more opponents), adequate h (enough hands for statistical significance), σ in optimal range (stable offspring)

2. **High diversity**: The opponents evaluated against represent a broad range of strategies, not a narrow slice. Achieved by: HoF training (external strategies), appropriate p (population exploration), σ not too low (preventing premature convergence)

3. **Appropriate specificity**: The opponents are challenging enough to discriminate good from bad strategies, but not so overfit that the signal is only meaningful for the current training distribution. Achieved by: moderate m (not so high that the signal is against the entire distribution), h in [375, 500] (not so deep that opponent patterns are memorized), fresh HoF (not stale enough to be fully exploited)

Every anti-pattern (σ=0.15, m=3, m=9+g200, h=750+p=40+g200) can be understood as a failure of one or more of these three properties:

| Anti-Pattern | Failure Mode |
|---|---|
| σ=0.15 | Low noise? No — mutation destroys signal integrity. Low diversity? No — too much perturbation means all offspring are effectively random |
| m=3 | Low noise fails — 3 matchups is statistically insufficient to measure true fitness |
| m=9 | Low noise partially fails (diluted gradient); Appropriate specificity fails (signal is for entire population distribution) |
| h=750 + long training | Appropriate specificity fails — agent memorizes specific training opponents, loses generality |
| p<20 without HoF | High diversity fails — closed-loop convergence to population-specific exploits |
| g200 + p=40 + h=750 | Appropriate specificity fails catastrophically — high-capacity optimization fully exploits fixed HoF |

### The Optimal Configuration Profile

The configuration `p12_m8_h500_s0.08_g200` (with HoF) satisfies all three signal quality properties:

- **Low noise**: m=8 provides 8 diverse matchup evaluations; h=500 gives ~500 statistically meaningful hands per matchup; σ=0.08 maintains stable offspring
- **High diversity**: HoF ensures opponents from outside the current population; p=12 with HoF allows full convergence without closed-loop failure
- **Appropriate specificity**: h=500 is not long enough for opponent memorization; m=8 is not so broad that signal is against the full distribution

It also happens to produce a format-generalist agent because h=500 avoids the over-specialization to multi-player dynamics that h=750 induces, while also providing enough depth to learn multi-player fundamentals.

---

## Part X: Predictions for Unexplored Configurations

Based on the mechanistic framework, the following predictions follow for configurations not yet tested:

### σ=0.05–0.07 with p=12–20

**Prediction**: σ=0.07 is likely optimal for p=40 (confirmed by limited Batch 3 data). For p=12–20, σ=0.07 may cause **premature convergence** without HoF, but with HoF it should match or slightly better σ=0.08. The expected effect is a cleaner fitness landscape (lower noise from offspring) with minimally reduced diversity (the HoF compensates).

**Risk**: If σ is too low (0.05), the population converges to a local optimum before exploring the strategy space adequately — offspring are too similar to parents to escape saddle points. The threshold for this failure is unknown at p=12 with HoF; the currently uncharted range σ ∈ [0.05, 0.07] is the most valuable experiment for Batch 4.

### g=100

**Prediction**: Near-identical to g=200 for p=12, σ=0.08 configs (convergence typically occurs by generation 100–150 for these settings). Substantially safer than g=200 for p=40, h=750 configs where HoF overfitting begins around generation 100–150 and fully manifests by generation 200.

The signature of convergence in the training logs is `mean_fitness` and `max_fitness` within the TensorBoard metrics converging to the same value. A g=100 run should terminate at or near this convergence point for most seen configurations.

### p=60–100

**Prediction**: Based on the population-sigma formula $\sigma_{optimal} \approx 0.5/\sqrt{p}$, optimal σ at p=60 is ~0.065 and at p=100 is ~0.050. Without appropriate σ reduction, large populations will not outperform p=40. With correct σ scaling, the increased diversity from 60–100 simultaneous agents should produce agents competitive with p=40 at the same g count, but potentially converging faster (more parallel exploration per generation).

The key risk is the same HoF overfitting mechanism: p=100 × g=200 × fixed HoF is a very high-capacity optimization regime targeting 4 fixed opponents. g=50–100 is likely the safer training depth for these population sizes.

### h=250–350 for HeadsUp Specialist

**Prediction**: Shorter matchups (h=250) for HeadsUp may further reduce opponent-memorization effects, potentially achieving slightly higher HeadsUp win rates at the cost of worse fitness signal accuracy (the BB/100 estimates have higher variance at h=250). The optimal h for HeadsUp specialists is likely in the range [300, 450] — lower than the general-purpose optimum. This is measurable by running the same config at h=250, h=375, h=500 and observing if the HeadsUp vs MultiTable performance split shifts predictably.

---

## Appendix: Quick Reference — Mechanism to Hyperparameter Mapping

| Desired Property | Mechanism | Optimal Value | Failure Modes |
|---|---|---|---|
| Reliable fitness estimation | More diverse matchups | m=7–8 | m=3 (noise), m=9–10 (dilution) |
| Generalizable strategy | Avoid opponent memorization | h=375–500 | h=750+ (exploitation of training opponents) |
| Stable offspring | Small-enough mutation | σ=0.07–0.10 | σ≥0.15 (phase transition to random walk) |
| Population exploration | Sigma scales with 1/√p | Use σ formula | Too-low σ at small p = premature convergence |
| Format generalization | Moderate matchup depth | h=500 | h=750 → multi-player specialist, h=250 → HU specialist |
| Convergence without overfitting | Sufficient generations | g=100–200 | g=200 at large p + fixed HoF = overfitting |
| External challenge | Hall of Fame, diverse sources | 3–6 diverse HoF agents | No HoF at p<20 = population collapse; stale HoF + g=200 = memorization |
| Single-format eval | — | Avoid | W/o split evaluation, format inversion is invisible |

---

*Mechanistic analysis based on implementations in `training/fitness.py`, `training/evolution.py`, `training/config.py`, and ~630,000 games of empirical tournament data from Batches 1–3.*  
*Last updated: February 28, 2026*
