"""
The measuring instruments must read zero on a mirror.

Three defects in the cross-tree gate went unnoticed for three days in
September 2026 (every gate at 200 chips whatever the rung, stack-capped
fold/call entries rejected as the wrong width, one raise cap for both seats),
and each produced a confident wrong story about the solver. Every one would
have failed a self-play check. So the two instruments the project now decides
by, `play_pickles` (a solve against a solve, each seat on its own tree at the
rung's stack) and `chipzen_duel` (whole bot against whole bot), are pinned to
zero on a mirror here, small enough for the suite, with the exact
configuration the decisions use.
"""
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from cfr.flat import load_strategy  # noqa: E402
from evaluation.benchmark import benchmark, cfr_agent  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RUNG = os.path.join(ROOT, "results", "cfr", "ladder169l", "nolimit_18bb.pkl")
LADDER = os.path.join(ROOT, "results", "cfr", "ladder169l_v5c")


def _agent(saved, seed):
    misses = [0, 0]
    args = saved["args"]
    return cfr_agent(saved["strategy"], saved["abstraction"], np.random.default_rng(seed),
                     misses=misses, raise_cap=args["raise_cap"], on_miss="call", stack_cap=True), misses


def test_a_solve_against_itself_at_its_own_stack_reads_zero_with_no_misses():
    if not os.path.exists(RUNG):
        pytest.skip("the 18bb rung is not on this machine")
    saved = load_strategy(RUNG)
    a, ma = _agent(saved, 0)
    b, mb = _agent(saved, 1000)
    stack, bb = int(saved["args"]["stack"]), int(saved["args"]["big_blind"])
    cap = saved["args"]["raise_cap"]
    result = benchmark(a, b, "mirror", hands=3000, seed=0, starting_stack=stack,
                       small_blind=bb // 2, big_blind=bb, raise_caps=(cap, cap))
    # 3,000 duplicate hands of an 18bb game read ±4 BB/100; zero is the answer.
    assert abs(result.bb_per_100) < 8.0, f"self-play read {result.bb_per_100:+.1f} BB/100"
    # At its own stack, with the stack cap honoured, a solve has an entry for
    # every node it reaches: a miss here means the harness built a history or
    # an action list the tree does not have.
    assert ma[0] == 0 and mb[0] == 0, f"misses {ma} / {mb} in self-play"


def test_the_duel_reads_even_on_a_mirror():
    if not os.path.isdir(LADDER):
        pytest.skip("the v5c ladder is not on this machine")
    from scripts.chipzen_duel import Dealer, build
    a = build(LADDER, "--deep-primary --stack-cap", "A", np.random.default_rng(1), None)
    b = build(LADDER, "--deep-primary --stack-cap", "B", np.random.default_rng(2), None)
    a.opponent, b.opponent = "B", "A"
    rng = np.random.default_rng(0)
    deck = np.arange(52)
    diffs = []
    for i in range(300):
        rng.shuffle(deck)
        cards = [int(c) for c in deck[:9]]
        first = Dealer([a, b], cards, 2500, 50, 100, 2 * i + 1, ("B", "A")).play()
        second = Dealer([b, a], cards, 2500, 50, 100, 2 * i + 2, ("A", "B")).play()
        diffs.append((first[0] + second[1]) / 2.0)
    diffs = np.array(diffs)
    se = diffs.std() / np.sqrt(diffs.size)
    assert abs(diffs.mean()) < 4 * max(se, 1.0), f"mirror read {diffs.mean():+.1f} ± {se:.1f} chips/hand"
    # The dealer must close every hand: a hand that did not close raises.
    assert a.stats.decisions > 0 and b.stats.decisions > 0


class _Scripted:
    """A duel player that plays a fixed sequence, then calls."""
    def __init__(self, moves):
        self.moves, self.stats = list(moves), type("S", (), {"decisions": 0})()

    def decide(self, state, valid, seat):
        self.stats.decisions += 1
        move = self.moves.pop(0) if self.moves else ("call", 0)
        action, amount = move
        if action == "raise":
            return {"action": "raise", "params": {"amount": amount}}
        return {"action": action if action in valid else "call", "params": {}}


def test_the_dealer_asks_the_opponent_to_answer_a_shove():
    # 20 September: a shove made after two actions on the street was closed
    # unanswered (a free showdown for the smaller commitment), and after the
    # first fix it was refunded and the hand played on as if it had never
    # happened. The opponent must be asked, and a fold must cost exactly what
    # it had committed.
    from scripts.chipzen_duel import Dealer
    cards = [0, 13, 12, 25, 30, 44, 7, 21, 48]      # 2c2d against AcAd; the aces hold
    sb = _Scripted([("raise", 300), ("fold", 0)])
    bb = _Scripted([("raise", 10000)])
    net = Dealer([sb, bb], cards, [10000, 10000], 50, 100, 1, ("x", "y")).play()
    assert sb.stats.decisions == 2, "the small blind was not asked to answer the shove"
    assert net == [-300, 300]
    # A call for less closes the street and the excess comes back: the short
    # stack risks only its own chips.
    sb = _Scripted([("raise", 10000)])
    bb = _Scripted([("call", 0)])
    net = Dealer([sb, bb], cards, [10000, 3000], 50, 100, 1, ("x", "y")).play()
    assert bb.stats.decisions == 1 and abs(net[0]) == 3000 and net[0] + net[1] == 0


def test_the_field_archetypes_read_even_against_themselves_and_carry_every_parameter():
    # The panel (chipzen/archetypes.py) is an instrument like the duel, so its
    # players are pinned to zero on a mirror too; a shape that favours one
    # seat would read as a set's strength. The parameter rows are checked
    # complete because a missing key would raise mid-duel, an hour in.
    from chipzen.archetypes import ARCHETYPES, PARAMS, build_archetype
    from scripts.chipzen_duel import Dealer
    keys = {"open_eq", "limp_eq", "threebet_eq", "fold_margin", "raise_eq", "raise_p", "bluff_p",
            "call_p", "defend_eq", "defend3_eq"}
    for kind in ARCHETYPES:
        assert keys <= set(PARAMS[kind]) <= keys | {"open_frac"}, kind
    rng = np.random.default_rng(0)
    deck = np.arange(52)
    for kind in ("station", "maniac"):
        a, b = build_archetype(kind, np.random.default_rng(1)), build_archetype(kind, np.random.default_rng(2))
        diffs = []
        for i in range(400):
            rng.shuffle(deck)
            cards = [int(c) for c in deck[:9]]
            first = Dealer([a, b], cards, [2500, 2500], 50, 100, 2 * i + 1, ("b", "a")).play()
            second = Dealer([b, a], cards, [2500, 2500], 50, 100, 2 * i + 2, ("a", "b")).play()
            diffs.append((first[0] + second[1]) / 2.0)
        diffs = np.array(diffs)
        se = diffs.std() / np.sqrt(diffs.size)
        assert abs(diffs.mean()) < 4 * max(se, 1.0), f"{kind} mirror read {diffs.mean():+.1f} ± {se:.1f}"
