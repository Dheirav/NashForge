"""
`--capped-price` (ArenaPlayer.capped_price, 5 October): the fallback rule and "called for pot odds" price the chips
we can call, with the bettor's uncalled excess out of the pot.

The three spots are the 5 October review's (tests/test_review_shortstack_postflop.py on the shelved
shortstack-postflop branch), where they were strict xfails against main. Each is asserted twice here: with the flag
the fixed answer, without it main's, because the flag changes default play and stays off until it is audited and
burst. A spot that changed without the flag would be a change to what plays tomorrow.
"""
import os

import numpy as np
import pytest

from abstraction.betting import CHECK_CALL, FOLD
from chipzen.player import ArenaPlayer, capped_call, fallback_choice

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SHIPPED = os.path.join(ROOT, "results", "cfr", "nolimit_strategy.pkl")


def entry(seat, action, amount, phase="preflop"):
    return {"seat": seat, "action": action, "amount": amount, "phase": phase, "is_timeout": False}


def bet_raised(hole, board, ours0, theirs0, raise_to, our_bet, their_raise, sb=50, bb=100):
    """We (seat 1, the big blind) called a raise, bet the flop and were raised: off the one-raise tree."""
    mine, theirs = ours0 - raise_to - our_bet, theirs0 - raise_to - their_raise
    to_call = their_raise - our_bet
    can_raise = mine > to_call and theirs > 0
    state = {"hand_number": 5, "phase": "flop", "board": board, "your_hole_cards": hole,
             "pot": 2 * raise_to + our_bet + their_raise, "your_stack": mine, "opponent_stacks": [theirs],
             "to_call": to_call, "min_raise": 0, "max_raise": mine if can_raise else 0,
             "action_history": [entry(0, "post_small_blind", sb), entry(1, "post_big_blind", bb),
                                entry(0, "raise", raise_to), entry(1, "call", raise_to - bb),
                                entry(1, "raise", our_bet, "flop"), entry(0, "raise", their_raise, "flop")]}
    return state, ["fold", "call"] + (["raise"] if can_raise else [])


def eighth():
    """8bb at 250/500: 1,000 behind, they raised to 16,500 with 12,000 more behind. Second pair."""
    return bet_raised(["Kc", "Qd"], ["5d", "As", "Qs"], 4000, 30000, 1500, 1500, 16500, 250, 500)


def fifty_behind():
    """5.5bb at 500/1,000: 50 behind, they shoved. The call is 50 into 35,450 less 24,500 uncalled."""
    return bet_raised(["6c", "9s"], ["Qd", "9c", "4h"], 5500, 30000, 2500, 2950, 27500, 500, 1000)


@pytest.fixture(scope="module")
def player():
    return ArenaPlayer([SHIPPED], np.random.default_rng(3))


@pytest.fixture
def capped(player):
    player.capped_price = True
    yield player
    player.capped_price = False


def test_the_flag_is_off_by_default(player):
    assert player.capped_price is False


def test_capped_call_takes_the_uncalled_excess_out_of_the_pot():
    assert capped_call(21000, 15000, 1000) == (7000, 1000)       # 1,000 / 8,000 after the call: an eighth
    assert capped_call(35450, 24550, 50) == (10950, 50)
    assert capped_call(3000, 1000, 1000) == (3000, 1000)         # the call is exactly our stack: nothing comes back
    assert capped_call(3000, 1000, 5000) == (3000, 1000)         # we cover the bet
    assert capped_call(3000, 1000, 0) == (3000, 1000)            # our stack not known: the arena's numbers stand


def test_the_rule_folds_to_a_bet_it_could_call_for_a_fraction(player, capped):
    state, valid = eighth()
    called = min(state["to_call"], state["your_stack"])
    assert called / (state["pot"] - (state["to_call"] - called) + called) == pytest.approx(0.125)
    out = capped.decide(state, valid, 1)
    assert out["record"]["fallback"]
    assert out["action"] == "call", out["record"]


def test_without_the_flag_the_rule_still_folds_the_eighth_as_main_does(player):
    state, valid = eighth()
    out = player.decide(state, valid, 1)
    assert out["record"]["fallback"]
    assert out["action"] == "fold", out["record"]


