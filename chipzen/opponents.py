"""
What each opponent does when we bet, counted from the arena's own records.

The arena's argument is that exploitation is where its field is beaten. This
project's solver has no opponent model at all: it plays one strategy against
everyone. This module is the smallest honest step toward one: a count, per
opponent, of how they answer our bets, kept across matches, and a single
adjustment with a measured trigger.

The adjustment: **do not bluff a bot that does not fold.** Against `mr_hide`
on 13 September (folded 5 times in 25 hands, called 31, raised 27) the bot lost
three matches and nine of eleven showdowns, several of them river bluffs and
thin bets into a hand that was never folding. When an opponent's fold-to-bet
rate over at least MIN_OBSERVED bets is below FOLD_FLOOR, a raise the solver
chose with a weak hand becomes a check or call instead. Value bets are left
alone: the strength threshold is on the hand, not on the action.

Nothing is guessed from a few hands. Below MIN_OBSERVED bets the profile is
"unknown" and the solver plays as it would against anyone.
"""
from __future__ import annotations

import copy
import glob
import json
import os
from typing import Dict, Optional, Tuple

#: Bets faced before a fold rate is believed. A hundred is a week of matches
#: against one bot, and roughly the sample at which a 25% rate is separated
#: from 40% at two standard errors.
MIN_OBSERVED = 100
#: Fold-to-bet below which bluffing is pointless. An equilibrium heads-up
#: strategy folds to a bet somewhere around 40% of the time; a bot under a
#: quarter is calling with everything.
FOLD_FLOOR = 0.25
#: Calls as a share of the opponent's non-fold answers below which it is a
#: fold-or-raise bot whose raises mean it. Measured 14 September: Blueprint
#: 0.34 (38 calls, 73 raises), the three bots that call us down 0.81 to 0.90.
CALL_FLOOR = 0.5

#: The sequential trigger (opt in, `Profiles(sequential=True)`): act as soon as
#: the 95 percent interval of the observed rate excludes the equilibrium-ish
#: baseline, from SEQ_MIN_OBSERVED bets on, rather than waiting for a fixed
#: hundred. Binomial arithmetic on 15 September: separating a 25 percent
#: folder from a 45 percent one at power 0.8 needs 45 bets, and 15 percent
#: needs 19, so the hundred was two to four times more than the evidence
#: required. The baselines are what a heads-up equilibrium does against a bet.
SEQ_MIN_OBSERVED = 40
#: The scouted reads' thresholds (see `folds_blind`, `never_bluffs`).
FOLD_BLIND_MIN = 100
FOLD_BLIND_RATE = 0.70
NEVER_BLUFF_MIN = 40
NEVER_BLUFF_RATE = 0.05
THREE_BET_MIN = 25
THREE_BET_FOLD_RATE = 0.75
#: Under posteriors the bound is the margin, so the bound is held against the break-even fold share of a small
#: three-bet, not against THREE_BET_FOLD_RATE, which already carries a margin over it: held against 0.75 a lower
#: bound threw the read out on melly (143 of 182, 79%) and mellyy (69 of 83), the bot it was written for (5 Oct).
THREE_BET_BREAK_EVEN = 0.67
#: Under posteriors the bound decides how much evidence is enough, so the fixed minimums (set when the inflated rows
#: had thousands of hands) give way to small floors that only keep a read off a handful of hands. On 5 Oct the clean
#: profiles cut HRT to 55 of 59 blind folds and 14 of 14 three-bet folds: the same 93 and 100 percent, below 100 and 25.
POSTERIOR_BLIND_MIN = 15
POSTERIOR_THREE_BET_MIN = 10
#: Under posteriors the "never" reads hold their bound to a line set by what the read does, not to the point-rate
#: line, which already carried a margin: "never bluffs" folds a bluff-catcher, which a pot bet needs about a third
#: bluffs to call and a half-pot bet a quarter, so a bound under a tenth is far inside it (Fold-ver-2, 0 of 40, was
#: lost against 0.05); a re-raise range of 6 percent is still the premium hands (r0ckGarden, 3.6 percent of 3,731,
#: was lost against 0.04).
NEVER_BLUFF_BOUND = 0.10
RARE_RAISE_BOUND = 0.06
#: "River never bluffs" asks for exactly zero only without posteriors. wsp went from 0 of 161 to 4 of 500 when its
#: row was cleaned, and 0.8 percent is still a value range; under posteriors the bound decides, at 3 percent (2 lost
#: runner1, 0 of 106, whose bound is 2.8 percent).
HONEST_RIVER_BOUND = 0.03
#: A bot whose re-raise is always value: it re-raises our open at or below
#: RARE_RAISE_RATE over at least RARE_RAISE_MIN chances. wsp, scouted before we
#: ever played it: 5 of 392, and 0 of 100 facing a three-bet. Every other bot on
#: file re-raises 4 to 40% of the time, so this is not a matter of degree: at
#: one in eighty there is no room in the range for a bluff.
RARE_RAISE_MIN = 120
RARE_RAISE_RATE = 0.04
#: The river-bet read is allowed one more strength class when the sample is
#: this large and the bluff count is exactly zero. 23 September: wsp had bet the
#: river 298 times without a bluff and we called 4,477 into 16,093 with top
#: pair, which was the rest of the match.
HONEST_RIVER_MIN = 100
BIG_BET_MIN = 100
BIG_BET_AIR_RATE = 0.05
SMALL_BET_AIR_RATE = 0.20
EQUILIBRIUM_FOLD = 0.40
#: The two aggressive-side reads (26 September: the coverage gaps). An over-
#: bluffer: river bets that were bluffs by the scout's definition (under half
#: equity against a random hand), over at least OVER_BLUFF_MIN of them; the
#: read is the lower end of the rate's 95 percent interval, and the player
#: turns it into a price. A pot-sized river bet is balanced at a third bluffs.
OVER_BLUFF_MIN = 40
#: An over-folder after the flop: our flop and turn bets it answered, over at
#: least OVER_FOLD_MIN, with raises at most OVER_FOLD_MAX_RAISE of them, since
#: a bot that folds often but raises the rest is not safe to bet into.
OVER_FOLD_MIN = 100
OVER_FOLD_MAX_RAISE = 0.15
#: A frequent re-raiser: its answers to our preflop opens ("preflop:Ur"), over
#: at least RERAISE_MIN of them. 27 Sept: an LLM re-raised v5x's opens with any
#: two cards and v5x folded 10 of 10; v5x folds 76 to 80% of opens to a 3x
#: re-raise at every depth, where any two break even at about 62%.
RERAISE_MIN = 60
EQUILIBRIUM_CALL_SHARE = 0.5
#: "Never calls" fires below this share of calls among the non-fold answers, in both of its rules. It was CALL_FLOOR
#: and EQUILIBRIUM_CALL_SHARE (0.5), which on 3 Oct fired on bots calling 46 to 48% (Dronev4, drone, LazerTank): on
#: Dronev4's copy the read cost 9.9 points (59.0 on, 68.9 off, 20,000 matches), and in the logs its 12 firings on
#: Shadow (59% now) cost 19,896 chips while its 650 on old Blueprint saved 9,979. 0.35 keeps Blueprint as measured
#: on 14 Sept (0.34, the profile the read was written for) and drops the near-half callers.
NEVER_CALL_SHARE = 0.35

