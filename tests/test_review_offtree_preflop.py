"""
Independent review of branch offtree-preflop (5 October): the cases `tests/test_offtree_preflop.py` leaves
open, for the `--offtree-preflop` rule, the always-on record fields and the audit's rebuild of a companion's
history.

The rule's tests play small stand-in solvers on the (4, 2, 1) schedule, whose strategy is a dict holding
only the nodes a test needs, the same device the branch's own tests use; the record's tests on the solver
paths patch nothing but the river solve. A test marked xfail(strict) is a review finding: the code does not
do what the branch's write-up says it does.
"""
import importlib.util
import os
import subprocess
import sys

import numpy as np
import pytest

from abstraction.betting import ALL_IN, CHECK_CALL, FOLD
from chipzen.player import ArenaPlayer, Solver
from engine.cards import Card
from scripts.audit_price_guard import answered_history, companion_schedule

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SHIPPED = os.path.join(ROOT, "results", "cfr", "nolimit_strategy.pkl")
TAPER = os.path.join(ROOT, "results", "cfr", "nolimit_taper_42.pkl")
TOP_FIVE = ("AA", "KK", "QQ", "AKs", "AKo")


def entry(seat, action, amount, phase="preflop"):
    return {"seat": seat, "action": action, "amount": amount, "phase": phase, "is_timeout": False}


BLINDS = [entry(0, "post_small_blind", 50), entry(1, "post_big_blind", 100)]


class ClassAbstraction:
    """Preflop buckets are the 169 classes, as the lossless ladders' are; one postflop bucket."""
    postflop_buckets = 6

    def __init__(self, ranges):
        self.ranges = ranges

    def bucket(self, hole, board, rng=None):
        return self.ranges.class_of(hole) if not board else 0


def solver_of(ranges, nodes, answer=FOLD, misses=False, depth=100.0, schedule=(4, 2, 1)):
    """
    A stand-in rung. `nodes` maps a history to a function of the class label giving that node's row.
    `answer` is what it plays at our node; `misses` makes every lookup a miss, as a rung without the
    node would.
    """
    strategy = {}
    for i, label in enumerate(ranges.labels):
        for history, row in nodes.items():
            strategy[f"{i}|{history}"] = np.asarray(row(label), dtype=float)
    solver = Solver(path="stand-in", depth_bb=depth, schedule=schedule, strategy=strategy,
                    abstraction=ClassAbstraction(ranges))

    def agent(game, player_id, mask, history):
        solver.misses[1] += 1
        if misses:
            solver.misses[0] += 1
        return answer
    solver.agent = agent
    return solver


def open_pot(label):
    return [0.0, 0.0, 0.0, 1.0, 0.0, 0.0]          # fold, call, half, pot, 2x, all-in


def four_bets(labels):
    return lambda label: [0.0, 0.0, 1.0] if label in labels else [0.5, 0.5, 0.0]   # fold, call, all-in


def standard(ranges, **kw):
    """The branch's stand-in: every class opens pot, the top five four-bet over our 2x three-bet."""
    return solver_of(ranges, {"": open_pot, "34": four_bets(TOP_FIVE)}, **kw)


def four_bet(hole, level=2600, opponent_start=10000, our_start=10000):
    """We are the big blind: they open pot to 300, we three-bet to 1,500, they four-bet to `level`."""
    mine = our_start - 1500
    return {"hand_number": 4, "phase": "preflop", "board": [], "your_hole_cards": hole,
            "pot": level + 1500, "your_stack": mine, "opponent_stacks": [opponent_start - level],
            "to_call": level - 1500, "min_raise": min(mine, 2 * level - 1500), "max_raise": mine,
            "action_history": BLINDS + [entry(0, "raise", 300), entry(1, "raise", 1500), entry(0, "raise", level)]}


@pytest.fixture()
def player():
    out = ArenaPlayer([SHIPPED], np.random.default_rng(5))
    assert out.short_ranges is not None, "the push-fold table (results/cfr/chance/push_fold_ranges.npz) is needed"
    out.ladder = [standard(out.short_ranges)]
    out.companions = []
    return out