def test_fallback_choice_itself_folds_the_second_class_at_a_real_eighth():
    mask = np.array([1, 1, 0, 0, 0, 1], dtype=float)
    assert fallback_choice(4, 5, mask, 21000, 15000, stack=1000) == CHECK_CALL
    # Main's call, which the Slumbot player and the flag-off arena player still make: 15,000 >= 21,000 - 15,000.
    assert fallback_choice(4, 5, mask, 21000, 15000) == FOLD
    # A stack that covers the bet prices it exactly as before.
    assert fallback_choice(4, 5, mask, 21000, 15000, stack=20000) == FOLD


def test_pot_odds_rule_folds_fifty_chips_into_eleven_thousand(player, capped):
    state, valid = fifty_behind()
    assert state["your_stack"] == 50 and state["opponent_stacks"] == [0]
    out = capped.decide(state, valid, 1)
    assert out["record"]["fallback"]
    assert out["action"] == "call", out["record"]


def test_without_the_flag_fifty_chips_into_eleven_thousand_are_folded_as_on_main(player):
    state, valid = fifty_behind()
    out = player.decide(state, valid, 1)
    assert out["record"]["fallback"]
    assert out["action"] == "fold", out["record"]


def test_pot_odds_rule_fires_on_a_call_that_puts_us_all_in_while_they_keep_chips(player, capped, monkeypatch):
    # Our call of the last 50 ends the betting as their all-in would. The rule is held to its own condition by
    # forcing the fallback to fold, so only "called for pot odds" can turn it into a call.
    monkeypatch.setattr(ArenaPlayer, "_fallback", lambda self, *a: FOLD)
    state, valid = bet_raised(["6c", "9s"], ["Qd", "9c", "4h"], 5500, 40000, 2500, 2950, 27500, 500, 1000)
    assert state["your_stack"] == 50 and state["opponent_stacks"][0] > 0
    out = capped.decide(state, valid, 1)
    assert out["action"] == "call" and out["record"]["adjusted"] == "called for pot odds", out["record"]
    capped.capped_price = False
    out = capped.decide(state, valid, 1)
    assert out["action"] == "fold" and out["record"]["adjusted"] is None, out["record"]


def test_the_capped_pot_odds_rule_still_folds_a_real_price(player, capped, monkeypatch):
    # 1,000 behind against the 16,500 raise: an eighth is a call for a hand, but not at any two cards' odds.
    monkeypatch.setattr(ArenaPlayer, "_fallback", lambda self, *a: FOLD)
    state, valid = eighth()
    out = capped.decide(state, valid, 1)
    assert out["action"] == "fold" and out["record"]["adjusted"] is None, out["record"]


def test_the_misread_test_asks_whether_the_bettor_kept_chips_beyond_our_call():
    misread = ArenaPlayer._misread
    assert misread(None, "21/25", 9200, 300, 9500)          # a min-raise read as all-in, both deep
    assert not misread(None, "21/25", 6700, 2700, 500)      # their bet covers our stack: a real all-in
    assert not misread(None, "21/25", 6700, 500, 500)       # exactly our stack is all of it too
    assert misread(None, "21/25", 6700)                     # our stack not known: their chips decide, as before
    assert misread("collapsed:21/1", "21/1", 6700, 2700, 500)   # a re-read prices a pot that is not the arena's


# The second half of --capped-price (5 Oct): the short-stack table and the reads that weigh a price. Each place is
# shown changing with the flag and staying on main's answer without it, and the reads on their bet's size are shown
# not to move at all.

from abstraction.betting import RAISE_POT  # noqa: E402


def blinds():
    return [entry(0, "post_small_blind", 50), entry(1, "post_big_blind", 100)]


class Reads:
    """A profile that holds only the reads a test names; every other read is off."""
    posteriors = False

    def __init__(self, **on):
        self.on = on

    def __getattr__(self, name):
        value = self.on.get(name, None if name.endswith("_floor") else False)
        return lambda *args, **kwargs: value


@pytest.fixture
def forced(player, monkeypatch):
    """The strategy answers with one action, so a read is tested on its own condition and not the rung's mix."""
    def force(action):
        for solver in player.ladder + player.companions:
            monkeypatch.setattr(solver, "agent", lambda *args: action)
    yield force
    player.profiles, player.opponent, player.aggro_reads, player.reraise_defence = None, None, False, False
    player.capped_price = False