#: Posterior reads (opt in, `Profiles(posteriors=True)`; docs/research/2026-10-05-posterior-reads.md).
#: A read fires when the posterior probability that the rate is past its threshold is at least this,
#: which is the one-sided bound at this quantile. One-sided because every read asks one direction.
POSTERIOR_CONFIDENCE = 0.95
#: The population prior's strength (its pseudo-count, alpha + beta) is fitted by method of moments
#: across the file, then held inside these. The floor keeps a field of very different bots from
#: fitting a prior of almost nothing, which would leave the zero-count rates (never bluffs, never
#: re-raises) with the zero-width bound the Wald interval had; two pseudo-trials is a uniform prior's
#: weight. The ceiling stops a field that happens to look alike from swamping a real outlier.
PRIOR_MIN_STRENGTH = 2.0
PRIOR_MAX_STRENGTH = 50.0
#: A bot enters the prior fit with at least this many effective trials of the rate, and the fit needs
#: this many bots; fewer and the prior is uniform. Below it a bot's rate is mostly its own noise.
PRIOR_MIN_TRIALS = 20
PRIOR_MIN_BOTS = 4
#: Matches are estimated as hands over this when a row does not carry its scout's match count.
#: Measured on the scout cache, 5 Oct: 2,649 matches of 35 bots, median over bots of the mean hands
#: per match 38.6, pooled 39.3 (`scripts/posterior_reads_eval.py icc`).
HANDS_PER_MATCH = 39.0
#: Within-match correlation of each rate: the intraclass correlation (ANOVA estimate) per bot over
#: its cached matches, pooled weighted by trials, 5 Oct. Trials inside one match share the opponent's
#: version, our strategy and the blind level, so n trials in m matches carry about
#: n / (1 + (n/m - 1) * rho) independent ones. The values are small, 0.02 to 0.07, but fold-to-bet
#: runs 30 trials a match, so its design effect is still about 2: half the bets are worth counting.
#: The three-bet node is the outlier at 0.19, with 3 trials a match. The research note's guess was 0.1.
MATCH_CORRELATION: Dict[str, float] = {
    "fold_to_bet": 0.035, "call_share": 0.028, "open_fold": 0.071, "open_reraise": 0.032,
    "three_bet_fold": 0.186, "river_bluff": 0.017, "big_air": 0.048, "small_air": 0.018,
    "postflop_fold": 0.021, "postflop_raise": 0.042, "first_bet_fold": 0.020,
}
DEFAULT_CORRELATION = 0.05


