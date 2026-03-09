# RL Module — Plug-and-Play Reinforcement Learning for PokerBot

> **Design goal**: sit completely *beside* the existing `training/` evolutionary system.  
> Zero engine changes. Zero training/ changes. Just add `rl/` and run.

---

## Directory Structure

```
rl/
├── __init__.py                  # Public API re-exports
├── base_agent.py                # Abstract interface all RL agents implement
├── poker_env.py                 # Custom Gym-style poker environment
│
├── agents/
│   └── __init__.py              # RandomOpponent · CallOpponent · RaiseOpponent · EvolutionOpponent
│
├── networks/
│   ├── __init__.py
│   └── policy_value_net.py      # PyTorch Actor-Critic network (shared trunk + actor/critic heads)
│
├── ppo/
│   ├── __init__.py
│   ├── config.py                # PPOConfig dataclass (all hyperparameters + JSON I/O)
│   ├── buffer.py                # Pre-allocated rollout buffer + GAE computation
│   ├── agent.py                 # PPOAgent (implements BaseRLAgent)
│   └── trainer.py               # PPOTrainer (full training loop)
│
└── eval/
    ├── __init__.py
    └── evaluator.py             # evaluate_vs_pool() · run_tournament()
```

Runner scripts at repo root:
- `run_ppo_training.py` — train / evaluate a PPO agent from CLI
- `run_rl_tournament.py` — cross-paradigm tournament (PPO vs evolution vs random)

---

## Quick Start

### 1. Train a heads-up PPO agent

```bash
# Default config (500k hands, 17→[128,128]→6 network, CPU)
python run_ppo_training.py --mode hu

# Against Hall-of-Fame evolution opponents
python run_ppo_training.py --mode hu \
    --hof-dir hall_of_fame/deep_p2_... \
    --total-hands 1000000 \
    --checkpoint-dir checkpoints/ppo_hu_v1
```

### 2. Evaluate a checkpoint

```bash
python run_ppo_training.py \
    --eval-only \
    --checkpoint checkpoints/ppo_hu_v1/ppo_final.pt \
    --hof-dir hall_of_fame/deep_p2_...
```

### 3. Cross-paradigm tournament (PPO vs evolution)

```bash
python run_rl_tournament.py \
    --ppo-checkpoint checkpoints/ppo_hu_v1/ppo_final.pt \
    --hof-dir hall_of_fame/deep_p2_... \
    --mode hu \
    --num-hands 1000
```

### 4. Use in Python

```python
from rl import PPOConfig, PPOTrainer, PPOAgent

# Build config
cfg = PPOConfig.heads_up_default()
cfg.hof_dir = "hall_of_fame/batch5_hu"
cfg.total_hands = 500_000

# Train
trainer = PPOTrainer(cfg)
agent   = trainer.train()

# Evaluate
from rl import evaluate_vs_pool
results = evaluate_vs_pool(agent, opponents=None, num_hands=2000)
print(f"win%={results['win_pct']:.1f}  BB/100={results['bb_per_100']:+.2f}")

# Save / load
agent.save("my_ppo_agent.pt")
loaded = PPOAgent.from_checkpoint("my_ppo_agent.pt")
```

---

## Key Components

### `BaseRLAgent`

```
rl/base_agent.py
```

All RL agents implement this two-method interface:

| Method | Signature | Description |
|--------|-----------|-------------|
| `act()` | `(obs, action_mask, deterministic) → int` | Pick abstract action index |
| `get_action()` | `(game, player_id) → int` | Drop-in for `AgentPlayer.get_action()` |

Implementing `BaseRLAgent` makes any agent instantly usable in:
- `PokerEnv` opponent pool
- `evaluate_vs_pool()`
- `run_tournament()`
- Existing evolution evaluator / tournament harness

---

### `PokerEnv`

```
rl/poker_env.py
```

Custom gym-style environment (no `gymnasium` dependency).

| Feature | Detail |
|---------|--------|
| Observation | 17-float feature vector from `engine.get_state_vector()` |
| Action space | Discrete(6): fold · check/call · raise½ · raisePot · raise2x · all-in |
| Reward | `chip_delta / big_blind` (BB units), terminal per hand |
| Shaped reward | Optional `RewardShaper` for dense immediate signals |
| Opponent pool | Any list of `.get_action(game,pid)` objects |

**Reward shapers** (pluggable, zero engine changes):
- `RewardShaper` — default (zero per-step; pure terminal reward)
- `AggressionShaper` — +0.05BB bonus for raises, -0.03BB for bad calls

```python
from rl.poker_env import PokerEnv, AggressionShaper
env = PokerEnv(num_players=2, reward_shaper=AggressionShaper())
```

**Action mask translation**: the engine `get_action_mask()` returns 5 slots `[fold, check, call, raise, all-in]`. `PokerEnv` translates this to the 6-slot abstract space automatically via `get_abstract_action_mask()`.

---

### `ActorCriticNet`

