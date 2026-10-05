"""
The off-tree preflop answer (`ArenaPlayer.offtree_preflop`) and the answering history in the record (5 October).

Every cap-2 rung offers only all-in at the third preflop raise, so a small four-bet is read as all-in and the
fold prices a shove of the whole stack; the price-guard audit found seven such folds at 17 to 23 percent. The
rule prices the real bet against the range the answering solution raises with on that line.

No shipped tree has an all-in-only preflop level (the one-raise solver has nothing at the second raise, the
(4, 2) taper nothing at the third), so the rule's tests play a small stand-in solver on the (4, 2, 1) schedule
the ladder rungs use: its strategy is a dict holding exactly the bettor's two nodes, and its own answer at our
node is a fold, as the 5 Oct rungs' was. The record's new fields are tested on the shipped solvers.
"""
import os

import numpy as np
import pytest

from abstraction.betting import FOLD
from chipzen.player import ArenaPlayer, Solver
from scripts.audit_price_guard import answered_history, companion_schedule

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SHIPPED = os.path.join(ROOT, "results", "cfr", "nolimit_strategy.pkl")
TAPER = os.path.join(ROOT, "results", "cfr", "nolimit_taper_42.pkl")
FOUR_BET = ("AA", "KK", "QQ", "AKs", "AKo")


def entry(seat, action, amount, phase="preflop"):
    return {"seat": seat, "action": action, "amount": amount, "phase": phase, "is_timeout": False}


BLINDS = [entry(0, "post_small_blind", 50), entry(1, "post_big_blind", 100)]


class ClassAbstraction:
    """Preflop buckets are the 169 classes themselves, as the lossless ladders' are."""
    postflop_buckets = 6

    def __init__(self, ranges):
        self.ranges = ranges

    def bucket(self, hole, board, rng=None):
        return self.ranges.class_of(hole) if not board else 0


def stand_in(ranges, open_share=None):
    """
    A 100bb (4, 2, 1) solver whose small blind opens pot with every hand (or `open_share` of a hand, per
    class label) and four-bets the top five classes over a 2x three-bet; its own answer is always a fold.
    """
    strategy = {}
    for i, label in enumerate(ranges.labels):
        opened = (open_share or {}).get(label, 1.0)
        # Facing the big blind: fold, call, half, pot, 2x, all-in.
        strategy[f"{i}|"] = np.array([1.0 - opened, 0.0, 0.0, opened, 0.0, 0.0])
        # Facing our 2x three-bet at the third raise: fold, call, all-in.
        strategy[f"{i}|34"] = np.array([0.0, 0.0, 1.0]) if label in FOUR_BET else np.array([0.5, 0.5, 0.0])
    solver = Solver(path="stand-in", depth_bb=100.0, schedule=(4, 2, 1), strategy=strategy,
                    abstraction=ClassAbstraction(ranges))

    def agent(game, player_id, mask, history):
        solver.misses[1] += 1
        return FOLD
    solver.agent = agent
    return solver


@pytest.fixture(scope="module")
def shipped():
    return ArenaPlayer([SHIPPED], np.random.default_rng(3), companions=[TAPER])


@pytest.fixture(scope="module")
def player():
    out = ArenaPlayer([SHIPPED], np.random.default_rng(5))
    assert out.short_ranges is not None, "the push-fold table (results/cfr/chance/push_fold_ranges.npz) is needed"
    out.ladder = [stand_in(out.short_ranges)]
    out.companions = []
    return out


def four_bet(hole, level=2600, opponent_start=10000):
    """
    We are the big blind at 100bb. They open pot to 300, we three-bet 2x pot to 1,500, and they four-bet to
    `level`, which the (4, 2, 1) schedule can only read as all-in. At 2,600 they keep 7,400 behind and the
    price is 1,100 into 5,200, 0.21.
    """
    behind = opponent_start - level
    return {"hand_number": 4, "phase": "preflop", "board": [], "your_hole_cards": hole,
            "pot": level + 1500, "your_stack": 8500, "opponent_stacks": [behind], "to_call": level - 1500,
            "min_raise": min(8500, 2 * level - 1500), "max_raise": 8500,
            "action_history": BLINDS + [entry(0, "raise", 300), entry(1, "raise", 1500), entry(0, "raise", level)]}


def decide(player, state, offtree=True, guard=False, valid=("fold", "call", "raise")):
    player.offtree_preflop, player.price_misread = offtree, guard
    try:
        return player.decide(state, list(valid), 1)
    finally:
        player.offtree_preflop = player.price_misread = False