def _node(row: Dict, key: str) -> Dict:
    return (row.get("by_history") or {}).get(key, {}) or {}


def _postflop(row: Dict, action: str) -> Tuple[int, int]:
    count = n = 0
    for key in ("flop:Ur", "flop:TcUr", "turn:Ur", "turn:TcUr"):
        node = _node(row, key)
        count += node.get(action, 0)
        n += sum(node.values())
    return count, n


def _first_bets(row: Dict) -> Tuple[int, int]:
    """Folds to our first bet on a street after the flop, checked to or first to act, all three streets."""
    folds = n = 0
    for street in ("flop", "turn", "river"):
        for key in (f"{street}:Ur", f"{street}:TcUr"):
            node = _node(row, key)
            folds += node.get("fold", 0)
            n += sum(node.values())
    return folds, n


#: Every rate a read uses, as (successes, trials) from a profile row.
RATES = {
    "fold_to_bet": lambda r: (r.get("folds", 0), r.get("bets_faced", 0)),
    "call_share": lambda r: (r.get("calls", 0), r.get("calls", 0) + r.get("raises", 0)),
    "open_fold": lambda r: (_node(r, "preflop:Ur").get("fold", 0), sum(_node(r, "preflop:Ur").values())),
    "open_reraise": lambda r: (_node(r, "preflop:Ur").get("raise", 0), sum(_node(r, "preflop:Ur").values())),
    "three_bet_fold": lambda r: (_node(r, "preflop:TrUr").get("fold", 0), sum(_node(r, "preflop:TrUr").values())),
    "river_bluff": lambda r: (r.get("river_bluffs", 0), r.get("river_bets", 0)),
    "big_air": lambda r: (r.get("big_bets_air", 0), r.get("big_bets", 0)),
    "small_air": lambda r: (r.get("small_bets_air", 0), r.get("small_bets", 0)),
    "postflop_fold": lambda r: _postflop(r, "fold"),
    "first_bet_fold": lambda r: _first_bets(r),
    "postflop_raise": lambda r: _postflop(r, "raise"),
}


def matches_of(row: Dict) -> float:
    """
    How many matches a row's counts came from. The scout knows, and a row seeded from 5 Oct keeps
    it in `scout_base`; live hands on top of that, and every row seeded before, are converted at
    HANDS_PER_MATCH. The conversion is the weak part: hands per match runs from 15 (PoetAndCoder)
    to 50 (wsp) because matches end on a bust, so a short-match bot's clustering is overstated
    (which only widens its bounds) and a long-match bot's understated.
    """
    base = row.get("scout_base") or {}
    hands = row.get("hands", 0) or 0
    if base.get("matches"):
        return base["matches"] + max(0, hands - base.get("hands", 0)) / HANDS_PER_MATCH
    return max(1.0, hands / HANDS_PER_MATCH)


def design_effect(row: Dict, trials: int, rate: str) -> float:
    """1 + (k - 1) * rho for k trials per match: the factor clustering inflates the variance by."""
    per_match = trials / matches_of(row)
    rho = MATCH_CORRELATION.get(rate, DEFAULT_CORRELATION)
    return max(1.0, 1.0 + (per_match - 1.0) * rho)


def effective(row: Dict, rate: str, correct: bool = True) -> Tuple[float, float]:
    """(successes, trials) of a rate, deflated to independent-trial equivalents."""
    s, n = RATES[rate](row)
    if n <= 0:
        return 0.0, 0.0
    d = design_effect(row, n, rate) if correct else 1.0
    return s / d, n / d


def fit_prior(rows: Dict[str, Dict], rate: str) -> Tuple[float, float]:
    """
    (mean, strength) of a Beta prior for one rate across every row given: empirical Bayes by method
    of moments. The spread of the bots' observed rates is part true difference and part sampling
    noise; the noise (the mean of mu(1-mu)/n_eff) is subtracted, what is left is the between-bot
    variance tau^2, and strength = mu(1-mu)/tau^2 - 1. Bots are weighted equally, because the prior
    is a statement about what a bot is, not about what a hand is.
    """
    points = []
    for row in rows.values():
        s, n = effective(row, rate)
        if n >= PRIOR_MIN_TRIALS:
            points.append((s / n, n))
    if len(points) < PRIOR_MIN_BOTS:
        return 0.5, PRIOR_MIN_STRENGTH
    rates = [p for p, _ in points]
    mean = sum(rates) / len(rates)
    spread = sum((p - mean) ** 2 for p in rates) / (len(rates) - 1)
    noise = sum(mean * (1.0 - mean) / n for _, n in points) / len(points)
    between = spread - noise
    strength = PRIOR_MAX_STRENGTH if between <= 0 else mean * (1.0 - mean) / between - 1.0
    strength = min(PRIOR_MAX_STRENGTH, max(PRIOR_MIN_STRENGTH, strength))
    # A mean of exactly 0 or 1 makes the prior degenerate, and no field rate is that pure.
    return min(0.99, max(0.01, mean)), strength


