"""
The bridge between Slumbot's hand and this project's solver.

No network. `docs/EXTERNAL_BENCHMARK.md` says a translation bug and a weak
strategy are indistinguishable from the result, so the arithmetic is pinned here
where it can fail loudly instead of quietly costing chips.

The cases below are the ways this specific bridge can be wrong: reading a bet
level as an increment, sizing a raise off the pot before the call rather than
after, losing the blinds that are committed before the betting string starts, and
letting a shove be described as a large raise.
"""
import numpy as np
import pytest

from slumbot.api import BIG_BLIND, SMALL_BLIND, STARTING_STACK, HandState
from slumbot.bridge import (Node, TranslationError, legal_mask, parse_card,
                            parse_cards, replay, to_slumbot)

RNG = lambda: np.random.default_rng(0)          # noqa: E731


def state(action, client_pos=0):
    return HandState(token="t", action=action, old_action="",
                     client_pos=client_pos, hole_cards=["Ah", "Kd"], board=[])


# --- cards -----------------------------------------------------------------

def test_cards_convert_to_the_engine_s_own_type():
    card = parse_card("Th")
    assert (card.rank, card.suit) == ("T", "h")
    assert [str(c) for c in parse_cards(["As", "2d", "Tc"])] == ["As", "2d", "Tc"]


def test_an_unreadable_card_raises_rather_than_guessing():
    with pytest.raises(TranslationError):
        parse_card("10h")           # Slumbot writes ten as T; this is not ours


# --- the blinds are committed before the string starts ----------------------

def test_the_pot_starts_at_the_blinds():
    """
    The betting string does not contain the blinds, and forgetting them makes
    every preflop pot too small -- which makes every pot-fraction bet read as
    larger than it was, and translates bets upward for the whole hand.
    """
    node = replay(state(""), RNG())
    assert node.pot == SMALL_BLIND + BIG_BLIND
    assert sorted(node.committed) == [SMALL_BLIND, BIG_BLIND]


def test_the_client_owes_the_difference_not_the_level():
    """
    Facing `b200` as the big blind, 100 is already in, so 100 is owed.

    Reading the level as the amount owed overpays on every preflop call. Chip
    accounting still balances -- the server takes what it is sent -- so only the
    result would move.
    """
    node = replay(state("b200"), RNG())
    assert node.to_call == BIG_BLIND        # 200 owed minus 100 already posted


# --- bet levels are cumulative ---------------------------------------------

def test_a_reraise_costs_the_difference_between_levels():
    node = replay(state("b200b600"), RNG())
    # the bot bet to 200, the client raised to 600; the bot owes 400 more
    assert node.to_call == 400


def test_pot_tracks_every_increment():
    """b200 then a call: 200 from each, on top of nothing else preflop."""
    node = replay(state("b200c"), RNG())
    assert node.pot == 400
    assert node.to_call == 0


# --- streets ---------------------------------------------------------------

def test_a_new_street_clears_what_is_committed_but_not_the_pot():
    node = replay(state("b200c/"), RNG())
    assert node.pot == 400
    assert node.committed == [0, 0]
    assert node.to_call == 0
    assert node.history.endswith("/")


def test_history_carries_one_symbol_per_action_and_a_slash_per_street():
    node = replay(state("b200c/kk/kb400c/"), RNG())
    assert node.history.count("/") == 3
    assert all(ch.isdigit() or ch == "/" for ch in node.history)


# --- who is acting, which the pilot found wrong on half its hands -----------

def test_the_button_acts_first_preflop_and_the_button_depends_on_the_seat():
    """
    At client_pos 1 the client posts the small blind and opens; at 0 the bot does.

    Measured against the live server: folding immediately loses 100 at
    client_pos 0 and 50 at client_pos 1, so the client is the big blind in the
    first case and the button in the second. Every test here used client_pos 0
    until a 300-hand pilot showed the other half of the hands attributing every
    action to the wrong player -- with no protocol error raised, because the
    actions stayed legal. Only the numbers were wrong.
    """
    # the client is the button and raises to 550 from the small blind
    mine = replay(state("b550", client_pos=1), RNG())
    assert mine.committed[0] == 550

    # the same string at the other seat is the bot's raise
    theirs = replay(state("b550", client_pos=0), RNG())
    assert theirs.committed[1] == 550


def test_the_big_blind_leads_after_the_flop():
    """
    Heads-up the order reverses exactly once: button first preflop, big blind
    first on every street after it. Alternating straight through the streets
    hands the flop lead to the wrong player.
    """
    # client_pos 1: client is the button, so the bot leads the flop
    node = replay(state("cc/b300", client_pos=1), RNG())
    assert node.committed[1] == 300

    # client_pos 0: client is the big blind, so the client leads the flop
    node = replay(state("cc/b300", client_pos=0), RNG())
    assert node.committed[0] == 300


