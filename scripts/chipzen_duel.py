"""
Two bot configurations, whole, head to head over duplicate hands.

    venv/bin/python scripts/chipzen_duel.py \\
        --a results/cfr/ladder169l_v5c --a-flags "" --a-label v7b \\
        --b results/cfr/ladder169l_v5c --b-flags "--deep-primary" --b-label v5c \\
        --hands 2000 --stack-bb 100

Every instrument before this one measured a single pickle. The cross-tree
gate (`tools/xtree-gate.sh`) ranks two solves of different trees, but a bare
pickle has no companion, so its answer to "which primary?" is "the one-raise
solve loses every re-raise it faces" or "the cap-2 solve wins them all",
depending on which seat is allowed to re-raise (19 September). The bot is a
primary plus companions plus reads, and only the arena has ever scored that
whole, twenty matches at a time at ±40 chips a hand. This plays it here: both
seats are `ArenaPlayer`s built exactly as `chipzen_run.py` builds them, fed
the arena's own message shape (state dict, `valid_actions`, seat) by a small
dealer that follows the arena's conventions (a raise's amount is the level, a
call's the increment, blinds posted, min-raise the last increment or a big
blind). Duplicate deals with the seats swapped, so cards and position cancel,
and the figure is chips per hand to A with its standard error.

What it is not: the arena. Its opponents adapt, its blinds climb, its clock
runs. A configuration that wins here has earned a burst, not a fixture.
"""
import argparse
import os
import sys
import time
from typing import List, Optional

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from abstraction.equity import FULL_DECK  # noqa: E402
from chipzen.opponents import Profiles  # noqa: E402
from chipzen.player import ArenaPlayer  # noqa: E402
from engine.hand_eval_fast import score_hand_7_fast  # noqa: E402
from scripts.chipzen_run import ladder_paths  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PHASES = ("preflop", "flop", "turn", "river")
BOARD_AT = {"preflop": 0, "flop": 3, "turn": 4, "river": 5}
#: The arena's blind schedule, read from every logged match (20 September):
#: the big blind by twenty-hand level, then doubling on from the last entry.
ARENA_BLINDS = (100, 150, 200, 300, 400, 600, 800, 1000, 1200, 1600, 2000, 3000)
ARENA_STACK = 10000


def arena_big_blind(hand_number: int) -> int:
    level = (hand_number - 1) // 20
    if level < len(ARENA_BLINDS):
        return ARENA_BLINDS[level]
    return ARENA_BLINDS[-1] * 2 ** (level - len(ARENA_BLINDS) + 1)


def build(ladder_dir: str, flags: str, label: str, rng: np.random.Generator,
          profiles_path: Optional[str]):
    """
    An ArenaPlayer as `chipzen_run.py` would start it with these flags, or one
    of the scripted field shapes when the "directory" is `archetype:<kind>`
    (chipzen/archetypes.py): a station, a nit, a maniac or a fold-or-raise
    bot, so a set can be measured against the field's mistakes and not only
    against our own solver.
    """
    if ladder_dir.startswith("archetype:"):
        from chipzen.archetypes import build_archetype
        player = build_archetype(ladder_dir.split(":", 1)[1], rng)
        player.label = label
        return player
    deep = "--deep-primary" in flags
    _, ladder, companions = ladder_paths(ladder_dir, deep)
    player = ArenaPlayer(ladder, rng, companions=companions,
                         river_shove_companion="--river-shove-companion" in flags,
                         stack_cap="--stack-cap" in flags,
                         river="--river-solve" in flags)
    if profiles_path:
        player.profiles = Profiles(profiles_path, sequential="--sequential-triggers" in flags,
                                   scout_reads="--scout-reads" in flags)
    player.label = label  # noqa: attribute for the report only
    return player


