"""
PPO Trainer.

Implements the full Proximal Policy Optimisation training loop:

  1. Collect n_steps transitions using the current policy.
  2. Compute GAE advantages.
  3. Optimise the clipped surrogate objective for n_epochs mini-batches.
  4. Optionally evaluate against opponent pool and save checkpoint.
  5. Repeat until total_hands reached.

Key design choices
------------------
* One environment per trainer (simple; extend to vectorised envs later).
* HoF opponent sampling: each episode randomly selects an opponent from the
  Hall-of-Fame pool (if configured) at probability hof_sample_prob.
* CSV logging: one row per update cycle with key statistics.
* Evaluation is decoupled — the trainer calls rl.eval.evaluator.evaluate_vs_pool().
"""

from __future__ import annotations

import csv
import os
import time
from typing import List, Optional, Any

import numpy as np
import torch
import torch.nn.functional as F
import torch.optim as optim

from rl.ppo.config import PPOConfig
from rl.ppo.agent import PPOAgent
from rl.ppo.buffer import RolloutBuffer
from rl.poker_env import PokerEnv, AggressionShaper


# ---------------------------------------------------------------------------
# HoF loader helper
# ---------------------------------------------------------------------------

def _load_hof_opponents(hof_dir: str) -> List[Any]:
    """
    Load all evolution agents from hall-of-fame directory.

    Returns a list of objects with .get_action(game, player_id) -> int.
    Each .npy file in hof_dir is loaded as a training.self_play.AgentPlayer.
    """
    import glob
    from training.policy_network import PolicyNetwork
    from training.config import NetworkConfig
    from training.self_play import AgentPlayer

    agents = []
    pattern = os.path.join(hof_dir, "*.npy")
    for path in sorted(glob.glob(pattern)):
        try:
            weights  = np.load(path)
            net_cfg  = NetworkConfig()
            net      = PolicyNetwork(net_cfg)
            net.set_weights(weights)
            agents.append(AgentPlayer(net))
        except Exception as e:
            print(f"[PPOTrainer] Warning: could not load HoF agent {path}: {e}")

    return agents


# ---------------------------------------------------------------------------
# PPO Trainer
# ---------------------------------------------------------------------------