def reshove_over_us(hole, ours=800, raise_to=2000, theirs=20000):
    """8bb: we open to 300 of our 800, they re-shove covering us. Capped, the call is our 500 into 1,100."""
    mine, left = ours - 300, theirs - raise_to
    return {"hand_number": 12, "phase": "preflop", "board": [], "your_hole_cards": hole,
            "pot": 300 + raise_to, "your_stack": mine, "opponent_stacks": [left], "to_call": raise_to - 300,
            "min_raise": 0, "max_raise": 0,
            "action_history": blinds() + [entry(0, "raise", 300), entry(1, "raise", raise_to)]}


def test_the_short_stack_table_prices_the_call_we_can_make(player):
    # Q6o has 0.362 against the 8bb re-shoving range. At the arena's full bet the price is 1,700 into 4,000
    # (0.425) and the table folds it; capped it is 500 into 1,600 (0.3125), the all-in the table was solved for.
    state = reshove_over_us(["Qh", "6d"])
    off = player.decide(state, ["fold", "call"], 0)
    assert off["record"]["adjusted"] == "short-stack solution" and off["action"] == "fold", off["record"]
    player.capped_price = True
    try:
        on = player.decide(state, ["fold", "call"], 0)
    finally:
        player.capped_price = False
    assert on["record"]["adjusted"] == "short-stack solution" and on["action"] == "call", on["record"]


@pytest.mark.parametrize("mine, to_call, theirs, expect", [
    (500, 500, 9000, (1100, 500)),        # our stack exactly the bet: nothing comes back, the price is main's
    (499, 500, 9000, (1100, 499)),        # one chip short: one chip of theirs comes back
    (500, 1700, 0, (1100, 500)),          # they are all in for more than we have: the excess still comes back
    (500, 1700, 18000, (1100, 500)),      # they keep chips and bet beyond our stack
])
def test_the_table_is_asked_at_the_capped_price_only_with_the_flag(player, monkeypatch, mine, to_call, theirs, expect):
    asked = []
    monkeypatch.setattr(player.short_ranges, "calls",
                        lambda hole, depth, call, pot, reraise: asked.append((pot, call)) or True)
    state = {"pot": 1100 + (to_call - mine), "to_call": to_call, "your_stack": mine, "opponent_stacks": [theirs],
             "action_history": blinds() + [entry(0, "raise", 300)]}
    mask = np.array([1, 1, 0, 0, 0, 0], dtype=bool)
    player._short_stack_answer([], [], 8.0, mask, state, 0)
    player.capped_price = True
    try:
        player._short_stack_answer([], [], 8.0, mask, state, 0)
    finally:
        player.capped_price = False
    assert asked == [(state["pot"], to_call), expect]


def reraised_open(ours, raise_to=6000):
    """We open to 300 and they re-raise to 6,000, covering us."""
    mine = ours - 300
    return {"hand_number": 30, "phase": "preflop", "board": [], "your_hole_cards": ["Qh", "8d"],
            "pot": 300 + raise_to, "your_stack": mine, "opponent_stacks": [30000 - raise_to],
            "to_call": raise_to - 300, "min_raise": 0, "max_raise": 0,
            "action_history": blinds() + [entry(0, "raise", 300), entry(1, "raise", raise_to)]}


def test_their_re_raise_is_value_prices_the_call_we_can_make(player, forced):
    # 300 behind against a re-raise to 6,000: 5,700 into 12,000 (0.475) at the full bet, a fold beyond 0.30, and
    # 300 into 1,200 (0.25) capped, a call. The read fires only on a raise, which the arena does not offer once
    # the bet covers our stack, so the strategy is forced to want one; in play this pricing cannot be reached.
    forced(RAISE_POT)
    player.profiles, player.opponent = Reads(never_three_bets=True), "villain"
    state = reraised_open(600)
    off = player.decide(state, ["fold", "call"], 0)
    assert off["record"]["adjusted"] == "their re-raise is value" and off["action"] == "fold", off["record"]
    player.capped_price = True
    on = player.decide(state, ["fold", "call"], 0)
    assert on["record"]["adjusted"] == "their re-raise is value" and on["action"] == "call", on["record"]


def test_re_raise_defended_weighs_its_range_against_the_capped_price(player, forced):
    # Q8o has 0.399 against the top 40 percent. 700 behind: 2,700 into 6,000 (0.45) needs 0.48 and folds, while
    # the call we can make, 700 into 2,000 (0.35), needs 0.38 and calls.
    forced(FOLD)
    player.profiles, player.opponent, player.reraise_defence = Reads(reraise_floor=0.4), "villain", True
    state = reraised_open(1000, 3000)
    off = player.decide(state, ["fold", "call"], 0)
    assert off["action"] == "fold" and off["record"]["adjusted"] is None, off["record"]
    player.capped_price = True
    on = player.decide(state, ["fold", "call"], 0)
    assert on["action"] == "call" and on["record"]["adjusted"] == "re-raise defended", on["record"]