def decide(player, state, offtree=True, guard=False, valid=("fold", "call", "raise"), seat=1):
    player.offtree_preflop, player.price_misread = offtree, guard
    return player.decide(state, list(valid), seat)


# ---------------------------------------------------------------- when the rule must not fire

def test_no_firing_when_the_call_puts_us_all_in(player):
    # We started 2,400 deep, so 900 are left after our three-bet and their four-bet to 2,600 covers us.
    state = four_bet(["Ah", "Kd"], our_start=2400)
    out = decide(player, state)
    assert out["record"]["history"] == "345"
    assert out["record"]["adjusted"] != "priced an off-tree raise", out["record"]


def test_price_caps_call_and_removes_uncalled_excess(player):
    # The formula on its own, whatever the firing decision: 900 called of 1,100, so 200 of theirs comes back.
    state = four_bet(["Ah", "Kd"], our_start=2400)
    priced = player._offtree_price(player.ladder[0], "345", [Card("A", "h"), Card("K", "d")], state)
    assert priced["price"] == pytest.approx(900 / (4100 - 200 + 900), abs=1e-4)
    assert priced["line"] == "345"


def test_a_pseudo_all_in_where_sized_raises_exist_is_not_priced(player):
    # We are the small blind: we open pot to 300 and face a three-bet to 6,000 with 4,000 behind. At the
    # second raise the schedule has 2x pot, so the bridge reads this as all-in by its size. Our rung holds that node and folds; the rule must leave it alone.
    ranges = player.short_ranges
    player.ladder = [solver_of(ranges, {"": open_pot, "3": lambda l: [0, 0, 0, 0, 1.0, 0], "35": lambda l: [1, 0, 0]})]
    state = {"hand_number": 6, "phase": "preflop", "board": [], "your_hole_cards": ["Ah", "Kd"],
             "pot": 6300, "your_stack": 9700, "opponent_stacks": [4000], "to_call": 5700,
             "min_raise": 9700, "max_raise": 9700,
             "action_history": BLINDS + [entry(0, "raise", 300), entry(1, "raise", 6000)]}
    out = decide(player, state, seat=0)
    assert out["record"]["history"] == "35" and not out["record"]["miss"], out["record"]
    assert "offtree" not in out["record"] and out["action"] == "fold"


def test_no_firing_without_the_push_fold_table(player):
    player.short_ranges = None
    out = decide(player, four_bet(["Ah", "Kd"]))
    assert out["action"] == "fold" and "offtree" not in out["record"]


def test_without_the_table_the_guard_still_prices_the_spot(player):
    # The rule could not price it, so the spot is the guard's: priced once, by the guard.
    player.short_ranges = None
    out = decide(player, four_bet(["Kh", "Jd"]), guard=True)
    assert out["action"] == "call" and out["record"]["adjusted"] == "priced a misread all-in"
    assert player.stats.offtree_preflop_calls == 0 and player.stats.misread_prices_called == 1


def test_an_empty_range_is_not_priced_and_leaves_the_spot_to_the_guard(player):
    ranges = player.short_ranges
    player.ladder = [solver_of(ranges, {"": open_pot, "34": four_bets(())})]      # nobody four-bets
    assert player.raise_reach(player.ladder[0], "345") is None
    alone = decide(player, four_bet(["Ah", "Kd"]))
    assert alone["action"] == "fold" and "offtree" not in alone["record"]
    both = decide(player, four_bet(["Kh", "Jd"]), guard=True)
    assert both["record"]["adjusted"] == "priced a misread all-in"