```
rl/networks/policy_value_net.py
```

Shared-trunk PyTorch actor-critic:

```
Input (17) → Linear → LayerNorm → ReLU    ┐
           → Linear → LayerNorm → ReLU    ┘ shared trunk
                                           ↓
                     ┌─────────────────────┤
                     │                     │
              Actor head              Critic head
           Linear→logits(6)           Linear→value(1)
```

| Feature | Detail |
|---------|--------|
| Init | Orthogonal weights (PPO best practice) |
| Masking | Illegal actions set to -1e8 before softmax |
| Save/load | `net.save(path)` / `ActorCriticNet.load(path)` |

---

### `PPOConfig`

```
rl/ppo/config.py
```

All hyperparameters in one dataclass. Serialises to/from JSON.

```python
cfg = PPOConfig.heads_up_default()   # sensible HU defaults
cfg = PPOConfig.multitable_default() # sensible 6-max defaults

cfg.to_json("run_config.json")
cfg = PPOConfig.from_json("run_config.json")
```

Key parameters:

| Parameter | Default (HU) | Description |
|-----------|-------------|-------------|
| `total_hands` | 500,000 | Training budget |
| `n_steps` | 512 | Rollout length before each update |
| `n_epochs` | 4 | Gradient passes per rollout |
| `batch_size` | 64 | Mini-batch size |
| `lr` | 3e-4 | Adam learning rate |
| `clip_range` | 0.2 | PPO clip ε |
| `ent_coef` | 0.01 | Entropy bonus (exploration) |
| `gamma` | 0.999 | Discount (high = good for sparse terminal reward) |
| `hof_dir` | None | Hall-of-fame directory for opponent sampling |
| `hof_sample_prob` | 0.5 | Probability of using HoF over random opponent |

---

### `PPOTrainer`

```
rl/ppo/trainer.py
```

Full PPO loop:
1. `_collect_rollout()` — run `n_steps` env steps, store in `RolloutBuffer`
2. `buffer.compute_returns_and_advantages()` — GAE(λ) 
3. `_ppo_update()` — `n_epochs × n_steps/batch_size` gradient updates
4. Repeat until `total_hands` reached; evaluate every `eval_every` cycles

Outputs:
- `logs/ppo_*/training_log.csv` — per-update stats
- `checkpoints/ppo_*/ppo_stepN.pt` — periodic checkpoints
- `checkpoints/ppo_*/ppo_final.pt` — final model
- `checkpoints/ppo_*/config.json` — run configuration

---

### Evaluator

```
rl/eval/evaluator.py
```

Two functions:

| Function | Use case |
|----------|----------|
| `evaluate_vs_pool(agent, opponents, num_hands)` | Measure BB/100 + win% of one agent |
| `run_tournament(agents_dict, num_hands)` | Round-robin leaderboard over any mix of agents |

Both work with any object that has `.get_action(game, player_id) -> int`:
- `PPOAgent`
- `AgentPlayer` (evolution)
- `RandomOpponent`, `CallOpponent`, `RaiseOpponent`

---

## Extending the Module (Adding New Algorithms)

The module is designed so adding DQN, A2C, or CFR requires zero changes to existing code:

### 1. Add a new algorithm directory

```
rl/dqn/
├── __init__.py
├── config.py     # DQNConfig dataclass
├── agent.py      # DQNAgent(BaseRLAgent)  ← implements act() and get_action()
└── trainer.py    # DQNTrainer
```

### 2. Implement `BaseRLAgent`

```python
from rl.base_agent import BaseRLAgent

class DQNAgent(BaseRLAgent):
    def act(self, obs, action_mask, deterministic=False) -> int:
        ...   # your Q-network logic here
```

### 3. Use the existing env and evaluator unchanged

```python
from rl.poker_env import PokerEnv
from rl.eval.evaluator import evaluate_vs_pool

env = PokerEnv(opponent_pool=[...])
result = evaluate_vs_pool(my_dqn_agent, opponents=[...])
```

---

## What Was NOT Changed

| Component | Status |
|-----------|--------|
| `engine/` | **Unchanged** |
| `training/` (evolution) | **Unchanged** |
| `agents/` | **Unchanged** |
| Existing tournament scripts | **Unchanged** |
| Existing checkpoints / HoF | **Unchanged** |

The `rl/` module is purely additive.

---

## Training Signal Notes

`features[15]` was fixed (B6 work) to reflect `facing_raise` (0/1 binary) rather than a hardcoded 0.5 constant. PPO benefits immediately from this because it trains weights from scratch via gradient descent — no "compensated weights" artifact that seeded evolution agents suffered from.

The recommended training sequence:
1. **PPO heads-up** vs HoF opponents — target >83% win rate vs B5 HU champion
2. **PPO 6-max** — extend to multitable after HU convergence
3. **Optional**: Add `AggressionShaper` to accelerate aggression learning
4. **Optional**: Integrate CFR solving as a separate `rl/cfr/` module