def score7(hole: List[int], board: List[int]) -> int:
    cards = hole + board
    return int(score_hand_7_fast(np.array([c % 13 for c in cards], dtype=np.int64),
                                 np.array([c // 13 for c in cards], dtype=np.int64)))


class Dealer:
    """One hand under the arena's rules, driving two players through `decide`."""

    def __init__(self, players, deck: List[int], stack, small_blind: int, big_blind: int,
                 hand_number: int, opponents):
        self.players = players
        self.opponents = opponents            # names each player calls the other
        self.deck = deck
        self.stack = list(stack) if isinstance(stack, (list, tuple)) else [stack, stack]
        self.sb, self.bb = small_blind, big_blind
        self.hand_number = hand_number
        self.hole = [deck[0:2], deck[2:4]]
        self.board_cards = deck[4:9]
        self.history: List[dict] = []
        self.committed = [0, 0]               # this street
        self.contributed = [0, 0]             # whole hand
        self.pot = 0
        self.phase = "preflop"
        self.last_increment = big_blind
        self.folded: Optional[int] = None

    def post(self, seat, action, amount):
        self.history.append({"seat": seat, "action": action, "amount": amount, "phase": self.phase})
        self.committed[seat] += amount
        self.contributed[seat] += amount
        self.stack[seat] -= amount
        self.pot += amount

    def state_for(self, seat: int) -> dict:
        opp = 1 - seat
        to_call = min(self.committed[opp] - self.committed[seat], self.stack[seat])
        level = self.committed[seat] + to_call
        min_raise = min(level + max(self.last_increment, self.bb), self.committed[seat] + self.stack[seat])
        max_raise = self.committed[seat] + self.stack[seat]
        n = BOARD_AT[self.phase]
        return {"hand_number": self.hand_number, "phase": self.phase,
                "board": [str(FULL_DECK[c]) for c in self.board_cards[:n]],
                "your_hole_cards": [str(FULL_DECK[c]) for c in self.hole[seat]],
                "pot": self.pot, "your_stack": self.stack[seat], "opponent_stacks": [self.stack[opp]],
                "to_call": max(to_call, 0), "min_raise": min_raise, "max_raise": max_raise,
                "action_history": list(self.history)}

    def valid_for(self, seat: int) -> List[str]:
        opp = 1 - seat
        to_call = self.committed[opp] - self.committed[seat]
        out = []
        if to_call > 0:
            out += ["fold", "call"]
        else:
            out.append("check")
        if self.stack[seat] > max(to_call, 0) and self.stack[opp] > 0:
            out.append("raise")
        return out

    def apply(self, seat: int, decision: dict):
        opp = 1 - seat
        action = decision["action"]
        to_call = self.committed[opp] - self.committed[seat]
        valid = self.valid_for(seat)
        if action == "check" and to_call > 0:
            action = "call"                                              # the arena rejects a check facing a bet
        if action == "raise" and "raise" not in valid:
            action = "call" if to_call > 0 else "check"
        if action == "fold":
            self.history.append({"seat": seat, "action": "fold", "amount": 0, "phase": self.phase})
            self.folded = seat
        elif action == "check":
            self.history.append({"seat": seat, "action": "check", "amount": 0, "phase": self.phase})
        elif action == "call":
            self.post(seat, "call", min(to_call, self.stack[seat]))
        else:
            level = int(decision["params"].get("amount") or 0)
            level = max(level, self.committed[seat] + to_call)         # never below a call
            ceiling = self.committed[seat] + self.stack[seat]
            min_level = self.committed[seat] + to_call + max(self.last_increment, self.bb)
            if level < min_level and level < ceiling:
                level = min(min_level, ceiling)                          # the arena's min_raise
            level = min(level, ceiling)                                  # never above the stack
            increment = level - self.committed[seat]
            raise_by = level - self.committed[opp]
            if raise_by <= 0:                                            # a "raise" that only calls
                self.post(seat, "call", min(to_call, self.stack[seat]))
                return
            if raise_by >= self.last_increment:
                self.last_increment = raise_by                           # a short all-in raise leaves the minimum alone
            self.history.append({"seat": seat, "action": "raise", "amount": level, "phase": self.phase})
            self.committed[seat] = level
            self.contributed[seat] += increment
            self.stack[seat] -= increment
            self.pot += increment

    def play(self) -> List[int]:
        """Net chips to each seat at the end of the hand."""
        self.post(0, "post_small_blind", min(self.sb, self.stack[0]))
        self.post(1, "post_big_blind", min(self.bb, self.stack[1]))
        for phase in PHASES:
            self.phase = phase
            if phase != "preflop":
                self.committed = [0, 0]
                self.last_increment = self.bb
            if min(self.stack) == 0 and self.committed[0] == self.committed[1]:
                continue                                                # all in: run it out
            to_act = 0 if phase == "preflop" else 1
            acted: List[int] = []
            guard = 0
            while True:
                guard += 1
                if guard > 2 * (sum(self.stack) + self.pot) // max(self.bb, 1) + 8:
                    raise RuntimeError(f"hand {self.hand_number} did not close: phase {self.phase} committed "
                                       f"{self.committed} stacks {self.stack} acted {acted[-6:]} "
                                       f"history {[(h['seat'], h['action'], h['amount']) for h in self.history]}")
                if self.folded is not None:
                    break
                if self.committed[0] == self.committed[1] and len(acted) >= 2:
                    break
                if self.committed[0] == self.committed[1] and min(self.stack) == 0:
                    break
                # A call for less than the bet, or a blind posted for less: the
                # seat with the smaller commitment has no chips left to answer
                # with, so the street is closed and the uncalled excess goes
                # back, as the trees and the engine both do. The test is on
                # the *short* seat's stack: a shove by the seat that committed
                # more leaves the other seat with chips and a decision, and an
                # earlier version that tested min(stack) refunded that shove
                # before the opponent was asked, so the hand played on as if
                # it had never happened.
                if self.committed[0] != self.committed[1]:
                    short = 0 if self.committed[0] < self.committed[1] else 1
                    excess = self.committed[1 - short] - self.committed[short]
                    if self.stack[short] == 0 and excess > 0:
                        self.committed[1 - short] -= excess
                        self.contributed[1 - short] -= excess
                        self.stack[1 - short] += excess
                        self.pot -= excess
                        break
                seat = to_act
                opp = 1 - seat
                if self.stack[seat] == 0:
                    # An all-in seat is never asked (the arena does not ask it
                    # either); a short blind post left it behind and it was
                    # being offered fold/call for nothing, and a folding
                    # player lost its stack without a showdown.
                    acted.append(seat); to_act = opp; continue
                state = self.state_for(seat)
                decision = self.players[seat].decide(state, self.valid_for(seat), seat)
                self.apply(seat, decision)
                acted.append(seat)
                to_act = opp
            if self.folded is not None:
                break
        if self.folded is not None:
            winner = 1 - self.folded
            net = [0, 0]
            net[winner] = self.contributed[self.folded]
            net[self.folded] = -self.contributed[self.folded]
            return net
        at_risk = min(self.contributed)
        s0 = score7(self.hole[0], self.board_cards)
        s1 = score7(self.hole[1], self.board_cards)
        if s0 > s1:
            return [at_risk, -at_risk]
        if s1 > s0:
            return [-at_risk, at_risk]
        return [0, 0]


def play_match(players, rng: np.random.Generator, opponents) -> dict:
    """
    One arena-style match: 10,000 chips each, the arena's blind schedule, the
    button alternating, until a stack is gone. Returns the winner's seat, the
    hands played and the net to seat 0. A fixture is decided this way, by
    whoever wins the last big pot once the blinds are high, and no fixed-depth
    figure says which layout does that better; this does.
    """
    stacks = [ARENA_STACK, ARENA_STACK]
    deck = np.arange(52)
    hand = 0
    while min(stacks) > 0 and hand < 400:
        hand += 1
        bb = arena_big_blind(hand)
        rng.shuffle(deck)
        cards = [int(c) for c in deck[:9]]
        # The button alternates: on even hands seat 1 posts the small blind.
        # The dealer always seats the small blind at index 0, so swap.
        if hand % 2 == 1:
            net = Dealer(players, cards, stacks, bb // 2, bb, hand, opponents).play()
        else:
            swapped = Dealer([players[1], players[0]], cards, [stacks[1], stacks[0]], bb // 2, bb, hand,
                             (opponents[1], opponents[0])).play()
            net = [swapped[1], swapped[0]]
        stacks = [stacks[0] + net[0], stacks[1] + net[1]]
    winner = 0 if stacks[0] > stacks[1] else (1 if stacks[1] > stacks[0] else -1)   # -1: a draw at the cap
    return {"winner": winner, "hands": hand, "net0": stacks[0] - ARENA_STACK}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--arena-matches", type=int, default=0,
                        help="instead of duplicate hands at one depth, play this many arena-style matches "
                             "(10,000 chips, the arena's blind schedule, to a bust) and report the match win rate")
    parser.add_argument("--a", required=True, help="ladder directory for A")
    parser.add_argument("--a-flags", default="", help='runner flags for A, e.g. "--deep-primary"')
    parser.add_argument("--a-label", default="A")
    parser.add_argument("--b", required=True, help="ladder directory for B, or archetype:{station,nit,maniac,foldraise}")
    parser.add_argument("--b-flags", default="")
    parser.add_argument("--b-label", default="B")
    parser.add_argument("--hands", type=int, default=2000, help="duplicate deals (each played twice)")
    parser.add_argument("--stack-bb", type=float, default=100.0)
    parser.add_argument("--big-blind", type=int, default=100)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--profiles", help="opponents.json for the reads (default: none, so no read fires)")
    parser.add_argument("--output")
    args = parser.parse_args()

    rng = np.random.default_rng(args.seed)
    a = build(args.a, args.a_flags, args.a_label, np.random.default_rng(args.seed + 1), args.profiles)
    b = build(args.b, args.b_flags, args.b_label, np.random.default_rng(args.seed + 2), args.profiles)
    a.opponent, b.opponent = args.b_label, args.a_label
    stack = int(args.stack_bb * args.big_blind)
    sb = args.big_blind // 2
    what = (f"{args.arena_matches:,} arena matches (10,000 chips, the arena's blind schedule)" if args.arena_matches
            else f"{args.hands:,} duplicate deals at {args.stack_bb:g}bb, blinds {sb}/{args.big_blind}")
    print(f"{args.a_label} ({args.a} {args.a_flags!r}) vs {args.b_label} ({args.b} {args.b_flags!r}): {what}", flush=True)

    if args.arena_matches:
        wins = np.empty(args.arena_matches); hands = np.empty(args.arena_matches); nets = np.empty(args.arena_matches)
        started = time.perf_counter()
        for i in range(args.arena_matches):
            # A sits in seat 0 on even matches and seat 1 on odd ones, so the
            # first-hand button alternates across the sample.
            if i % 2 == 0:
                r = play_match([a, b], rng, (args.b_label, args.a_label)); won = 0.5 if r["winner"] < 0 else float(r["winner"] == 0); net = r["net0"]
            else:
                r = play_match([b, a], rng, (args.a_label, args.b_label)); won = 0.5 if r["winner"] < 0 else float(r["winner"] == 1); net = -r["net0"]
            wins[i], hands[i], nets[i] = won, r["hands"], net
            if (i + 1) % max(1, args.arena_matches // 20) == 0 or i + 1 == args.arena_matches:
                taken = time.perf_counter() - started
                p = wins[: i + 1].mean(); se = np.sqrt(p * (1 - p) / (i + 1))
                print(f"  {i + 1:>5,}/{args.arena_matches:,} matches  {args.a_label} wins {100 * p:5.1f}% ± {100 * se:4.1f}  "
                      f"{hands[: i + 1].mean():5.1f} hands/match  {taken:5.0f}s  "
                      f"eta {(args.arena_matches - i - 1) * taken / (i + 1) / 60:5.1f} min", flush=True)
        p = float(wins.mean()); se = float(np.sqrt(p * (1 - p) / args.arena_matches))
        print(f"\n{args.a_label} vs {args.b_label}: {args.a_label} wins {100 * p:.1f}% ± {100 * se:.1f} of "
              f"{args.arena_matches:,} arena matches, {hands.mean():.1f} hands a match; "
              f"A: {a.stats.decisions} decisions, {a.stats.misses} misses, {a.stats.companion_hits} companion, "
              f"{a.stats.fallbacks} rule; B: {b.stats.decisions}, {b.stats.misses}, {b.stats.companion_hits}, {b.stats.fallbacks}")
        if args.output:
            import json
            with open(args.output, "w") as handle:
                json.dump({"a": {"dir": args.a, "flags": args.a_flags, "label": args.a_label},
                           "b": {"dir": args.b, "flags": args.b_flags, "label": args.b_label},
                           "arena_matches": args.arena_matches, "win_rate": p, "stderr": se,
                           "hands_per_match": float(hands.mean()), "seed": args.seed,
                           "a_stats": vars(a.stats), "b_stats": vars(b.stats),
                           "measured": time.strftime("%Y-%m-%d %H:%M")}, handle, indent=1, default=str)
        return

    deck = np.arange(52)
    diffs = np.empty(args.hands)
    started = time.perf_counter()
    for i in range(args.hands):
        rng.shuffle(deck)
        cards = [int(c) for c in deck[:9]]
        first = Dealer([a, b], cards, stack, sb, args.big_blind, 2 * i + 1, (args.b_label, args.a_label)).play()
        second = Dealer([b, a], cards, stack, sb, args.big_blind, 2 * i + 2, (args.a_label, args.b_label)).play()
        diffs[i] = (first[0] + second[1]) / 2.0              # A's net, averaged over both seats
        if (i + 1) % max(1, args.hands // 20) == 0 or i + 1 == args.hands:
            taken = time.perf_counter() - started
            mean = diffs[: i + 1].mean(); se = diffs[: i + 1].std() / np.sqrt(i + 1)
            print(f"  {i + 1:>6,}/{args.hands:,}  {mean:+7.1f} ± {se:5.1f} chips/hand to {args.a_label}  "
                  f"{taken:5.0f}s  eta {(args.hands - i - 1) * taken / (i + 1) / 60:5.1f} min", flush=True)
    mean, se = float(diffs.mean()), float(diffs.std() / np.sqrt(args.hands))
    bb100 = 100.0 * mean / args.big_blind
    print(f"\n{args.a_label} vs {args.b_label}: {mean:+.1f} ± {se:.1f} chips/hand "
          f"({bb100:+.1f} BB/100) over {args.hands:,} duplicate deals; "
          f"A: {a.stats.decisions} decisions, {a.stats.misses} misses, {a.stats.companion_hits} companion, "
          f"{a.stats.fallbacks} rule; B: {b.stats.decisions}, {b.stats.misses}, {b.stats.companion_hits}, {b.stats.fallbacks}")
    if args.output:
        import json
        with open(args.output, "w") as handle:
            json.dump({"a": {"dir": args.a, "flags": args.a_flags, "label": args.a_label},
                       "b": {"dir": args.b, "flags": args.b_flags, "label": args.b_label},
                       "hands": args.hands, "stack_bb": args.stack_bb, "big_blind": args.big_blind,
                       "seed": args.seed, "chips_per_hand": mean, "stderr": se, "bb_per_100": bb100,
                       "a_stats": vars(a.stats), "b_stats": vars(b.stats),
                       "measured": time.strftime("%Y-%m-%d %H:%M")}, handle, indent=1, default=str)
        print(f"wrote {args.output}")


if __name__ == "__main__":
    main()