def test_no_firing_when_a_read_chose_the_fold(player):
    # The strategy shoves seven-deuce; a station read withholds the bluff, which leaves a fold. The read
    # priced the real bet on purpose, so the rule must not turn it into a call, even at a price (100 into
    # 3,200, 0.03) where seven-deuce would otherwise call.
    ranges = player.short_ranges
    player.ladder = [standard(ranges, answer=ALL_IN)]

    class Station:
        posteriors = False

        def never_folds(self, *a):
            return True

        def __getattr__(self, name):
            return lambda *a, **k: False
    player.profiles = Station()
    out = decide(player, four_bet(["7h", "2d"], level=1600))
    assert out["record"]["adjusted"] == "bluff withheld", out["record"]
    assert out["action"] == "fold" and "offtree" not in out["record"]
    # The control: without the read the same spot fires.
    player.profiles = None
    player.ladder = [standard(ranges)]
    assert decide(player, four_bet(["7h", "2d"], level=1600))["record"]["adjusted"] == "priced an off-tree raise"


def test_no_firing_on_the_rule_fallback(player):
    # Our rung misses at our node and there is no companion: the rule answered, so no strategy's history did.
    player.ladder = [standard(player.short_ranges, misses=True)]
    out = decide(player, four_bet(["Ah", "Kd"]))
    record = out["record"]
    assert record["fallback"] and record["answered_history"] is None
    assert "offtree" not in record


def test_no_firing_when_the_arena_offers_no_call(player):
    out = decide(player, four_bet(["Ah", "Kd"]), valid=("fold",))
    assert out["action"] == "fold" and "offtree" not in out["record"]


def test_the_rule_fires_at_depths_the_push_fold_table_does_not_reach(player):
    # The table's equity matrix does not depend on depth, so the rule needs none of its depth rows: 100bb is
    # well beyond the table's last depth, and the rule still prices the spot.
    assert player.short_ranges.depths[-1] < 100
    assert decide(player, four_bet(["Ah", "Kd"]))["record"]["adjusted"] == "priced an off-tree raise"


def test_each_spot_is_priced_once_when_both_are_on(player):
    out = decide(player, four_bet(["Ah", "Kd"]), guard=True)
    assert out["record"]["adjusted"] == "priced an off-tree raise"
    assert player.stats.offtree_preflop_calls == 1 and player.stats.misread_prices_called == 0


def test_the_range_comes_from_the_companion_that_answered(player):
    # The primary misses at our node; the companion holds it and folds. The rule must read the bettor's range
    # from the companion's strategy (here aces only), not the primary's.
    ranges = player.short_ranges
    player.ladder = [standard(ranges, misses=True)]
    companion = solver_of(ranges, {"": open_pot, "34": four_bets(("AA",))})
    player.companions = [companion]
    out = decide(player, four_bet(["Ah", "Kd"]))
    record = out["record"]
    assert record["companion"] == "100bb(4, 2, 1)" and record["answered_history"] == "345"
    aces_only = float(ranges.weights[ranges.index["AA"]])
    assert record["offtree"]["range_share"] == pytest.approx(aces_only, abs=1e-4)
    # Ace-king against aces only (one combo left with the ace of hearts out) is far under the price.
    assert out["action"] == "fold"


# ---------------------------------------------------------------- the range and the equity

def test_the_range_on_a_limped_line_reads_the_unfacing_node(player):
    # 1245: we limp from the small blind, they raise half, we raise 2x, they shove the third raise. The bettor is the big blind: a check-or-raise node after the limp (five wide) and a
    # fold, call or all-in node facing our 2x (three wide).
    ranges = player.short_ranges
    solver = solver_of(ranges, {"1": lambda l: [0.5, 0.5, 0, 0, 0] if l != "72o" else [1.0, 0, 0, 0, 0],
                                "124": lambda l: [0, 0, 1.0] if l in ("AA", "72o") else [0, 1.0, 0]})
    reach = player.raise_reach(solver, "1245")
    assert reach[ranges.index["AA"]] == pytest.approx(0.5)
    assert reach[ranges.index["72o"]] == 0.0       # never raised the limp
    assert reach[ranges.index["KK"]] == 0.0        # raised, never shoved
    assert ArenaPlayer._unnamed_raise(solver, "1245")


