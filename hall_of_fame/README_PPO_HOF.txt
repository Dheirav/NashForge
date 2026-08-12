# PPO Hall-of-Fame Directory

This directory was created to ensure PPO training can sample strong evolution agents as opponents.

## How to use
- All `.npy` files from `hall_of_fame/champions/` and `hall_of_fame/archived/` were copied here.
- Set `--hof-dir hall_of_fame/ppo_hu` when running PPO training or evaluation.
- This ensures PPO learns against a diverse pool of strong agents, not just random.

## Why?
- If `--hof-dir` is empty or missing `.npy` files, PPO will only train against random opponents, which is not challenging and leads to poor learning.
- With this fix, PPO can learn to beat the best evolved agents.
