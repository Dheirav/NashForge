"""
Regret update rules — vanilla CFR, CFR+, and Discounted CFR.

These are usually presented as three algorithms. They are better understood as
one algorithm with three discount schedules applied to the accumulators before
each new contribution is added:

* **Vanilla** keeps everything at full weight. Iteration 1 counts as much as
  iteration 100,000, so early exploratory regret never fades.
* **CFR+** floors cumulative regret at zero, so an action that has been bad is
  forgiven the moment it stops being bad, and weights the average strategy by
  the iteration number.
* **Discounted CFR** decays positive and negative regret at different rates and
  decays the strategy sum too, which is a smoother version of the same idea.

Why this matters here rather than being a footnote: **CFR+'s guarantees are
proven for deterministic full traversal** (Tammelin 2014; Tammelin et al. 2015).
Under Monte Carlo sampling the flooring interacts badly with estimator variance
— sampling noise that pushes a regret negative is discarded outright rather than
averaged away, and the information is gone. Discounted CFR (Brown & Sandholm
2019) was introduced partly in response. Which one actually wins under external
sampling is an empirical question, and Leduc is small enough to answer it
exactly rather than by folklore.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class UpdateRule:
    """
    A regret and strategy accumulation schedule.

    Attributes:
        name: Label used in reports.
        floor_regret: Clamp cumulative regret at zero after each update (CFR+).
        alpha: Discount exponent for positive regret; ``None`` for no decay.
        beta: Discount exponent for negative regret; ``None`` for no decay.
        gamma: Discount exponent for the strategy sum; ``None`` for no decay.
        linear_strategy: Weight each strategy contribution by the iteration
            number, as CFR+ does.
    """
    name: str
    floor_regret: bool = False
    alpha: float | None = None
    beta: float | None = None
    gamma: float | None = None
    linear_strategy: bool = False

    # ------------------------------------------------------------------

    def discount(self, node, iteration: int) -> None:
        """
        Decay the accumulators in place, before this iteration's contribution.

        ``iteration`` is 1-indexed, matching the t in the published schedules.
        """
        if self.alpha is not None or self.beta is not None:
            regret = node.regret_sum
            if self.alpha is not None:
                scale = iteration ** self.alpha
                regret[regret > 0] *= scale / (scale + 1.0)
            if self.beta is not None:
                scale = iteration ** self.beta
                regret[regret < 0] *= scale / (scale + 1.0)

        if self.gamma is not None:
            node.strategy_sum *= (iteration / (iteration + 1.0)) ** self.gamma

    def add_regret(self, node, instantaneous: np.ndarray) -> None:
        """Accumulate this iteration's counterfactual regret."""
        node.regret_sum += instantaneous
        if self.floor_regret:
            # Regret matching+: a negative cumulative regret is reset rather
            # than remembered, so an action recovers immediately once it starts
            # paying again instead of first working off its history.
            np.maximum(node.regret_sum, 0.0, out=node.regret_sum)

    def strategy_weight(self, iteration: int) -> float:
        """Weight applied to this iteration's strategy contribution."""
        return float(iteration) if self.linear_strategy else 1.0


#: Zinkevich et al. (2007). No discounting; the reference behaviour.
VANILLA = UpdateRule(name="vanilla")

#: Tammelin (2014). Guarantees are for full traversal, not for sampling.
CFR_PLUS = UpdateRule(name="cfr+", floor_regret=True, linear_strategy=True)

#: Brown & Sandholm (2019), with the parameters recommended there.
DISCOUNTED = UpdateRule(name="dcfr", alpha=1.5, beta=0.0, gamma=2.0)

#: Linear CFR — the simple special case where everything decays at rate t.
LINEAR = UpdateRule(name="linear", alpha=1.0, beta=1.0, gamma=1.0)

ALL_RULES = (VANILLA, CFR_PLUS, DISCOUNTED, LINEAR)