def test_the_bettors_range_is_the_product_of_its_actions_on_the_line(player):
    ranges = player.short_ranges
    solver = stand_in(ranges, open_share={"AKo": 0.5, "KK": 0.0})
    reach = player.raise_reach(solver, "345")
    assert reach[ranges.index["AA"]] == 1.0
    assert reach[ranges.index["AKo"]] == 0.5        # opened half the time, then always four-bet
    assert reach[ranges.index["KK"]] == 0.0         # never opened pot, so not on this line
    assert reach[ranges.index["72o"]] == 0.0        # opened, but never four-bets
    # Our own actions do not enter it: the same line after a different three-bet size has no node here.
    assert player.raise_reach(solver, "325") is None


def test_only_a_raise_the_schedule_cannot_name_is_priced():
    solver = Solver(path="", depth_bb=100.0, schedule=(4, 2, 1), strategy={}, abstraction=None)
    assert ArenaPlayer._unnamed_raise(solver, "345")          # the third raise: all-in is the only size
    assert not ArenaPlayer._unnamed_raise(solver, "35")       # the second has 2x pot as well
    assert not ArenaPlayer._unnamed_raise(solver, "5")        # an open shove, read by size
    one_raise = Solver(path="", depth_bb=100.0, schedule=1, strategy={}, abstraction=None)
    assert not ArenaPlayer._unnamed_raise(one_raise, "35")    # nothing at all there, not even all-in


def test_a_small_four_bet_is_called_when_the_equity_against_the_range_pays(player):
    before = player.stats.offtree_preflop_calls
    out = decide(player, four_bet(["Ah", "Kd"]))
    record = out["record"]
    assert record["history"] == "345" and not record["miss"], record
    assert out["action"] == "call" and record["adjusted"] == "priced an off-tree raise", record
    assert record["offtree"]["price"] == pytest.approx(1100 / 5200, abs=1e-3)
    assert record["offtree"]["equity"] > record["offtree"]["price"] + player.OFFTREE_MARGIN
    assert player.stats.offtree_preflop_calls == before + 1


def test_the_rule_is_off_unless_asked_for(player):
    assert not player.offtree_preflop
    out = decide(player, four_bet(["Ah", "Kd"]), offtree=False)
    assert out["action"] == "fold" and "offtree" not in out["record"]


def test_a_hand_that_the_range_crushes_still_folds(player):
    # Seven-deuce against aces to ace-king is about 21 percent, under the price plus the margin.
    out = decide(player, four_bet(["7h", "2d"]))
    assert out["action"] == "fold" and out["record"]["adjusted"] is None
    assert out["record"]["offtree"]["equity"] < out["record"]["offtree"]["price"] + player.OFFTREE_MARGIN


def test_a_big_four_bet_is_left_to_the_strategy(player):
    # To 6,000 with 4,000 behind: 4,500 into 12,000 is 0.375, and ace-king's 0.39 is not five points clear.
    out = decide(player, four_bet(["Ah", "Kd"], level=6000))
    assert out["action"] == "fold" and out["record"]["adjusted"] is None, out["record"]


def test_a_real_all_in_is_not_priced(player):
    # The same line, but the four-bet is their whole stack: the strategy priced it correctly.
    out = decide(player, four_bet(["Ah", "Kd"], level=2600, opponent_start=2600))
    assert out["record"]["history"].endswith("5")
    assert out["action"] == "fold" and "offtree" not in out["record"]


def test_postflop_is_not_touched(player):
    # A small third raise on the flop, read as all-in with chips behind: preflop ranges say nothing there.
    state = {"hand_number": 5, "phase": "flop", "board": ["Ah", "Tc", "4s"], "your_hole_cards": ["Ad", "Kd"],
             "pot": 3200, "your_stack": 8000, "opponent_stacks": [7000], "to_call": 600,
             "min_raise": 1800, "max_raise": 8000,
             "action_history": BLINDS + [entry(0, "raise", 200), entry(1, "call", 100),
                                         entry(1, "raise", 200, "flop"), entry(0, "raise", 800, "flop"),
                                         entry(1, "raise", 1400, "flop"), entry(0, "raise", 2000, "flop")]}
    out = decide(player, state)
    assert out["record"]["history"].endswith("5") and "offtree" not in out["record"], out["record"]