@pytest.mark.parametrize("client_pos", [0, 1])
def test_the_priced_decision_is_always_the_client_s(client_pos):
    """
    `committed` and `prior` are built client-first, so the actor being priced is
    index 0 whatever the seat. Indexing by `client_pos` read the bot's chips.
    """
    assert replay(state("b200c/", client_pos=client_pos), RNG()).to_act == 0


@pytest.mark.parametrize("client_pos", [0, 1])
def test_the_blinds_match_what_the_server_charges(client_pos):
    """An immediate fold costs 100 at seat 0 and 50 at seat 1; the pot holds both."""
    node = replay(state("", client_pos=client_pos), RNG())
    expected = BIG_BLIND if client_pos == 0 else SMALL_BLIND
    assert node.committed[0] == expected
    assert node.pot == SMALL_BLIND + BIG_BLIND


# --- what a bet is understood as -------------------------------------------

def test_a_shove_is_the_all_in_action_not_a_large_raise():
    """
    The abstraction has a slot for all-in, and it is not "two times pot".

    Describing a 200bb shove as a large raise asks the strategy a question about
    a bet it could still fold behind, which is a different decision entirely.
    """
    node = replay(state(f"b{STARTING_STACK}"), RNG())
    assert node.history[-1] == "5"


def test_a_bet_beyond_the_abstraction_is_counted():
    """A bet this project cannot describe should be a number, not a shrug."""
    node = replay(state("b200c/b10000"), RNG())
    assert node.misses >= 1


# --- what goes back out ----------------------------------------------------

def test_passive_actions_pick_the_legal_word():
    facing = Node(pot=400, committed=[100, 300], to_act=0)
    assert to_slumbot(1, facing) == "c"
    quiet = Node(pot=400, committed=[0, 0], to_act=0)
    assert to_slumbot(1, quiet) == "k"
    assert to_slumbot(0, facing) == "f"


def test_a_raise_is_sized_off_the_pot_after_the_call():
    """
    A pot-sized raise, committed 100 against 200 with 400 in the middle, goes to 700.

    Calling costs 100, which brings this player to 200 and the pot to 500; the
    raise is then that 500 on top, for a level of 700. Sizing the raise off the
    400 that was there *before* the call would send 600 and under-bet by a fifth
    of every raise -- which reads as a strategy playing timidly rather than as a
    bridge doing arithmetic in the wrong order.
    """
    node = Node(pot=400, committed=[100, 200], to_act=0)
    assert node.to_call == 100
    assert to_slumbot(3, node) == "b700"


def test_a_half_pot_raise_uses_the_same_order():
    """Same node, half pot: call to 200, then 250 more."""
    node = Node(pot=400, committed=[100, 200], to_act=0)
    assert to_slumbot(2, node) == "b450"


def test_a_raise_never_exceeds_the_stack():
    node = Node(pot=STARTING_STACK, committed=[0, 0], to_act=0)
    assert to_slumbot(4, node) == f"b{STARTING_STACK}"


def test_all_in_goes_out_as_the_stack():
    assert to_slumbot(5, Node(pot=400, committed=[0, 0], to_act=0)) == f"b{STARTING_STACK}"


# --- the mask mirrors the panel's -------------------------------------------

def test_folding_is_removed_when_there_is_nothing_to_call():
    mask = legal_mask(Node(pot=400, committed=[0, 0]))
    assert mask[0] == 0.0
    assert mask[1] == 1.0


def test_raises_stop_at_the_cap():
    mask = legal_mask(Node(pot=400, committed=[0, 100], raises_this_street=1))
    assert list(mask[2:]) == [0.0, 0.0, 0.0, 0.0]
    assert mask[1] == 1.0


def test_the_actor_is_never_stranded():
    """Every narrowing removes options, so something must always remain."""
    mask = legal_mask(Node(pot=400, committed=[0, 0], raises_this_street=9))
    assert mask.any()
    assert mask[1] == 1.0


# --- the whole walk --------------------------------------------------------

def test_a_full_hand_replays_without_losing_chips():
    """
    Every chip that goes in is in the pot at the end.

    The engine's accounting is sound -- the audit says so -- and this bridge does
    its own, so a disagreement here is the bridge being wrong. Both players call
    a 200 bet preflop and check the rest: 400 in the middle, and nothing after.
    """
    node = replay(state("b200c/kk/kk/kk"), RNG())
    assert node.pot == 400
    assert node.to_call == 0
    assert node.street == 3
