"""
PPO hyperparameter configuration.

Everything is in one dataclass so you can pass a single object around and
easily serialise/deserialise it (json.dumps(asdict(cfg))).
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
import json
from typing import List, Optional


@dataclass
class PPOConfig:
    """
    Full configuration for a PPO training run.

    Network
    -------
    obs_size:        Feature vector length (must match engine.get_state_vector).
    num_actions:     Number of abstract actions (must match engine action space).
    hidden_size:     Width of each hidden layer in the actor-critic trunk.
    num_layers:      Number of shared trunk layers.

    Environment
    -----------
    num_players:     Table size.  2 = heads-up, 6 = 6-max.
    starting_stack:  Starting chip count per player.
    small_blind:     Small blind.
    big_blind:       Big blind.
    use_aggression_shaper: Add AggressionShaper dense reward.

    Rollout
    -------
    n_steps:         Steps to collect per update (hands, not individual actions).
    n_envs:          Number of parallel environments (threads).

    PPO update
    ----------
    n_epochs:        Gradient epochs per rollout.
    batch_size:      Mini-batch size for gradient update.
    gamma:           Discount factor (set close to 1 for sparse terminal reward).
    gae_lambda:      GAE λ for advantage estimation.
    clip_range:      PPO clip ε.
    vf_coef:         Value function loss coefficient.
    ent_coef:        Entropy bonus coefficient.
    max_grad_norm:   Gradient clipping.
    lr:              Adam learning rate.
    lr_decay:        Multiply lr by this factor each update cycle (1.0 = no decay).
    target_kl:       Early-stop update if approx KL exceeds this (None = disabled).

    Training schedule
    -----------------
    total_hands:     Total environment steps (hands); controls run length.
    eval_every:      Evaluate vs opponent pool every N update cycles.
    save_every:      Save checkpoint every N update cycles.
    checkpoint_dir:  Directory to save checkpoints.
    log_dir:         Directory for training logs (CSV).

    Hall-of-fame
    ------------
    hof_dir:         Path to existing hall-of-fame directory (evolution agents).
                     If set, opponents are sampled from HoF at each episode.
    hof_sample_prob: Probability of using a HoF agent as the opponent.
    """

    # ── Network ───────────────────────────────────────────────────────
    obs_size:    int = 19
    num_actions: int = 6
    hidden_size: int = 128
    num_layers:  int = 2

    # ── Environment ───────────────────────────────────────────────────
    num_players:            int  = 2
    starting_stack:         int  = 1_000
    small_blind:            int  = 5
    big_blind:              int  = 10
    use_aggression_shaper:  bool = False

    # ── Rollout ───────────────────────────────────────────────────────
    n_steps: int = 512    # hands per rollout
    n_envs:  int = 1      # parallel envs (kept as 1 for simplicity; extend later)

    # ── PPO update ────────────────────────────────────────────────────
    n_epochs:       int   = 4
    batch_size:     int   = 64
    gamma:          float = 0.999    # episodes are short; keep high
    gae_lambda:     float = 0.95
    clip_range:     float = 0.2
    vf_coef:        float = 0.5
    ent_coef:       float = 0.01
    max_grad_norm:  float = 0.5
    lr:             float = 3e-4
    lr_decay:       float = 1.0
    target_kl:      Optional[float] = None

    # ── Training schedule ─────────────────────────────────────────────
    total_hands:     int = 500_000
    eval_every:      int = 20        # update cycles between evals
    save_every:      int = 50        # update cycles between checkpoints
    checkpoint_dir:  str = "checkpoints/ppo"
    log_dir:         str = "logs/ppo"

    # ── Hall-of-fame opponents ────────────────────────────────────────
    hof_dir:          Optional[str]   = None
    hof_sample_prob:  float           = 0.5

    # ── Misc ─────────────────────────────────────────────────────────
    seed:    Optional[int] = None
    device:  str           = "cpu"   # "cuda", "mps", "cpu"
    verbose: int           = 1       # 0=silent, 1=progress, 2=debug

    # ------------------------------------------------------------------

    def to_json(self, path: str) -> None:
        with open(path, "w") as f:
            json.dump(asdict(self), f, indent=2)

    @classmethod
    def from_json(cls, path: str) -> "PPOConfig":
        with open(path) as f:
            d = json.load(f)
        return cls(**d)

    def __post_init__(self):
        # Sanity checks
        assert self.n_steps >= self.batch_size, \
            "n_steps must be >= batch_size"
        assert 0 < self.clip_range < 1, \
            "clip_range should be in (0, 1)"

    @classmethod
    def heads_up_default(cls) -> "PPOConfig":
        """Sensible defaults for heads-up training."""
        return cls(
            num_players=2,
            n_steps=512,
            total_hands=500_000,
            hidden_size=128,
            ent_coef=0.01,
            hof_sample_prob=0.5,
        )

    @classmethod
    def multitable_default(cls) -> "PPOConfig":
        """Sensible defaults for 6-max training."""
        return cls(
            num_players=6,
            n_steps=1024,
            total_hands=2_000_000,
            hidden_size=256,
            ent_coef=0.005,
            hof_sample_prob=0.3,
        )
