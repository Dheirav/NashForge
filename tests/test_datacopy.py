"""The data-driven copy: its decisions read from scout hands, the table's back-off, and play that stays legal and
follows the table."""
import json
import os
import sys

import numpy as np
import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from chipzen.datacopy import (ACTIONS, DataCopy, action_distribution, band, fit_table, scout_decisions,  # noqa: E402
                              size_bin, size_distribution)


def act(seat, action, amount, phase="preflop"):
    return {"seat": seat, "action": action, "amount": amount, "phase": phase}


META = {"participants": [{"name": "hero", "seat": 0}, {"name": "villain", "seat": 1}]}
# Blinds 50/100; hero (seat 0) opens to 300, villain re-raises to 600, hero calls; flop: villain bets 600, hero folds.
HAND = {"hole_cards": {"0": ["Ah", "Kd"], "1": ["7c", "2d"]}, "board": "Qs9h3c",
        "actions": [act(0, "post_small_blind", 50), act(1, "post_big_blind", 100), act(0, "raise", 250),
                    act(1, "raise", 500), act(0, "call", 300), act(1, "raise", 600, "flop"), act(0, "fold", 0, "flop")]}


def test_decisions_are_read_with_their_situation_and_size():
    d = scout_decisions(META, [HAND])
    hero, villain = d["hero"], d["villain"]
    assert [x["action"] for x in hero] == ["raise", "passive", "fold"]
    assert [x["action"] for x in villain] == ["raise", "raise"]
    assert villain[0]["facing"] and villain[0]["raises"] == 1          # their re-raise faces our open
    assert hero[2]["street"] == 1 and hero[2]["facing"] and hero[2]["board"] == ["Qs", "9h", "3c"]
    # the re-raise: 600 against our 300, so 300 over a pot of 400 + 200 to call: half the pot, the second bin
    assert villain[0]["size"] == size_bin(300 / 600) == 1


def table_from(bot, field, eq=0.5):
    return json.loads(json.dumps(fit_table(bot, field, lambda d: eq)))       # through JSON, as a file would be


def d(street, facing, raises, action, size=None):
    return {"street": street, "facing": facing, "raises": raises, "cards": ["Ah", "Kd"], "board": [], "action": action,
            "size": size}


def test_the_table_backs_off_from_band_to_situation_to_field():
    bot = [d(0, True, 1, "raise", 0)] * 30                            # this bot always re-raises a raise, small
    field = [d(0, True, 1, "fold")] * 300 + [d(1, False, 0, "passive")] * 300
    t = table_from(bot, field, eq=0.5)
    seen = action_distribution(t, 0, True, 1, 0.5)                  # its own band: mostly raise
    assert seen[ACTIONS.index("raise")] > 0.8
    other_band = action_distribution(t, 0, True, 1, 0.95)           # unseen band: its situation's counts
    assert other_band[ACTIONS.index("raise")] > 0.8
    unseen = action_distribution(t, 1, False, 0, 0.5)               # unseen situation: the field's
    assert unseen[ACTIONS.index("passive")] > 0.9
    sizes = size_distribution(t, 0, True)
    assert int(np.argmax(sizes)) == 0


class FixedEquity(DataCopy):
    def _equity(self, state):
        return 0.5


def state(to_call, board=(), history=()):
    return {"your_hole_cards": ["Ah", "Kd"], "board": list(board), "to_call": to_call, "pot": 400, "min_raise": 600,
            "max_raise": 9000, "phase": "preflop" if not board else "flop", "action_history": list(history)}


def test_it_only_plays_what_the_arena_offers_and_follows_its_table():
    bot = [d(0, True, 1, "fold")] * 20 + [d(0, True, 1, "raise", 0)] * 20
    t = table_from(bot, [d(0, True, 1, "passive")] * 10)
    copy = FixedEquity(t, np.random.default_rng(0))
    facing = state(200, history=[{"phase": "preflop", "action": "raise"}])
    picks = [copy.decide(facing, ["fold", "call", "raise"], 1)["action"] for _ in range(2000)]
    share = {a: picks.count(a) / len(picks) for a in ("fold", "call", "raise")}
    p = action_distribution(t, 0, True, 1, 0.5, price=200 / 600)       # the state's own price: 200 into 400
    assert abs(share["fold"] - p[0]) < 0.04 and abs(share["raise"] - p[2]) < 0.04
    no_raise = [copy.decide(facing, ["fold", "call"], 1)["action"] for _ in range(300)]
    assert "raise" not in no_raise
    # Nothing to call: even a bot recorded folding there checks, though the arena lists fold.
    folder = FixedEquity(table_from([d(0, False, 0, "fold")] * 50, [d(0, False, 0, "fold")] * 50), np.random.default_rng(1))
    assert all(folder.decide(state(0), ["fold", "check", "raise"], 1)["action"] != "fold" for _ in range(300))
    raised = [copy.decide(facing, ["fold", "call", "raise"], 1) for _ in range(300)]
    amounts = [r["params"]["amount"] for r in raised if r["action"] == "raise"]
    assert amounts and all(600 <= a <= 9000 for a in amounts)


def test_the_duel_builds_it_from_a_table_file(tmp_path):
    from chipzen_duel import build
    path = tmp_path / "villain.json"
    path.write_text(json.dumps(table_from([d(0, True, 1, "raise", 0)] * 5, [d(0, True, 1, "fold")] * 5)))
    player = build(f"datacopy:{path}", "", "villain", np.random.default_rng(0), None)
    assert isinstance(player, DataCopy) and player.label == "villain" and vars(player.stats)["decisions"] == 0


def test_the_price_separates_a_small_bet_from_a_big_one():
    # A bot that calls a bet at a price under 0.2 and folds one over 0.4: without the price these were one situation.
    small = [dict(d(1, True, 0, "passive"), price=0.15)] * 40
    big = [dict(d(1, True, 0, "fold"), price=0.45)] * 40
    t = table_from(small + big, [d(1, True, 0, "passive")] * 40)
    cheap, dear = action_distribution(t, 1, True, 0, 0.5, price=0.15), action_distribution(t, 1, True, 0, 0.5, price=0.45)
    assert cheap[ACTIONS.index("passive")] > 0.85 and dear[ACTIONS.index("fold")] > 0.85
