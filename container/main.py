"""
NashForge on the Chipzen upload track: the arena bot, with its solved strategies stored compactly.

The container's entrypoint runs this file; the `__main__` block connects to the match the executor
names in CHIPZEN_WS_URL and plays the `Bot` subclass below. Everything the bot needs is in this
directory: `nfarena/` is the arena player (our `chipzen` package, renamed so it does not shadow the
SDK's), the shared modules beside it are the rules, card abstraction and lookup it uses, and
`ladder/` holds one table per stack depth (`cfr/pure.py`: hashed keys, 32-bit probabilities, JSON
for the rest). The set is v5x, played purified, which is how it measured best against the field,
with the opponent reads the season's fixtures played: `profiles.json` (trimmed to what the reads use)
and `reads.toml` (the tuned thresholds).

A decision that raises is answered with check or fold rather than a timeout, so a bug costs one
action and never the match. At a table of more than two seats (the upload track's 6-max sit-and-go)
the solver is not used at all: see `multiway_action`.
"""
import asyncio
import os
import sys
from pathlib import Path

import numpy as np
from chipzen import Action, Bot, GameState, run_bot

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
# The read thresholds the live bot plays with (kept out of the public tree, like the tables); they
# are read when nfarena.opponents is imported, so this comes first.
os.environ.setdefault("CHIPZEN_READS", str(HERE / "reads.toml"))

from nfarena.opponents import Profiles  # noqa: E402
from nfarena.player import ArenaPlayer  # noqa: E402

PURIFY = "all"


class NashForge(Bot):
    def __init__(self):
        rungs = sorted(str(p)[:-len(".rung.json")] + ".pkl" for p in (HERE / "ladder").glob("*.rung.json"))
        self.player = ArenaPlayer(rungs, np.random.default_rng(), companions=[], purify=PURIFY, stack_cap=True)
        self.player.label = "NashForge"
        # Opponent reads, as the fixtures played them (--sequential-triggers --scout-reads): the
        # profiles trimmed to what the reads use (container/trim_profiles.py), counted on as we play.
        # Never saved: the filesystem is read-only, and each match starts from the shipped counts.
        self.player.profiles = Profiles(str(HERE / "profiles.json"), sequential=True, scout_reads=True)
        self.seat, self.stacks_before = None, None
        #: True at a table of more than two seats. The solver, the bridge and the reads are heads-up
        #: only (seats 0 and 1, one opponent's stack, one opponent's profile), and the upload track
        #: also runs a 6-max sit-and-go, which "poker" in supported_games does not exclude.
        self.multiway = False

    def on_match_start(self, match_info: dict) -> None:
        # As chipzen/client.py reads it: our seat is the entry marked is_self, the other is the opponent.
        seats = match_info.get("seats") or []
        self.multiway = len(seats) > 2
        for entry in seats:
            if entry.get("is_self"):
                self.seat = int(entry["seat"])
            else:
                self.player.opponent = entry.get("display_name")

    def on_round_start(self, message: dict) -> None:
        self.stacks_before = (message.get("state") or {}).get("stacks")

    def on_round_result(self, message: dict) -> None:
        # Every finished hand is counted into the opponent's profile, which is what lets a read
        # form against a bot we have never met.
        try:
            result = message.get("result") or {}
            if self.seat is not None and self.player.opponent and not self.multiway:
                after = result.get("stacks")
                net = after[self.seat] - self.stacks_before[self.seat] if self.stacks_before and after else 0
                self.player.profiles.observe(result, self.seat, self.player.opponent, net)
        except Exception:
            pass

    def decide(self, state: GameState) -> Action:
        valid = list(state.valid_actions)
        if self.multiway or len(state.opponent_stacks) > 1:
            return self.multiway_action(state, valid)
        try:
            # The player reads the server's own state dict, as the remote client hands it over.
            raw = {"hand_number": state.hand_number, "phase": state.phase,
                   "your_hole_cards": [str(c) for c in state.hole_cards], "board": [str(c) for c in state.board],
                   "pot": state.pot, "your_stack": state.your_stack, "opponent_stacks": list(state.opponent_stacks),
                   "your_seat": state.your_seat, "dealer_seat": state.dealer_seat, "to_call": state.to_call,
                   "min_raise": state.min_raise, "max_raise": state.max_raise,
                   "action_history": list(state.action_history)}
            decision = self.player.decide(raw, valid, state.your_seat)
            action = decision["action"]
            if action == "raise":
                return Action.raise_to(int(decision["params"]["amount"]))
            if action in ("fold", "check", "call"):
                return getattr(Action, action)()
        except Exception:
            pass
        return Action.check() if "check" in valid else Action.fold()

    #: Hands shoved before the flop at a multiway table: strong enough against several opponents that
    #: all-in is not a mistake, so the bot is not simply blinded out.
    PREMIUM = {("A", "A"), ("K", "K"), ("Q", "Q"), ("A", "K")}

    def multiway_action(self, state: GameState, valid) -> Action:
        """No solver here: shove a premium hand before the flop, otherwise check or fold."""
        ranks = tuple(sorted((c.rank for c in state.hole_cards), key="23456789TJQKA".index, reverse=True))
        if state.phase == "preflop" and ranks in self.PREMIUM:
            if "raise" in valid and state.max_raise > 0:
                return Action.raise_to(int(state.max_raise))
            if "call" in valid:
                return Action.call()
        return Action.check() if "check" in valid else Action.fold()


if __name__ == "__main__":
    # The executor starts the container with the match's socket in CHIPZEN_WS_URL and a token or a
    # single-use ticket beside it (the SDK's developer manual, "container contract").
    asyncio.run(run_bot(os.environ["CHIPZEN_WS_URL"], NashForge(),
                        token=os.environ.get("CHIPZEN_TOKEN"), ticket=os.environ.get("CHIPZEN_TICKET")))