def test_a_stack_capped_or_mis_sized_node_drops_the_class(player):
    ranges = player.short_ranges
    solver = solver_of(ranges, {"": open_pot,
                                "34": lambda l: [0.0, 1.0] if l == "KK" else
                                ([0, 0, 0, 1.0] if l == "QQ" else [0, 0, 1.0])})
    reach = player.raise_reach(solver, "345")
    assert reach[ranges.index["KK"]] == 0.0        # a fold/call node cannot have shoved
    assert reach[ranges.index["QQ"]] == 0.0        # a row of the wrong width is no evidence
    assert reach[ranges.index["AA"]] == 1.0


def test_card_removal_counts_combos(player):
    ranges = player.short_ranges
    left = ranges.combos_left([Card("A", "h"), Card("A", "d")])
    assert left.sum() == 50 * 49 / 2
    assert left[ranges.index["AA"]] == 1 and left[ranges.index["AKs"]] == 2 and left[ranges.index["AKo"]] == 6
    left = ranges.combos_left([Card("A", "h"), Card("K", "d")])
    assert left[ranges.index["AA"]] == 3 and left[ranges.index["KK"]] == 3
    assert left[ranges.index["AKs"]] == 2 and left[ranges.index["AKo"]] == 7


def test_equity_against_an_empty_range_is_none(player):
    ranges = player.short_ranges
    assert ranges.equity_against([Card("A", "h"), Card("K", "d")], np.zeros(169)) is None
    assert ranges.equity_against([Card("A", "h")], np.ones(169)) is None


def test_equity_against_every_hand_is_close_to_equity_against_random(player):
    import pokerbot_native as native
    ranges = player.short_ranges
    for hole in (["Ah", "Kd"], ["7h", "2d"], ["Qs", "Qc"]):
        cards = [Card(h[0], h[1]) for h in hole]
        mine = ranges.equity_against(cards, np.ones(169))
        exact = float(native.equity_vs_random([c.index for c in cards], [], 2000, 3))
        assert mine == pytest.approx(exact, abs=0.02), hole


def test_aces_against_aces_only_is_a_split(player):
    ranges = player.short_ranges
    reach = np.zeros(169)
    reach[ranges.index["AA"]] = 1.0
    assert ranges.equity_against([Card("A", "h"), Card("A", "d")], reach) == pytest.approx(0.5, abs=0.02)


# ---------------------------------------------------------------- the record on every answer path

def test_the_record_on_a_companion_miss(player):
    ranges = player.short_ranges
    player.ladder = [standard(ranges, misses=True)]
    player.companions = [standard(ranges, misses=True)]
    record = decide(player, four_bet(["Ah", "Kd"]), offtree=False)["record"]
    assert record["companion"] is None and record["fallback"]
    assert record["companion_history"] == "345"           # asked, and missed: the translation is still kept
    assert record["answered_history"] is None


def test_the_record_on_the_river_solve(monkeypatch):
    # The river re-solve answers on the primary's history whatever a companion said before it.
    import chipzen.player as module
    from types import SimpleNamespace
    player = ArenaPlayer([SHIPPED], np.random.default_rng(1), companions=[TAPER], river=True)
    monkeypatch.setattr(module, "decide_river", lambda *a, **k: SimpleNamespace(
        choice=CHECK_CALL, iterations=1, ms=1.0, hands=1, range_source="blueprint", distribution={1: 1.0}))
    state = {"hand_number": 9, "phase": "river", "board": ["Ah", "Tc", "4s", "9d", "2c"],
             "your_hole_cards": ["Ts", "9h"], "pot": 800, "your_stack": 9600, "opponent_stacks": [9500],
             "to_call": 200, "min_raise": 400, "max_raise": 9600,
             "action_history": BLINDS + [entry(0, "raise", 200), entry(1, "call", 100),
                                         entry(1, "check", 0, "flop"), entry(0, "check", 0, "flop"),
                                         entry(1, "check", 0, "turn"), entry(0, "check", 0, "turn"),
                                         entry(1, "check", 0, "river"), entry(0, "raise", 200, "river")]}
    record = player.decide(state, ["fold", "call", "raise"], 1)["record"]
    assert record["river"] and "error" not in record["river"], record["river"]
    assert record["answered_history"] == record["history"] and record["companion"] is None