def river_over_us(ours=3000, bet=4000, hole=("Qh", "Jd")):
    """30bb effective: three streets called down to our last 600, then a river bet of 4,000 into 4,800."""
    history = blinds() + [entry(0, "raise", 300), entry(1, "call", 200),
                          entry(1, "raise", 1000, "flop"), entry(0, "call", 1000, "flop"),
                          entry(1, "raise", 1100, "turn"), entry(0, "call", 1100, "turn"),
                          entry(1, "raise", bet, "river")]
    return {"hand_number": 40, "phase": "river", "board": ["Qd", "9c", "4h", "2s", "7d"],
            "your_hole_cards": list(hole), "pot": 4800 + bet, "your_stack": ours - 2400,
            "opponent_stacks": [20000 - 2400 - bet], "to_call": bet, "min_raise": 0, "max_raise": 0,
            "action_history": history}


def test_river_bluff_caught_breaks_even_on_the_capped_price(player, forced, monkeypatch):
    # A bluff share of 0.2 against 4,000 into 8,800 needs 0.3125 at the full bet and folds; the call we can make,
    # 600 into 5,400, needs a tenth and calls.
    import pokerbot_native
    monkeypatch.setattr(pokerbot_native, "equity_vs_random", lambda *args: 0.6)
    forced(FOLD)
    player.profiles, player.opponent, player.aggro_reads = Reads(river_bluff_floor=0.2), "villain", True
    state = river_over_us()
    off = player.decide(state, ["fold", "call"], 0)
    assert off["record"]["effective_bb"] >= ArenaPlayer.SHOVE_RULE_MIN_BB, off["record"]
    assert off["action"] == "fold" and off["record"]["adjusted"] is None, off["record"]
    player.capped_price = True
    on = player.decide(state, ["fold", "call"], 0)
    assert on["action"] == "call" and on["record"]["adjusted"] == "river bluff caught", on["record"]


def test_river_bluff_caught_is_unchanged_when_our_stack_is_exactly_the_bet(player, forced, monkeypatch):
    import pokerbot_native
    monkeypatch.setattr(pokerbot_native, "equity_vs_random", lambda *args: 0.6)
    forced(FOLD)
    player.profiles, player.opponent, player.aggro_reads = Reads(river_bluff_floor=0.2), "villain", True
    state = river_over_us(ours=6400)        # 4,000 behind against the 4,000 bet: nothing comes back
    answers = []
    for flag in (False, True):
        player.capped_price = flag
        answers.append(player.decide(state, ["fold", "call"], 0)["action"])
    assert answers == ["fold", "fold"]


@pytest.mark.parametrize("read, choice, expect", [
    (dict(big_bets_are_value=True), CHECK_CALL, "big bet believed"),
    (dict(never_calls=True), CHECK_CALL, "shove call declined"),
])
def test_reads_on_their_bet_size_keep_the_full_bet(player, forced, read, choice, expect):
    # A river bet of 5,000 into 4,800 is a pot-sized bet from them, though capped it is a call of 600 into 5,400.
    # The read is about what they hold, which their bet says, so the flag must not change it.
    forced(choice)
    player.profiles, player.opponent = Reads(**read), "villain"
    state = river_over_us(bet=5000, hole=("5h", "3c"))     # nothing: below the classes either read lets through
    for flag in (False, True):
        player.capped_price = flag
        out = player.decide(state, ["fold", "call"], 0)
        assert out["action"] == "fold" and out["record"]["adjusted"] == expect, (flag, out["record"])


def test_a_small_bet_stays_small_and_a_capped_big_one_is_not_made_small(player, forced):
    # "small bet called" calls a middling hand against a bet of 0.6 of the pot or less. Capped, the 4,000 bet is a
    # call of 600 into 4,800, an eighth, but it was not a small bet, and the read stays silent with the flag on.
    forced(FOLD)
    player.profiles, player.opponent = Reads(big_bets_are_value=True), "villain"
    state = river_over_us()
    for flag in (False, True):
        player.capped_price = flag
        out = player.decide(state, ["fold", "call"], 0)
        assert out["record"]["adjusted"] != "small bet called", (flag, out["record"])