def beta_quantile(alpha: float, beta: float, q: float) -> float:
    # scipy is imported here and not at the top, so a bot with posteriors off never loads it.
    from scipy.special import betaincinv
    return float(betaincinv(alpha, beta, q))


def _private_overrides() -> dict:
    """
    Tuned thresholds from outside the repository.

    The values above are the documented defaults and the reasoning behind
    them. The numbers the live bot plays with are the exploitable part of it:
    a rival who knows we fold to river bets from anyone profiled as never
    bluffing can bluff us once it has built that profile. So, like the solved
    strategies, the tuned values live outside the public tree, in
    `~/.chipzen/reads.toml` (`[thresholds]`, upper-case keys as here), and
    override the defaults at import. Absent file, defaults; unknown key, an
    error, so a typo cannot silently leave a read on its default.
    """
    path = os.environ.get("CHIPZEN_READS") or os.path.expanduser("~/.chipzen/reads.toml")
    if not os.path.exists(path):
        return {}
    import tomllib
    with open(path, "rb") as handle:
        table = tomllib.load(handle).get("thresholds", {})
    known = {k for k, v in globals().items() if k.isupper() and isinstance(v, (int, float))}
    unknown = set(table) - known
    if unknown:
        raise ValueError(f"{path}: unknown threshold(s) {sorted(unknown)}; known: {sorted(known)}")
    return table


globals().update(_private_overrides())


def _upper_bound(successes: int, trials: int) -> float:
    """Upper end of the 95 percent Wald interval of a rate."""
    if trials <= 0:
        return 1.0
    rate = successes / trials
    return rate + 1.96 * (rate * (1.0 - rate) / trials) ** 0.5


def _lower_bound(successes: int, trials: int) -> float:
    """Lower end of the 95 percent Wald interval of a rate."""
    if trials <= 0:
        return 0.0
    rate = successes / trials
    return rate - 1.96 * (rate * (1.0 - rate) / trials) ** 0.5


