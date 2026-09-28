"""
The river oracle is only an upper bound if it is the script's policy exactly.
Two ways it could quietly not be: `action_probabilities` drifting from
`Archetype.decide`, and the history replay reconstructing a different pot,
price or raise count from the one the script saw. Each is checked against the
real thing, not a copy of it.
"""
import importlib.util
import os

import numpy as np
import pytest

from chipzen.archetypes import ARCHETYPES, PARAMS, Archetype, action_probabilities
from cfr.river_oracle import decisions

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _duel():
    spec = importlib.util.spec_from_file_location("chipzen_duel", os.path.join(ROOT, "scripts", "chipzen_duel.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _state(phase, to_call, pot, raises, stack=5000):
    history = [{"seat": 0, "action": "post_small_blind", "amount": 50, "phase": "preflop"},
               {"seat": 1, "action": "post_big_blind", "amount": 100, "phase": "preflop"}]
    history += [{"seat": i % 2, "action": "raise", "amount": 300 * (i + 1), "phase": phase} for i in range(raises)]
    board = [] if phase == "preflop" else ["2c", "7d", "Js"][: {"flop": 3, "turn": 3, "river": 3}[phase]] + \
        (["Qh"] if phase in ("turn", "river") else []) + (["3s"] if phase == "river" else [])
    return {"phase": phase, "board": board, "your_hole_cards": ["Ah", "Kd"], "pot": pot, "to_call": to_call,
            "your_stack": stack, "min_raise": to_call + 200, "max_raise": stack, "action_history": history}


# (phase, to_call, pot, raises, can_raise): every branch of `decide`.
SPOTS = [("preflop", 50, 150, 0, True),      # the small blind, unopened
         ("preflop", 0, 200, 0, True),       # the big blind facing a limp
         ("preflop", 0, 200, 0, False),
         ("preflop", 200, 500, 1, True),     # facing an open
         ("preflop", 600, 1400, 2, True),    # facing a three-bet
         ("preflop", 600, 1400, 2, False),
         ("flop", 300, 900, 1, True),        # facing a bet
         ("flop", 300, 900, 1, False),
         ("turn", 0, 900, 0, True),          # checked to
         ("river", 0, 900, 0, False)]


@pytest.mark.parametrize("kind", ARCHETYPES)
def test_probabilities_match_decide(kind):
    """Sampled `decide` frequencies land on `action_probabilities`, spot by spot."""
    p = PARAMS[kind]
    rng = np.random.default_rng(11)
    bot = Archetype(kind, rng)
    draws = 3000
    for phase, to_call, pot, raises, can_raise in SPOTS:
        valid = (["fold", "call"] if to_call > 0 else ["check"]) + (["raise"] if can_raise else [])
        state = _state(phase, to_call, pot, raises)
        # Equities either side of every threshold the shape has.
        cuts = sorted({v for k, v in p.items() if k.endswith("_eq")} |
                      {to_call / (pot + to_call) + p["fold_margin"] if to_call else 0.5})
        for e in sorted({min(max(c + d, 0.01), 0.99) for c in cuts for d in (-0.02, 0.02)}):
            bot._equity = lambda _s, e=e: e
            counts = np.zeros(3)
            for _ in range(draws):
                action = bot.decide(state, valid, 0)["action"]
                counts[{"fold": 0, "check": 1, "call": 1, "raise": 2}[action]] += 1
            expected = action_probabilities(p, np.array([e]), facing=to_call > 0,
                                            price=to_call / (pot + to_call) if to_call else 0.0,
                                            preflop=phase == "preflop", can_raise=can_raise, raises=raises)[0]
            # Four standard errors of a proportion at 3,000 draws is under 0.037.
            assert np.allclose(counts / draws, expected, atol=0.037), (kind, phase, raises, can_raise, e, counts / draws, expected)
            assert np.isclose(expected.sum(), 1.0) and (expected >= -1e-12).all()


def test_replay_sees_what_the_script_saw():
    """Through the duel's own dealer: the replayed context of every opponent decision is the one it acted on."""
    duel = _duel()
    rng = np.random.default_rng(5)
    for hand in range(200):
        seen = {0: [], 1: []}
        players = []
        for seat, kind in enumerate(("maniac", "station")):
            bot = Archetype(kind, np.random.default_rng(hand * 2 + seat))

            def decide(state, valid, s, bot=bot, seat=seat):
                raises = sum(1 for a in state["action_history"]
                             if a.get("phase") == state["phase"] and a.get("action") == "raise")
                action = Archetype.decide(bot, state, valid, s)
                seen[seat].append({"state": state, "facing": state["to_call"] > 0, "raises": raises,
                                   "price": state["to_call"] / (state["pot"] + state["to_call"]) if state["to_call"] else 0.0,
                                   "can_raise": "raise" in valid})
                return action
            bot.decide = decide
            players.append(bot)
        deck = list(rng.permutation(52))
        dealer = duel.Dealer(players, deck, [int(rng.integers(600, 6000)), int(rng.integers(600, 6000))], 50, 100, hand, ("b", "a"))
        dealer.play()
        if not seen[0]:
            continue
        last = seen[0][-1]["state"]
        replayed = decisions(last, opponent_seat=1)
        truth = [d for d in seen[1] if len(d["state"]["action_history"]) < len(last["action_history"])]
        assert len(replayed) == len(truth), (hand, len(replayed), len(truth))
        for r, t in zip(replayed, truth):
            assert r["facing"] == t["facing"] and r["raises"] == t["raises"] and r["can_raise"] == t["can_raise"], (hand, r, t)
            assert r["price"] == pytest.approx(t["price"]), (hand, r, t)