def test_record_fields_are_json_safe(player):
    import json
    player.companions = [standard(player.short_ranges)]
    player.ladder = [standard(player.short_ranges, misses=True)]
    record = decide(player, four_bet(["Ah", "Kd"]))["record"]
    assert json.loads(json.dumps(record))["offtree"] == record["offtree"]


# ---------------------------------------------------------------- the audit's rebuild of old records

def test_answered_history_for_old_records():
    assert answered_history({"history": "345"}, [], 0, 0, 1) == ("345", "primary")
    assert answered_history({"history": "21/1", "companion": "collapsed:21/"}, [], 0, 0, 1) == ("21/", "collapsed")
    assert answered_history({"history": "x", "companion": "100bb{'odd': 1}"}, [], 0, 0, 1) == (None, "other")
    assert answered_history({"answered_history": None, "history": "x"}, [], 0, 0, 1) == (None, "logged")


def test_companion_schedule_parses_every_printed_form():
    assert companion_schedule("62.5bb(4, 2, 1)") == (4, 2, 1)
    assert companion_schedule("100bb(4,)") == (4,)
    assert companion_schedule("35bb1") == 1
    assert companion_schedule(None) is None and companion_schedule("river shove") is None


def test_the_rebuild_reads_the_last_action_the_same_way_under_any_draw():
    # A three-bet between the taper's 2x and all-in sizes is translated at random, but whether the four-bet
    # we face reads as all-in does not depend on that draw.
    from chipzen.bridge import replay
    history = BLINDS + [entry(0, "raise", 300), entry(1, "raise", 1100), entry(0, "raise", 1800)]
    state = {"action_history": history, "your_stack": 8900, "opponent_stacks": [8200], "phase": "preflop"}
    ends = {replay(state, 1, np.random.default_rng(seed), schedule=(4, 2)).node.history[-1] for seed in range(20)}
    assert len(ends) == 1


def test_the_rebuild_matches_the_live_companion_preflop():
    # The preflop counterpart of the branch's flop test: a primary miss answered by the taper.
    shipped = ArenaPlayer([SHIPPED], np.random.default_rng(3), companions=[TAPER])
    state = {"hand_number": 1, "phase": "preflop", "board": [], "your_hole_cards": ["Ah", "Kd"],
             "pot": 1200, "your_stack": 9700, "opponent_stacks": [9100], "to_call": 600,
             "min_raise": 1500, "max_raise": 9700,
             "action_history": BLINDS + [entry(0, "raise", 300), entry(1, "raise", 900)]}
    # We are the small blind facing a three-bet after our open: off the one-raise tree, on the taper's.
    record = dict(shipped.decide(state, ["fold", "call", "raise"], 0)["record"])
    assert record["companion"] == "100bb(4, 2)", record
    live = record.pop("answered_history")
    record.pop("companion_history")
    rebuilt, source = answered_history(record, state["action_history"], state["your_stack"],
                                       state["opponent_stacks"][0], 0)
    assert source == "companion, rebuilt" and rebuilt[-1] == live[-1] and len(rebuilt) == len(live)


# ---------------------------------------------------------------- flag off is main

