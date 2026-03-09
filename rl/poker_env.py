"""
Gym-style poker environment wrapping the PokerGame engine.

Design goals
------------
* Zero dependency on `gym` or `gymnasium` – this project only needs NumPy
  and PyTorch, so we ship a minimal Env interface here.
* Engine-agnostic reward shaping via a pluggable RewardShaper.
* Opponent pool that can hold any mix of:
    - EvolutionAgent (NumPy network from training/)
    - RandomAgent / HeuristicAgent (from agents/)
    - PPOAgent (from rl/)
    – i.e. anything with .get_action(game, player_id) -> int

Episode = one poker hand (reset_hand → apply actions until showdown).

Observation
-----------
17-dimensional float32 feature vector produced by engine.get_state_vector().

Action space
------------
Discrete(6):  0=fold  1=check/call  2=raise½pot  3=raise1pot  4=raise2x  5=all-in

Reward
------
Default: chip_delta / big_blind at end of hand (BB units).
Shaped reward (optional) adds immediate signals (see RewardShaper below).
"""

from __future__ import annotations

import random
from typing import List, Optional, Tuple, Dict, Any
import numpy as np

from engine import PokerGame, get_state_vector, get_action_mask as _engine_get_action_mask
from training.fitness import abstract_action_to_engine_action


def get_abstract_action_mask(game, player_id: int) -> "np.ndarray":
    """
    Convert the engine's 5-slot mask [fold,check,call,raise,all-in]
    to the 6-slot abstract mask used by policy networks:
      0=fold  1=check/call  2=raise½pot  3=raisepot  4=raise2x  5=all-in

    Rules:
      - slot 0 (fold)       ← engine fold
      - slot 1 (check/call) ← engine check OR call
      - slots 2-4 (raises)  ← engine raise (all three get the same bit)
      - slot 5 (all-in)     ← engine all-in
    """
    eng = _engine_get_action_mask(game, player_id)   # [fold, check, call, raise, all-in]
    mask = np.zeros(6, dtype=np.float32)
    mask[0] = float(eng[0])                   # fold
    mask[1] = float(eng[1] or eng[2])         # check or call
    mask[2] = float(eng[3])                   # raise (½pot)
    mask[3] = float(eng[3])                   # raise (1pot)
    mask[4] = float(eng[3])                   # raise (2x)
    mask[5] = float(eng[4])                   # all-in
    # Ensure at least one legal action
    if mask.sum() == 0:
        mask[1] = 1.0
    return mask


# ---------------------------------------------------------------------------
# Space stubs (no gym dependency)
# ---------------------------------------------------------------------------

class DiscreteSpace:
    """Minimal stand-in for gym.spaces.Discrete."""
    def __init__(self, n: int):
        self.n = n
        self.shape = (n,)

    def sample(self) -> int:
        return random.randrange(self.n)


class BoxSpace:
    """Minimal stand-in for gym.spaces.Box."""
    def __init__(self, low: float, high: float, shape: Tuple[int, ...], dtype=np.float32):
        self.low  = np.full(shape, low,  dtype=dtype)
        self.high = np.full(shape, high, dtype=dtype)
        self.shape = shape
        self.dtype = dtype


# ---------------------------------------------------------------------------
# Reward shaper (pluggable)
# ---------------------------------------------------------------------------

class RewardShaper:
    """
    Compute immediate (per-step) reward signals to augment the sparse
    terminal chip-delta reward.

    Override shape_step() to add custom signals without touching env code.
    Final reward = terminal_chips_reward + sum(shaping_bonuses_over_hand).
    """

    def shape_step(
        self,
        game: PokerGame,
        player_id: int,
        action_idx: int,
        prev_stack: int,
    ) -> float:
        """
        Called *after* the action is applied to the game.

        Default implementation: zero (pure terminal reward).
        """
        return 0.0