class PPOTrainer:
    """
    Full PPO training loop.

    Parameters
    ----------
    config:          PPOConfig controlling all hyperparameters.
    opponent_pool:   Pre-built list of opponents (optional).
                     If None and config.hof_dir is set, loads HoF agents.
                     If None and no hof_dir, uses RandomOpponent.
    """

    def __init__(
        self,
        config:         PPOConfig,
        opponent_pool:  Optional[List[Any]] = None,
    ):
        self.cfg    = config
        self.device = torch.device(config.device)

        # ── Agent ────────────────────────────────────────────────────
        self.agent = PPOAgent(config)

        # ── Opponent pool ─────────────────────────────────────────────
        if opponent_pool is not None:
            self._opp_pool = opponent_pool
        elif config.hof_dir:
            self._opp_pool = _load_hof_opponents(config.hof_dir)
            if config.verbose:
                print(f"[PPOTrainer] Loaded {len(self._opp_pool)} HoF opponents from {config.hof_dir}")
        else:
            self._opp_pool = []   # PokerEnv will use RandomOpponent by default

        # ── Environment factory ───────────────────────────────────────
        shaper = AggressionShaper() if config.use_aggression_shaper else None
        self._env_kwargs = dict(
            num_players    = config.num_players,
            starting_stack = config.starting_stack,
            small_blind    = config.small_blind,
            big_blind      = config.big_blind,
            reward_shaper  = shaper,
            seed           = config.seed,
        )

        # ── Rollout buffer ────────────────────────────────────────────
        self.buffer = RolloutBuffer(
            n_steps     = config.n_steps,
            obs_size    = config.obs_size,
            num_actions = config.num_actions,
            gamma       = config.gamma,
            gae_lambda  = config.gae_lambda,
            device      = str(self.device),
        )

        # ── Optimiser ─────────────────────────────────────────────────
        self.optimizer = optim.Adam(self.agent.net.parameters(), lr=config.lr)

        # ── State trackers ────────────────────────────────────────────
        self.total_hands     = 0
        self.update_cycle    = 0
        self._rng            = np.random.default_rng(config.seed)
        self._current_lr     = config.lr

        # ── Logging ───────────────────────────────────────────────────
        os.makedirs(config.log_dir, exist_ok=True)
        os.makedirs(config.checkpoint_dir, exist_ok=True)

        self._log_path = os.path.join(config.log_dir, "training_log.csv")
        self._log_fields = [
            "update", "total_hands", "policy_loss", "value_loss",
            "entropy", "approx_kl", "clip_fraction",
            "mean_reward", "lr", "elapsed_s",
        ]
        self._start_time = time.time()
        self._init_log()

    # ------------------------------------------------------------------
    # Main training entry point
    # ------------------------------------------------------------------

    def train(self) -> PPOAgent:
        """
        Run the full training loop until total_hands is reached.

        Returns the trained PPOAgent.
        """
        cfg = self.cfg
        if cfg.verbose:
            print(f"[PPOTrainer] Starting PPO training")
            print(f"  total_hands={cfg.total_hands:,}  n_steps={cfg.n_steps}  n_epochs={cfg.n_epochs}")
            print(f"  network: {cfg.obs_size}→[{cfg.hidden_size}x{cfg.num_layers}]→{cfg.num_actions}")
            print(f"  device: {self.device}  opponent_pool_size: {len(self._opp_pool)}")

        while self.total_hands < cfg.total_hands:
            rewards = self._collect_rollout()
            stats   = self._ppo_update()
            self.update_cycle += 1

            # Apply LR decay
            if cfg.lr_decay < 1.0:
                self._current_lr *= cfg.lr_decay
                for g in self.optimizer.param_groups:
                    g["lr"] = self._current_lr

            # Log
            self._write_log(stats, np.mean(rewards))

            if cfg.verbose >= 1 and (self.update_cycle % 10 == 0):
                elapsed = time.time() - self._start_time
                print(
                    f"  [{self.update_cycle:5d}] "
                    f"hands={self.total_hands:,}  "
                    f"πloss={stats['policy_loss']:.4f}  "
                    f"vloss={stats['value_loss']:.4f}  "
                    f"ent={stats['entropy']:.4f}  "
                    f"rew={np.mean(rewards):.3f}  "
                    f"elapsed={elapsed:.0f}s"
                )

            # Evaluate
            if self.update_cycle % cfg.eval_every == 0:
                self._run_eval()

            # Save checkpoint
            if self.update_cycle % cfg.save_every == 0:
                self._save_checkpoint()

        # Final save
        self._save_checkpoint(label="final")
        if cfg.verbose:
            print(f"[PPOTrainer] Training complete. total_hands={self.total_hands:,}")

        return self.agent

    # ------------------------------------------------------------------
    # Rollout collection
    # ------------------------------------------------------------------

    def _sample_opponent(self) -> Optional[Any]:
        """Sample one opponent from the pool (or None → RandomOpponent)."""
        if not self._opp_pool:
            return None
        if self._rng.random() < self.cfg.hof_sample_prob:
            idx = int(self._rng.integers(0, len(self._opp_pool)))
            return self._opp_pool[idx]
        return None

    def _build_env(self) -> PokerEnv:
        opponent = self._sample_opponent()
        pool     = [opponent] if opponent is not None else None
        from rl.poker_env import PokerEnv
        return PokerEnv(opponent_pool=pool, **self._env_kwargs)

    def _collect_rollout(self) -> List[float]:
        """
        Collect n_steps transitions into self.buffer.

        Returns list of per-episode total rewards.
        """
        cfg = self.cfg
        self.buffer.reset()
        self.agent.net.eval()

        episode_rewards: List[float] = []
        episode_reward  = 0.0
        hands_in_rollout = 0

        env = self._build_env()
        obs, _ = env.reset()

        while not self.buffer.is_full:
            action_mask = self._get_mask_from_obs(env, obs)

            action, log_prob, value = self.agent.act_with_value(obs, action_mask)
            next_obs, reward, terminated, _, info = env.step(action)

            self.buffer.add(
                obs         = obs,
                action      = action,
                reward      = float(reward),
                done        = terminated,
                value       = value,
                log_prob    = log_prob,
                action_mask = action_mask,
            )

            episode_reward += float(reward)
            obs = next_obs

            if terminated:
                episode_rewards.append(episode_reward)
                episode_reward = 0.0
                hands_in_rollout += 1
                self.total_hands += 1
                env = self._build_env()
                obs, _ = env.reset()

                if self.total_hands >= cfg.total_hands:
                    break

        # Bootstrap last value
        last_value = self.agent.get_value(obs) if not terminated else 0.0
        self.buffer.compute_returns_and_advantages(last_value)

        return episode_rewards

    @staticmethod
    def _get_mask_from_obs(env: PokerEnv, obs: np.ndarray) -> np.ndarray:
        """Extract current action mask from env (after last step)."""
        from rl.poker_env import get_abstract_action_mask
        game   = env._game
        if game is None or env._is_done():
            return np.ones(6, dtype=np.float32)
        return get_abstract_action_mask(game, env._agent_id)

    # ------------------------------------------------------------------
    # PPO update step
    # ------------------------------------------------------------------

    def _ppo_update(self) -> dict:
        """Run n_epochs of PPO on the stored rollout. Returns stats dict."""
        cfg = self.cfg
        self.agent.net.train()

        total_policy_loss = 0.0
        total_value_loss  = 0.0
        total_entropy     = 0.0
        total_kl          = 0.0
        total_clip_frac   = 0.0
        n_batches         = 0

        for _ in range(cfg.n_epochs):
            for batch in self.buffer.get_batches(cfg.batch_size):
                obs_b, act_b, old_lp_b, adv_b, ret_b, mask_b = batch

                # Forward pass
                log_probs, values, entropy = self.agent.net.evaluate_actions(
                    obs_b, act_b, mask_b
                )
                values = values.squeeze(-1)

                # Ratio for PPO clip
                ratio       = torch.exp(log_probs - old_lp_b)
                clip_ratio  = torch.clamp(ratio, 1 - cfg.clip_range, 1 + cfg.clip_range)
                policy_loss = -torch.min(ratio * adv_b, clip_ratio * adv_b).mean()

                # Value loss (MSE with optional clipping)
                value_loss = F.mse_loss(values, ret_b)

                # Entropy bonus
                entropy_loss = -entropy.mean()

                loss = (
                    policy_loss
                    + cfg.vf_coef * value_loss
                    + cfg.ent_coef * entropy_loss
                )

                self.optimizer.zero_grad()
                loss.backward()
                torch.nn.utils.clip_grad_norm_(
                    self.agent.net.parameters(), cfg.max_grad_norm
                )
                self.optimizer.step()

                # Accumulate stats
                with torch.no_grad():
                    approx_kl  = ((ratio - 1) - torch.log(ratio)).mean().item()
                    clip_frac  = ((ratio - 1).abs() > cfg.clip_range).float().mean().item()

                total_policy_loss += policy_loss.item()
                total_value_loss  += value_loss.item()
                total_entropy     += entropy.mean().item()
                total_kl          += approx_kl
                total_clip_frac   += clip_frac
                n_batches         += 1

                # Early stop on KL divergence
                if cfg.target_kl is not None and approx_kl > cfg.target_kl:
                    break

        n = max(n_batches, 1)
        return {
            "policy_loss":   total_policy_loss / n,
            "value_loss":    total_value_loss  / n,
            "entropy":       total_entropy     / n,
            "approx_kl":     total_kl          / n,
            "clip_fraction": total_clip_frac   / n,
        }

    # ------------------------------------------------------------------
    # Evaluation hook
    # ------------------------------------------------------------------

    def _run_eval(self) -> None:
        """Evaluate current agent vs opponent pool and print results."""
        from rl.eval.evaluator import evaluate_vs_pool

        self.agent.net.eval()
        opponents = self._opp_pool if self._opp_pool else None
        result    = evaluate_vs_pool(
            agent          = self.agent,
            opponents      = opponents,
            num_hands      = 500,
            cfg            = self.cfg,
        )
        if self.cfg.verbose:
            print(
                f"  [eval @{self.update_cycle}] "
                f"win%={result['win_pct']:.1f}  "
                f"BB/100={result['bb_per_100']:.2f}"
            )

    # ------------------------------------------------------------------
    # Checkpointing
    # ------------------------------------------------------------------

    def _save_checkpoint(self, label: str = "") -> None:
        tag  = label or f"step{self.update_cycle}"
        path = os.path.join(self.cfg.checkpoint_dir, f"ppo_{tag}.pt")
        self.agent.save(path)
        if self.cfg.verbose >= 2:
            print(f"  [ckpt] saved → {path}")

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------

    def _init_log(self) -> None:
        with open(self._log_path, "w", newline="") as f:
            csv.DictWriter(f, fieldnames=self._log_fields).writeheader()

    def _write_log(self, stats: dict, mean_reward: float) -> None:
        row = {
            "update":        self.update_cycle,
            "total_hands":   self.total_hands,
            "policy_loss":   f"{stats['policy_loss']:.6f}",
            "value_loss":    f"{stats['value_loss']:.6f}",
            "entropy":       f"{stats['entropy']:.6f}",
            "approx_kl":     f"{stats['approx_kl']:.6f}",
            "clip_fraction": f"{stats['clip_fraction']:.4f}",
            "mean_reward":   f"{mean_reward:.4f}",
            "lr":            f"{self._current_lr:.2e}",
            "elapsed_s":     f"{time.time() - self._start_time:.1f}",
        }
        with open(self._log_path, "a", newline="") as f:
            csv.DictWriter(f, fieldnames=self._log_fields).writerow(row)