def _main_player_class(tmp_path):
    try:
        source = subprocess.run(["git", "-C", ROOT, "show", "main:chipzen/player.py"], capture_output=True,
                                text=True, check=True).stdout
    except Exception:
        pytest.skip("main is not reachable from this checkout")
    path = tmp_path / "player_main.py"
    path.write_text(source)
    spec = importlib.util.spec_from_file_location("player_main_review", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["player_main_review"] = module
    spec.loader.exec_module(module)
    return module.ArenaPlayer


def _synthetic_states():
    yield four_bet(["Ah", "Kd"]), 1
    yield four_bet(["Kh", "Jd"]), 1
    yield four_bet(["7h", "2d"], level=1600), 1
    yield four_bet(["Ah", "Kd"], our_start=2400), 1
    yield four_bet(["Ah", "Kd"], opponent_start=2600), 1
    yield {"hand_number": 3, "phase": "flop", "board": ["Ah", "Tc", "4s"], "your_hole_cards": ["Ad", "Qh"],
           "pot": 1300, "your_stack": 9500, "opponent_stacks": [9200], "to_call": 300,
           "min_raise": 900, "max_raise": 9500,
           "action_history": BLINDS + [entry(0, "raise", 200), entry(1, "call", 100),
                                       entry(1, "raise", 300, "flop"), entry(0, "raise", 600, "flop")]}, 1
    yield {"hand_number": 10, "phase": "flop", "board": ["Ah", "Tc", "4s"], "your_hole_cards": ["Ts", "9h"],
           "pot": 3500, "your_stack": 8500, "opponent_stacks": [8000], "to_call": 500,
           "min_raise": 1000, "max_raise": 8500,
           "action_history": BLINDS + [entry(0, "raise", 200), entry(1, "raise", 525),
                                       entry(0, "raise", 1500), entry(1, "call", 975),
                                       entry(1, "check", 0, "flop"), entry(0, "raise", 500, "flop")]}, 1
    rng = np.random.default_rng(17)
    deck = [r + s for r in "23456789TJQKA" for s in "hdcs"]
    for n in range(40):
        hole = list(rng.choice(deck, 2, replace=False))
        open_to = int(rng.choice([200, 250, 300, 400]))
        three = int(rng.choice([600, 900, 1200, 1500]))
        four = int(rng.choice([1600, 2200, 3000, 5000]))
        yield four_bet(hole, level=max(four, three + 100)), 1
        yield {"hand_number": 20 + n, "phase": "preflop", "board": [], "your_hole_cards": hole,
               "pot": open_to + 100, "your_stack": 9900, "opponent_stacks": [10000 - open_to],
               "to_call": open_to - 100, "min_raise": 2 * open_to - 100, "max_raise": 9900,
               "action_history": BLINDS + [entry(0, "raise", open_to)]}, 1


@pytest.mark.parametrize("guard", [False, True])
def test_flag_off_decides_exactly_as_main(tmp_path, guard):
    Main = _main_player_class(tmp_path)
    states = list(_synthetic_states())
    outs = []
    for cls in (ArenaPlayer, Main):
        p = cls([SHIPPED], np.random.default_rng(23), companions=[TAPER])
        stand = cls([SHIPPED], np.random.default_rng(23))
        p.price_misread = guard
        out = []
        for state, seat in states:
            o = p.decide(state, ["fold", "call", "raise"], seat)
            out.append((o["action"], o["params"],
                        {k: v for k, v in o["record"].items()
                         if k not in ("ms", "answered_history", "companion_history", "alt_history", "offtree")}))
        # The stand-in ladder, where the rule would fire if it were on.
        stand.ladder = [standard(stand.short_ranges)]
        stand.companions = []
        stand.price_misread = guard
        for state, seat in states[:5]:
            o = stand.decide(state, ["fold", "call", "raise"], seat)
            out.append((o["action"], o["params"], o["record"]["adjusted"], o["record"]["choice"]))
        outs.append(out)
    if not guard:
        assert outs[0] == outs[1]
        return
    # With the guard on, the one intended difference is stack-cap's fix (merged 6 Oct): a bet that covers our stack
    # is a real all-in, so the guard no longer calls it a misread. Any other difference is still a failure.
    every = [s for s, _ in states] + [s for s, _ in states[:5]]
    for i, (new, old) in enumerate(zip(outs[0], outs[1])):
        if new == old:
            continue
        st = every[i]
        assert int(st["to_call"]) >= int(st["your_stack"]), (i, new, old)
        assert "priced a misread all-in" in old and "priced a misread all-in" not in new, (i, new, old)