class Profiles:
    """Per-opponent counts, persisted as JSON, rebuilt from match logs."""

    def __init__(self, path: str, sequential: bool = False, bankroll: bool = False,
                 scout_reads: bool = False, posteriors: bool = False):
        self.path = path
        #: Posterior reads (POSTERIOR_CONFIDENCE and below). With this on, every read keeps its own
        #: minimum count (the sequential one where it has one) as the "have we seen this bot" gate,
        #: and decides on the bound of a Beta posterior instead of the point rate or the Wald bound:
        #: a population prior fitted from the whole file, updated by the bot's counts deflated for
        #: within-match correlation. The minimums stay because a prior alone must never fire a read.
        #: The `sequential` flag then has nothing left to change. Off by default.
        self.posteriors = posteriors
        self._priors: Dict[str, Tuple[float, float]] = {}
        #: The two reads that need the scout's counts (`scripts/chipzen_scout.py`):
        #: a big blind that folds to most opens, and a bot whose river bets are
        #: never bluffs. Off by default; measured on thousands of decisions with
        #: both players' cards, 15 September.
        self.scout_reads = scout_reads
        #: Sequential triggers, see SEQ_MIN_OBSERVED. Off by default.
        self.sequential = sequential
        #: Risk what you have won (Ganzfried and Sandholm 2015): with this on,
        #: an exploit fires only while our net against that opponent is not
        #: negative, so a wrong read cannot keep costing chips. Off by default.
        self.bankroll = bankroll
        self.rows: Dict[str, Dict] = {}
        if os.path.exists(path):
            with open(path) as handle:
                self.rows = json.load(handle)

    def _row(self, name: str) -> Dict:
        row = self.rows.setdefault(name, {"bets_faced": 0, "folds": 0, "calls": 0,
                                          "raises": 0, "hands": 0})
        row.setdefault("net", 0)
        row.setdefault("by_history", {})
        return row

    def observe(self, result: dict, our_seat: int, opponent: str, net: int = 0) -> None:
        """
        Count the opponent's answers to our bets in one finished hand, our net
        chips from it, and every action of theirs by the public history it was
        taken at.

        `by_history` is the raw material for a data-biased response (Johanson
        and Bowling 2009): a frequency model per public history, mixed with
        the equilibrium as a prior. The key is the street and the letters of
        the actions so far on it, U for ours and T for theirs, so "flop:UrTc"
        is the opponent acting after our raise and their call. Counts only;
        nothing reads them yet.
        """
        row = self._row(opponent)
        self._priors.clear()        # the field moved by a hand; refit on the next read
        row["hands"] += 1
        row["net"] += int(net)
        previous = None
        street = None
        letters = ""
        for action in result.get("action_history") or []:
            if action["action"].startswith("post"):
                continue
            if action["phase"] != street:
                street, previous, letters = action["phase"], None, ""
            kind = action["action"]
            if action["seat"] != our_seat:
                node = row["by_history"].setdefault(f"{street}:{letters}", {})
                node[kind] = node.get(kind, 0) + 1
                if previous == "raise":
                    row["bets_faced"] += 1
                    row["folds" if kind == "fold" else ("raises" if kind == "raise" else "calls")] += 1
            letters += ("U" if action["seat"] == our_seat else "T") + kind[0]
            previous = kind if action["seat"] == our_seat else None

    # ------------------------------------------------------------------ posteriors

    def prior(self, rate: str) -> Tuple[float, float]:
        """(mean, strength) of the population prior for a rate, fitted from this file's rows."""
        if rate not in self._priors:
            self._priors[rate] = fit_prior(self.rows, rate)
        return self._priors[rate]

    def posterior(self, name: Optional[str], rate: str, correct: bool = True) -> Tuple[float, float]:
        """
        (alpha, beta) of the bot's posterior for a rate. With no row it is the prior itself, which is
        why no read may act on a posterior without its minimum count.
        """
        mean, strength = self.prior(rate)
        s, n = effective(self.rows.get(name or "") or {}, rate, correct)
        return mean * strength + s, (1.0 - mean) * strength + (n - s)

    def posterior_mean(self, name: Optional[str], rate: str, correct: bool = True) -> float:
        alpha, beta = self.posterior(name, rate, correct)
        return alpha / (alpha + beta)

    def upper(self, name: Optional[str], rate: str) -> float:
        """The rate is below this with probability POSTERIOR_CONFIDENCE."""
        return beta_quantile(*self.posterior(name, rate), POSTERIOR_CONFIDENCE)

    def lower(self, name: Optional[str], rate: str) -> float:
        """The rate is above this with probability POSTERIOR_CONFIDENCE."""
        return beta_quantile(*self.posterior(name, rate), 1.0 - POSTERIOR_CONFIDENCE)

    def _trials(self, name: Optional[str], rate: str) -> int:
        return RATES[rate](self.rows.get(name or "") or {})[1]

    def fold_floor_upper(self, name: Optional[str]) -> Optional[float]:
        """
        The posterior upper bound of the bot's fold-to-bet rate, or None below SEQ_MIN_OBSERVED bets.
        The player compares it with the break-even fold share of the bluff it is about to make: a
        bet b into a pot P with no equity needs b / (P + b) folds, a third for half the pot and a
        half for the pot, so "never bluff a station" becomes "do not make a bluff it will not fold
        to often enough". hoops folds 36 percent: a pot bluff loses there and a half-pot one wins.

        One rate for every size is the weak part. On the scout cache every bot folds more to bigger
        bets (hoops 44 percent to half-pot postflop bets and 57 to pot-sized ones), and the rate at
        the decision's own spot (`first_bet_fold`) was tried and dropped: pooled over sizes, it
        overstates folds to small bets, and it released PoetAndCoder's half-pot bluffs although that
        bot folds 30 percent to them. The fix is fold counts by our bet size, which no row keeps yet.
        """
        if not self.exploits_allowed(name) or self._trials(name, "fold_to_bet") < SEQ_MIN_OBSERVED:
            return None
        return self.upper(name, "fold_to_bet")

    # ------------------------------------------------------------------ reads

    def folds_blind(self, name: Optional[str]) -> bool:
        """
        A big blind that folds to at least FOLD_BLIND_RATE of opens over
        FOLD_BLIND_MIN of them. mellyy, scouted: 497 of 631, flat with depth
        and size; each fold is a blind won by a minimum raise.
        """
        if not self.scout_reads or not self.exploits_allowed(name):
            return False
        node = (self.rows.get(name or "") or {}).get("by_history", {}).get("preflop:Ur", {})
        n = sum(node.values())
        if self.posteriors:
            return n >= POSTERIOR_BLIND_MIN and self.lower(name, "open_fold") >= FOLD_BLIND_RATE
        return n >= FOLD_BLIND_MIN and node.get("fold", 0) / n >= FOLD_BLIND_RATE

    def never_bluffs(self, name: Optional[str]) -> bool:
        """
        River bets that were bluffs (under half equity against a random hand)
        in fewer than NEVER_BLUFF_RATE of at least NEVER_BLUFF_MIN river bets.
        runner1, scouted: 0 of 63; its minimum postflop betting equity was 0.58.
        """
        if not self.scout_reads or not self.exploits_allowed(name):
            return False
        row = self.rows.get(name or "") or {}
        bets = row.get("river_bets", 0)
        if self.posteriors:
            # The exact zero `river_never_bluffs` keeps stands here too. The player asks that read only after
            # this one, and a strong prior lifts a zero's bound over 0.10 (thirty bots bluffing 40 percent put 0 of
            # 150 above it), so without this the pair would be stricter than main, which fires both on that zero.
            zero = bets >= HONEST_RIVER_MIN and row.get("river_bluffs", 0) == 0
            return bets >= NEVER_BLUFF_MIN and (zero or self.upper(name, "river_bluff") < NEVER_BLUFF_BOUND)
        return bets >= NEVER_BLUFF_MIN and row.get("river_bluffs", 0) / bets < NEVER_BLUFF_RATE

    def never_three_bets(self, name: Optional[str]) -> bool:
        """
        A bot that re-raises our open almost never, so its re-raise is value.

        The same node `folds_blind` already reads, looking at the other key in
        it. On 23 September that dictionary was in memory during the match,
        `{'call': 217, 'fold': 170, 'raise': 5}`, and nothing asked how often
        it raised; we four-bet all in with ace-king into kings and lost the
        fixture. The distinction is not close: every other profile on file
        re-raises between 4 and 40% of the time.
        """
        if not self.scout_reads or not self.exploits_allowed(name):
            return False
        node = (self.rows.get(name or "") or {}).get("by_history", {}).get("preflop:Ur", {})
        n = sum(node.values())
        if self.posteriors:
            return n >= RARE_RAISE_MIN and self.upper(name, "open_reraise") <= RARE_RAISE_BOUND
        return n >= RARE_RAISE_MIN and node.get("raise", 0) / n <= RARE_RAISE_RATE

    def river_never_bluffs(self, name: Optional[str]) -> bool:
        """
        A stronger form of `never_bluffs`: a large sample and not one bluff.

        `never_bluffs` allows a few, because a rate below 5% of 40 bets is
        already worth acting on. This one is the case where the count is
        exactly zero over at least HONEST_RIVER_MIN bets, which is where a
        hand we would normally pay off should also fold. Under posteriors the
        exact zero gives way to a bound of HONEST_RIVER_BOUND, and the player
        still asks it only once `never_bluffs` has fired.
        """
        if not self.scout_reads or not self.exploits_allowed(name):
            return False
        row = self.rows.get(name or "") or {}
        enough = row.get("river_bets", 0) >= HONEST_RIVER_MIN
        if self.posteriors:
            # Never stricter than the exact zero: a zero's bound moves with the other bots' bluff rates (runner1,
            # 0 of 106, sat at 2.8 percent on the file and 3.2 in a field of heavier bluffers), so the zero stands
            # on its own and the bound only adds the near-zeros like wsp's 4 of 500.
            return enough and (row.get("river_bluffs", 0) == 0 or self.upper(name, "river_bluff") <= HONEST_RIVER_BOUND)
        return enough and row.get("river_bluffs", 0) == 0

    def folds_to_three_bet(self, name: Optional[str]) -> bool:
        """
        Folds to at least THREE_BET_FOLD_RATE of three-bets over THREE_BET_MIN of
        them: the public history "they open, we re-raise, they act". mellyy,
        scouted: 25 of 29. A small three-bet breaks even at about 67 percent.
        """
        if not self.scout_reads or not self.exploits_allowed(name):
            return False
        node = (self.rows.get(name or "") or {}).get("by_history", {}).get("preflop:TrUr", {})
        n = sum(node.values())
        if self.posteriors:
            return n >= POSTERIOR_THREE_BET_MIN and self.lower(name, "three_bet_fold") >= THREE_BET_BREAK_EVEN
        return n >= THREE_BET_MIN and node.get("fold", 0) / n >= THREE_BET_FOLD_RATE

    def big_bets_are_value(self, name: Optional[str]) -> bool:
        """
        A sizing tell: first bets of 0.7 pot and up that were air (under 0.4
        equity) in fewer than BIG_BET_AIR_RATE of at least BIG_BET_MIN, while
        the small bets were air often enough (SMALL_BET_AIR_RATE) that the split
        is a tell and not tightness. PoetAndCoder, scouted: 0 of 429 big, 39
        percent of 1,080 small.
        """
        if not self.scout_reads or not self.exploits_allowed(name):
            return False
        row = self.rows.get(name or "") or {}
        big, small = row.get("big_bets", 0), row.get("small_bets", 0)
        if self.posteriors:
            return big >= BIG_BET_MIN and small >= BIG_BET_MIN and self.upper(name, "big_air") < BIG_BET_AIR_RATE \
                and self.lower(name, "small_air") >= SMALL_BET_AIR_RATE
        return big >= BIG_BET_MIN and row.get("big_bets_air", 0) / big < BIG_BET_AIR_RATE \
            and small >= BIG_BET_MIN and row.get("small_bets_air", 0) / small >= SMALL_BET_AIR_RATE

    def river_bluff_floor(self, name: Optional[str]) -> Optional[float]:
        """
        The lower bound of the share of its river bets that were bluffs, or
        None below OVER_BLUFF_MIN river bets. The mirror of `never_bluffs`:
        that read folds to an honest bettor, this one lets the player call a
        bluffer when the bound pays for the call. Shadow, scouted 26 Sept, bluffed
        23 of its 48 river bets and no read fired on it.
        """
        if not self.scout_reads or not self.exploits_allowed(name):
            return None
        row = self.rows.get(name or "") or {}
        bets = row.get("river_bets", 0)
        if bets < OVER_BLUFF_MIN:
            return None
        if self.posteriors:
            return self.lower(name, "river_bluff")
        return max(0.0, _lower_bound(row.get("river_bluffs", 0), bets))

    def postflop_fold_floor(self, name: Optional[str]) -> Optional[float]:
        """
        The lower bound of the share of our first flop and turn bets it folded
        to ("flop:Ur", "flop:TcUr" and the turn's two), or None below
        OVER_FOLD_MIN answers or when it raised more than OVER_FOLD_MAX_RAISE of
        them. A half-pot bet with no equity breaks even at a third folds.
        """
        if not self.scout_reads or not self.exploits_allowed(name):
            return None
        nodes = (self.rows.get(name or "") or {}).get("by_history", {})
        folds = raises = n = 0
        for key in ("flop:Ur", "flop:TcUr", "turn:Ur", "turn:TcUr"):
            node = nodes.get(key, {})
            folds += node.get("fold", 0)
            raises += node.get("raise", 0)
            n += sum(node.values())
        if self.posteriors:
            # Safe to bet into only if it credibly rarely raises, so the raise share is read on its upper bound.
            if n < OVER_FOLD_MIN or self.upper(name, "postflop_raise") > OVER_FOLD_MAX_RAISE:
                return None
            return self.lower(name, "postflop_fold")
        if n < OVER_FOLD_MIN or raises / n > OVER_FOLD_MAX_RAISE:
            return None
        return _lower_bound(folds, n)

    def reraise_floor(self, name: Optional[str]) -> Optional[float]:
        """The lower bound of the share of our opens it re-raised, or None below RERAISE_MIN."""
        if not self.scout_reads or not self.exploits_allowed(name):
            return None
        node = (self.rows.get(name or "") or {}).get("by_history", {}).get("preflop:Ur", {})
        n = sum(node.values())
        if n < RERAISE_MIN:
            return None
        if self.posteriors:
            return self.lower(name, "open_reraise")
        return max(0.0, _lower_bound(node.get("raise", 0), n))

    def exploits_allowed(self, name: Optional[str]) -> bool:
        """With the bankroll rule on, only while we are not behind against them."""
        if not self.bankroll:
            return True
        row = self.rows.get(name or "")
        return bool(row) and row.get("net", 0) >= 0

    def fold_to_bet(self, name: Optional[str]) -> Tuple[Optional[float], int]:
        """(rate, bets observed); rate is None until MIN_OBSERVED bets."""
        row = self.rows.get(name or "")
        if not row or row["bets_faced"] < MIN_OBSERVED:
            return None, (row or {}).get("bets_faced", 0)
        return row["folds"] / row["bets_faced"], row["bets_faced"]

    def never_folds(self, name: Optional[str]) -> bool:
        """
        Folds to our bets credibly less than an equilibrium would. Under posteriors that is the
        upper bound under EQUILIBRIUM_FOLD from SEQ_MIN_OBSERVED bets, and the player also asks
        whether the particular bluff needs more folds than that (`fold_floor_upper`).
        """
        if not self.exploits_allowed(name):
            return False
        if self.posteriors:
            upper = self.fold_floor_upper(name)
            return upper is not None and upper < EQUILIBRIUM_FOLD
        if self.sequential:
            row = self.rows.get(name or "")
            if row and row["bets_faced"] >= SEQ_MIN_OBSERVED and \
                    _upper_bound(row["folds"], row["bets_faced"]) < EQUILIBRIUM_FOLD:
                return True
        rate, _ = self.fold_to_bet(name)
        return rate is not None and rate < FOLD_FLOOR

    def never_calls(self, name: Optional[str]) -> bool:
        """
        A fold-or-raise opponent: it answers a bet by folding or raising and
        almost never by calling. Against `Blueprint` on 14 September (1,005
        folds, 322 raises, 39 calls) every big pot lost was a call of its
        all-in with a hand that was not the best; a bot like that only raises
        when it has it, so a shove from it is answered by the top strength
        class alone.
        """
        if not self.exploits_allowed(name):
            return False
        row = self.rows.get(name or "")
        if not row:
            return False
        answered = row["calls"] + row["raises"]
        if self.posteriors:
            # The threshold stays at 0.35, now on the bound: Dronev4's 31 calls in 67 answers sits at 46
            # percent, and nothing that close to half should read as a bot that never calls.
            return answered >= SEQ_MIN_OBSERVED // 2 and self.upper(name, "call_share") < NEVER_CALL_SHARE
        if self.sequential and answered >= SEQ_MIN_OBSERVED // 2 and \
                _upper_bound(row["calls"], answered) < NEVER_CALL_SHARE:
            return True
        if row["bets_faced"] < MIN_OBSERVED:
            return False
        return answered >= 40 and row["calls"] / answered < NEVER_CALL_SHARE

    def save(self) -> None:
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        tmp = self.path + ".tmp"
        with open(tmp, "w") as handle:
            json.dump(self.rows, handle, indent=1, sort_keys=True)
        os.replace(tmp, self.path)

    #: Opponents that changed: their rows count only hands from matches that started after this time (epoch seconds),
    #: from `results/chipzen/profile_since.json` ({"Blueprint": "2026-09-30T00:00:00+05:30"}). A bot its author
    #: rewrote is a new bot, and 14,000 hands of the old one teach the reads the wrong thing: Blueprint went from
    #: playing 35% of its small blinds to over 90% between two matches on 29 Sept, for every opponent.
    SINCE_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "chipzen",
                              "profile_since.json")

    def since(self) -> Dict[str, float]:
        import datetime as dt
        try:
            raw = json.load(open(self.SINCE_FILE))
        except (OSError, ValueError):
            return {}
        out = {}
        for name, when in raw.items():
            try:
                out[name] = dt.datetime.fromisoformat(str(when)).timestamp()
            except ValueError:
                continue
        return out

    def rebuild(self, *dirs: str) -> "Profiles":
        """
        Recount from every match log, so the file is never the only copy.

        Rows marked `scouted` (written by `scripts/chipzen_scout.py` from the
        platform's records of a bot's matches against others) are kept as the
        starting point, and live hands accumulate on top of them: a round-robin
        meets each opponent once, so a read that starts at hand one is the
        only kind that helps.

        The starting point is the row's `scout_base`, the scout's own counts,
        never the saved row. Until 4 Oct it was the saved row, which already
        held the live hands, so every start counted every live hand once more:
        Blueprint's row grew by 2,916 hands a start with no new match, and the
        scout's never-shrink rule then refused every fresh scout of it. A row
        written before `scout_base` existed is frozen as its own base the first
        time through, so it stops growing; re-seeding it from the scout cache
        is what makes it clean.
        """
        kept = {}
        for name, row in self.rows.items():
            if not row.get("scouted"):
                continue
            base = row.get("scout_base")
            if base is None:
                base = {k: v for k, v in row.items() if k != "scout_base"}
            fresh = copy.deepcopy(base)
            fresh["scouted"] = True
            fresh["scout_base"] = base
            kept[name] = fresh
        self.rows = kept
        self._priors.clear()
        cutoff = self.since()
        seen = set()
        for directory in dirs:
            for path in sorted(glob.glob(os.path.join(directory, "*.jsonl"))):
                if os.path.basename(path) in seen:
                    continue
                seen.add(os.path.basename(path))
                seat, opponent, before = None, None, None
                with open(path) as handle:
                    for line in handle:
                        try:
                            frame = json.loads(line)
                        except ValueError:
                            continue
                        if frame.get("frame") == "match_start":
                            seat = frame.get("seat")
                            opponent = next((s.get("display_name") for s in frame.get("seats") or []
                                             if not s.get("is_self")), None)
                            if opponent in cutoff and (frame.get("at") or 0) < cutoff[opponent]:
                                opponent = None          # an older version of this bot: not counted
                        elif frame.get("frame") == "round_start":
                            before = (frame.get("state") or {}).get("stacks")
                        elif frame.get("frame") == "round_result" and seat is not None and opponent:
                            result = frame["result"]
                            after = result.get("stacks")
                            net = after[seat] - before[seat] if before and after else 0
                            self.observe(result, seat, opponent, net)
        return self