class AggressionShaper(RewardShaper):
    """
    Small bonus for +EV aggression: adds a tiny positive reward when the
    agent raises into a situation where the pot odds favour it, and a tiny
    penalty for calling with bad pot odds.

    This is intentionally small so it doesn't override the final chip signal.
    """

    RAISE_BONUS   =  0.05   # BB units
    BAD_CALL_PEN  = -0.03   # BB units

    def shape_step(
        self,
        game: PokerGame,
        player_id: int,
        action_idx: int,
        prev_stack: int,
    ) -> float:
        bb = game.state.big_blind
        player = game.players[player_id]
        to_call = game.current_bet - player.bet
        pot      = game.state.pot.total or 1

        pot_odds = to_call / (pot + to_call + 1e-8)

        if action_idx in (2, 3, 4, 5):  # raise / all-in
            return self.RAISE_BONUS / bb
        if action_idx == 1 and to_call > 0:  # call with bad pot odds
            if pot_odds > 0.5:
                return self.BAD_CALL_PEN / bb
        return 0.0


# ---------------------------------------------------------------------------
# Main environment
# ---------------------------------------------------------------------------

class PokerEnv:
    """
    Single-agent poker environment (agent = seat 0).

    Opponents occupy the remaining seats and are sampled from
    `opponent_pool` at the start of each episode.

    Parameters
    ----------
    num_players:      Table size (2-6). Default: 2 (heads-up).
    starting_stack:   Chips each player starts with. Default: 1 000.
    small_blind:      SB amount. Default: 5.
    big_blind:        BB amount. Default: 10.
    opponent_pool:    List of agents with .get_action(game, pid). If None,
                      random agents are used.
    reward_shaper:    Optional RewardShaper for dense rewards.
    seed:             Random seed for reproducibility.
    """

    OBS_SIZE   = 17
    NUM_ACTIONS = 6

    def __init__(
        self,
        num_players:    int                     = 2,
        starting_stack: int                     = 1_000,
        small_blind:    int                     = 5,
        big_blind:      int                     = 10,
        opponent_pool:  Optional[List[Any]]     = None,
        reward_shaper:  Optional[RewardShaper]  = None,
        seed:           Optional[int]           = None,
    ):
        assert 2 <= num_players <= 6, "num_players must be 2-6"
        self.num_players    = num_players
        self.starting_stack = starting_stack
        self.small_blind    = small_blind
        self.big_blind      = big_blind
        self.reward_shaper  = reward_shaper or RewardShaper()

        # Opponent pool – any object with .get_action(game, pid) -> int
        if opponent_pool is None:
            from rl.agents.random_opponent import RandomOpponent
            self.opponent_pool = [RandomOpponent() for _ in range(num_players - 1)]
        else:
            self.opponent_pool = list(opponent_pool)

        self._rng  = np.random.default_rng(seed)
        self._game: Optional[PokerGame] = None
        self._agent_id: int = 0          # Agent is always seat 0

        # Spaces
        self.observation_space = BoxSpace(0.0, 1.0, (self.OBS_SIZE,))
        self.action_space      = DiscreteSpace(self.NUM_ACTIONS)

        # Per-episode stats
        self._episode_shaped_rewards: float = 0.0
        self._episode_actions: int = 0

    # ------------------------------------------------------------------
    # Core Gym interface
    # ------------------------------------------------------------------

    def reset(self) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Start a new hand.

        Returns
        -------
        obs:  Initial observation for the agent (float32, shape [OBS_SIZE]).
        info: Dict with metadata (game_seed, etc.).
        """
        seed = int(self._rng.integers(0, 2**31))
        stacks = [self.starting_stack] * self.num_players

        self._game = PokerGame(
            player_stacks=stacks,
            small_blind=self.small_blind,
            big_blind=self.big_blind,
            seed=seed,
            enable_history=False,
        )

        self._episode_shaped_rewards = 0.0
        self._episode_actions = 0

        # Let opponents act until it is the agent's turn
        obs = self._advance_to_agent()
        info = {"game_seed": seed}
        return obs, info

    def step(
        self, action_idx: int
    ) -> Tuple[np.ndarray, float, bool, bool, Dict[str, Any]]:
        """
        Apply agent's action, let opponents respond, return next state.

        Returns
        -------
        obs:        Next observation (zeros if hand ended).
        reward:     Shaped step reward + terminal chip delta (in BB).
        terminated: True if hand is over.
        truncated:  Always False (no time-limit truncation).
        info:       Dict with chip_delta, bb_per_100, actions, etc.
        """
        game = self._game
        agent_id = self._agent_id
        prev_stack = game.players[agent_id].stack

        # Mask illegal actions
        mask = get_abstract_action_mask(game, agent_id)
        if not mask[action_idx]:
            action_idx = self._fallback_action(mask)

        # Apply agent action
        engine_action = abstract_action_to_engine_action(action_idx, game, agent_id)
        game.apply_action(agent_id, engine_action)
        self._episode_actions += 1

        # Shaped reward (immediate signal)
        shaped = self.reward_shaper.shape_step(game, agent_id, action_idx, prev_stack)
        self._episode_shaped_rewards += shaped

        # Check if hand is done
        terminated = self._is_done()

        if terminated:
            terminal_reward = self._terminal_reward(prev_stack)
            total_reward    = terminal_reward + self._episode_shaped_rewards
            obs             = np.zeros(self.OBS_SIZE, dtype=np.float32)
            chip_delta      = game.players[agent_id].stack - self.starting_stack
            info = {
                "chip_delta":  chip_delta,
                "bb_per_100":  (chip_delta / self.big_blind) * 100,
                "actions":     self._episode_actions,
                "shaped_bonus": self._episode_shaped_rewards,
            }
            return obs, total_reward, True, False, info

        # Let opponents act until agent's turn again (or hand ends)
        obs = self._advance_to_agent()

        if self._is_done():
            terminal_reward = self._terminal_reward(prev_stack)
            total_reward    = terminal_reward + self._episode_shaped_rewards
            chip_delta      = game.players[agent_id].stack - self.starting_stack
            info = {
                "chip_delta":  chip_delta,
                "bb_per_100":  (chip_delta / self.big_blind) * 100,
                "actions":     self._episode_actions,
                "shaped_bonus": self._episode_shaped_rewards,
            }
            return obs, total_reward, True, False, info

        return obs, shaped, False, False, {"actions": self._episode_actions}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _advance_to_agent(self) -> np.ndarray:
        """
        Run opponent actions until it's the agent's turn or the hand ends.
        Returns the agent's observation.
        """
        game = self._game
        while True:
            if self._is_done():
                return np.zeros(self.OBS_SIZE, dtype=np.float32)

            current = game.state.current_player
            if current is None:
                return np.zeros(self.OBS_SIZE, dtype=np.float32)
            if current == self._agent_id:
                break

            # Opponent acts
            opp_idx = (current - 1) % (self.num_players - 1)   # map seat -> pool idx
            opp_idx = min(opp_idx, len(self.opponent_pool) - 1)
            opponent = self.opponent_pool[opp_idx]

            opp_action_idx = opponent.get_action(game, current)
            opp_mask       = get_abstract_action_mask(game, current)
            if not opp_mask[opp_action_idx]:
                opp_action_idx = self._fallback_action(opp_mask)

            eng_action = abstract_action_to_engine_action(opp_action_idx, game, current)
            game.apply_action(current, eng_action)

        obs = np.array(get_state_vector(game, self._agent_id), dtype=np.float32)
        return obs

    def _is_done(self) -> bool:
        """True if the hand has reached showdown or only one player remains."""
        game = self._game
        if game.state.betting_round == "showdown":
            return True
        active = [p for p in game.players if not p.has_folded]
        if len(active) <= 1:
            return True
        return False

    def _terminal_reward(self, prev_agent_stack: int) -> float:
        """
        Chip delta normalised to big-blind units.

        Using starting_stack as baseline so reward = 0 means break-even.
        """
        final_stack = self._game.players[self._agent_id].stack
        chip_delta  = final_stack - self.starting_stack
        return chip_delta / self.big_blind

    @staticmethod
    def _fallback_action(mask: np.ndarray) -> int:
        """Return first legal action (check/call preferred, else fold)."""
        for preferred in (1, 0):            # try check/call first, then fold
            if mask[preferred]:
                return preferred
        legal = np.where(mask)[0]
        return int(legal[0]) if len(legal) else 1