def test_the_price_guard_defers_to_the_range_where_the_rule_priced_the_spot(player):
    # King-jack beats a random hand 61 percent of the time, so at 0.21 the guard alone calls; against
    # the four-bet range it has 22 percent, and with both on the range's answer stands.
    alone = decide(player, four_bet(["Kh", "Jd"]), offtree=False, guard=True)
    assert alone["action"] == "call" and alone["record"]["adjusted"] == "priced a misread all-in"
    both = decide(player, four_bet(["Kh", "Jd"]), offtree=True, guard=True)
    assert both["action"] == "fold" and both["record"]["adjusted"] is None, both["record"]


def test_the_record_names_the_history_that_answered(shipped):
    # A plain flop bet: the primary holds the node, so the answer came from its own history and no companion
    # was asked.
    state = {"hand_number": 2, "phase": "flop", "board": ["Ah", "Tc", "4s"], "your_hole_cards": ["Ts", "9h"],
             "pot": 500, "your_stack": 9800, "opponent_stacks": [9700], "to_call": 100,
             "min_raise": 200, "max_raise": 9800,
             "action_history": BLINDS + [entry(0, "raise", 200), entry(1, "call", 100),
                                         entry(1, "check", 0, "flop"), entry(0, "raise", 100, "flop")]}
    record = shipped.decide(state, ["fold", "call", "raise"], 1)["record"]
    assert record["companion"] is None
    assert record["answered_history"] == record["history"]
    assert "companion_history" not in record and "alt_history" not in record


def raised_flop():
    """Their min-raise of our flop bet: off the one-raise tree, a sized re-raise on the taper's."""
    return {"hand_number": 3, "phase": "flop", "board": ["Ah", "Tc", "4s"], "your_hole_cards": ["Ad", "Qh"],
            "pot": 1300, "your_stack": 9500, "opponent_stacks": [9200], "to_call": 300,
            "min_raise": 900, "max_raise": 9500,
            "action_history": BLINDS + [entry(0, "raise", 200), entry(1, "call", 100),
                                        entry(1, "raise", 300, "flop"), entry(0, "raise", 600, "flop")]}


def test_the_record_keeps_the_companions_own_history(shipped):
    record = shipped.decide(raised_flop(), ["fold", "call", "raise"], 1)["record"]
    assert record["miss"] and record["companion"] == "100bb(4, 2)", record
    assert record["history"].endswith("5")                     # the primary's read: all-in
    assert record["companion_history"] == record["answered_history"]
    assert not record["companion_history"].endswith("5")       # the taper's: a sized re-raise


def test_the_audit_rebuilds_the_companions_history_as_the_bot_built_it(shipped):
    # Records before 5 Oct have no `answered_history`; the audit rebuilds it from the arena's actions on the
    # schedule the companion field names, and must land on the history the live bot asked.
    state = raised_flop()
    record = dict(shipped.decide(state, ["fold", "call", "raise"], 1)["record"])
    live = record.pop("answered_history")
    record.pop("companion_history")
    assert companion_schedule(record["companion"]) == (4, 2)
    assert companion_schedule("50bb2") == 2 and companion_schedule("collapsed:21/1") is None
    rebuilt, source = answered_history(record, state["action_history"], state["your_stack"],
                                       state["opponent_stacks"][0], 1)
    assert source == "companion, rebuilt" and rebuilt == live


def test_the_record_keeps_the_collapsed_history(shipped):
    # A preflop third raise read as all-in, called, then a flop bet: the street is re-read.
    state = {"hand_number": 10, "phase": "flop", "board": ["Ah", "Tc", "4s"], "your_hole_cards": ["Ts", "9h"],
             "pot": 3500, "your_stack": 8500, "opponent_stacks": [8000], "to_call": 500,
             "min_raise": 1000, "max_raise": 8500,
             "action_history": BLINDS + [entry(0, "raise", 200), entry(1, "raise", 525),
                                         entry(0, "raise", 1500), entry(1, "call", 975),
                                         entry(1, "check", 0, "flop"), entry(0, "raise", 500, "flop")]}
    record = shipped.decide(state, ["fold", "call", "raise"], 1)["record"]
    assert record["alt_history"] != record["history"]
    # Both solvers miss on the true history, and the taper answers on its own re-read; the record keeps the
    # primary's re-read, the taper's translation and the history that actually answered.
    assert str(record["companion"]).startswith("collapsed:"), record
    assert record["answered_history"] == record["companion"][len("collapsed:"):]
    assert record["companion_history"] not in (record["history"], record["answered_history"])
