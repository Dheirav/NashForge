"""
The abstract betting tree, and the information-set arithmetic that follows.

Card abstraction bounds how many hands the solver distinguishes; bet abstraction
bounds how many betting lines it distinguishes. Together they decide whether the
game fits in memory, which is the whole feasibility question for running CFR on
a laptop rather than a cluster.

The action space is the project's existing six — fold, check/call, three raise
sizes, all-in — reused as the bet abstraction, with raises capped per street.
That reuse is deliberate but not free: the six actions were designed as a policy
network's output layer, not as a CFR bet abstraction, and **action abstraction
upper-bounds achievable exploitability regardless of how well the solver runs.**
A floor in the exploitability curve may be the action space rather than the
solver, which is why this is stated in the proposal's threats to validity.

Counting information sets exactly needs no engine and no cards: the betting tree
is finite and small, so it is enumerated here, and the total is that count
multiplied by the buckets available on each street.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple

#: The existing six-action abstraction, in the project's established order.
FOLD, CHECK_CALL, RAISE_HALF, RAISE_POT, RAISE_TWO, ALL_IN = range(6)
ACTION_NAMES = ("fold", "check/call", "raise-half", "raise-pot", "raise-2x", "all-in")
RAISE_ACTIONS = (RAISE_HALF, RAISE_POT, RAISE_TWO, ALL_IN)

STREETS = ("preflop", "flop", "turn", "river")


def legal_actions(raises_so_far: int, facing_bet: bool, raise_cap: int,
                  last_action: int | None = None) -> Tuple[int, ...]:
    """
    Actions available given the state of the current street's betting.

    Folding with nothing to call is legal in poker but strictly dominated, so it
    is left out of the tree — it would double the branching factor to no
    purpose. Once the cap is reached only folding or calling remains.

    An all-in cannot be raised: a player facing one may only fold or call, since
    there are no chips left to raise with. Treating all-in as an ordinary raise
    inflates the tree with lines that cannot occur.
    """
    if last_action == ALL_IN:
        return (FOLD, CHECK_CALL)

    actions: List[int] = []
    if facing_bet:
        actions.append(FOLD)
    actions.append(CHECK_CALL)
    if raises_so_far < raise_cap:
        actions.extend(RAISE_ACTIONS)
    return tuple(actions)


def enumerate_street_sequences(raise_cap: int) -> List[Tuple[Tuple[int, ...], bool]]:
    """
    Every betting sequence for one street.

    Returns ``(sequence, ended_in_fold)`` pairs. A street closes when a bet is
    called or when both players check; a fold ends the hand outright.
    """
    completed: List[Tuple[Tuple[int, ...], bool]] = []

    def walk(sequence: Tuple[int, ...], raises: int, facing: bool, actor: int) -> None:
        last = sequence[-1] if sequence else None
        for action in legal_actions(raises, facing, raise_cap, last):
            extended = sequence + (action,)
            if action == FOLD:
                completed.append((extended, True))
            elif action == CHECK_CALL:
                if facing:                       # called a bet: street closes
                    completed.append((extended, False))
                elif sequence and sequence[-1] == CHECK_CALL:
                    completed.append((extended, False))   # checked through
                else:
                    walk(extended, raises, False, 1 - actor)
            else:                                # a bet or raise
                walk(extended, raises + 1, True, 1 - actor)

    walk((), 0, False, 0)
    return completed


def count_decision_points(raise_cap: int) -> Dict[int, int]:
    """
    Decision points per player within one street, keyed by player index.

    A decision point is a distinct public betting prefix at which that player is
    to act. Multiplied by the number of card buckets, this gives the information
    sets that street contributes.
    """
    counts = {0: 0, 1: 0}

    def walk(sequence: Tuple[int, ...], raises: int, facing: bool, actor: int) -> None:
        counts[actor] += 1
        last = sequence[-1] if sequence else None
        for action in legal_actions(raises, facing, raise_cap, last):
            if action == FOLD:
                continue
            if action == CHECK_CALL:
                if facing or (sequence and sequence[-1] == CHECK_CALL):
                    continue
                walk(sequence + (action,), raises, False, 1 - actor)
            else:
                walk(sequence + (action,), raises + 1, True, 1 - actor)

    walk((), 0, False, 0)
    return counts


@dataclass(frozen=True)
class AbstractionSize:
    """Measured size of an abstract game."""
    buckets: Dict[str, int]
    raise_cap: int
    decision_points_per_street: int
    reaching_sequences: Dict[str, int]
    information_sets: int
    table_bytes: int

    def summary(self) -> str:
        buckets = " ".join(f"{s}={self.buckets[s]}" for s in STREETS)
        return (f"cap={self.raise_cap}  {buckets}  "
                f"infosets={self.information_sets:,}  "
                f"table={self.table_bytes / 1e6:.1f} MB")


def measure(buckets: Dict[str, int], raise_cap: int = 2,
            num_actions: int = 6, bytes_per_entry: int = 8) -> AbstractionSize:
    """
    Information sets and table memory for an abstraction, counted exactly.

    A street is reached once for each way an earlier street could close without
    a fold, so the betting lines multiply across streets. Memory assumes one
    regret and one strategy accumulator per action, which is what CFR stores.
    """
    per_street = count_decision_points(raise_cap)
    decisions = per_street[0] + per_street[1]

    surviving = len([seq for seq, folded in enumerate_street_sequences(raise_cap)
                     if not folded])

    reaching: Dict[str, int] = {}
    lines = 1
    total = 0
    for street in STREETS:
        reaching[street] = lines
        total += lines * decisions * buckets[street]
        lines *= surviving

    entries = total * num_actions * 2          # regret and strategy sums
    return AbstractionSize(
        buckets=dict(buckets),
        raise_cap=raise_cap,
        decision_points_per_street=decisions,
        reaching_sequences=reaching,
        information_sets=total,
        table_bytes=entries * bytes_per_entry,
    )
