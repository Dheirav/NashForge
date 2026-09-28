"""
NashForge on the Chipzen upload track: the arena bot, with its solved strategies stored compactly.

The platform imports this file and plays the `Bot` subclass below. Everything the bot needs is in this
directory: `nfarena/` is the arena player (our `chipzen` package, renamed so it does not shadow the
SDK's), the shared modules beside it are the rules, card abstraction and lookup it uses, and
`ladder/` holds one table per stack depth (`cfr/pure.py`: hashed keys, 32-bit probabilities, JSON
for the rest). The set is v5x, played purified, which is how it measured best against the field.

A decision that raises is answered with check or fold rather than a timeout, so a bug costs one
action and never the match.
"""
import sys
from pathlib import Path

import numpy as np
from chipzen import Action, Bot, GameState

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from nfarena.player import ArenaPlayer  # noqa: E402

PURIFY = "all"


class NashForge(Bot):
    def __init__(self):
        rungs = sorted(str(p)[:-len(".rung.json")] + ".pkl" for p in (HERE / "ladder").glob("*.rung.json"))
        self.player = ArenaPlayer(rungs, np.random.default_rng(), companions=[], purify=PURIFY, stack_cap=True)
        self.player.label = "NashForge"

    def on_match_start(self, match_info: dict) -> None:
        # The opponent's name goes on each decision's record, as on the remote track.
        me = match_info.get("your_seat", match_info.get("seat"))
        for seat in match_info.get("seats") or match_info.get("players") or []:
            if isinstance(seat, dict) and seat.get("seat") != me:
                self.player.opponent = seat.get("name") or seat.get("bot_name")

    def decide(self, state: GameState) -> Action:
        valid = list(state.valid_actions)
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
