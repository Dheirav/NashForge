#!/usr/bin/env python3
"""
Cross-paradigm tournament runner.

Compares PPO checkpoints against existing evolution checkpoints and
random/heuristic baselines in a round-robin tournament.

Usage
-----
# PPO vs all HoF agents (heads-up):
python run_rl_tournament.py \\
    --ppo-checkpoint checkpoints/ppo_hu/ppo_final.pt \\
    --hof-dir hall_of_fame/batch5_hu \\
    --mode hu

# Full comparison including random baseline:
python run_rl_tournament.py \\
    --ppo-checkpoint checkpoints/ppo_hu/ppo_final.pt \\
    --evo-checkpoints checkpoints/deep_p12_m7_h500_s0.05_seeded_hof3_g200/best_genome_g200.npy \\
    --mode hu \\
    --num-hands 1000

# Dry-run:
python run_rl_tournament.py --dry-run
"""

import argparse
import glob
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rl import run_tournament, PPOAgent, PPOConfig
from rl.agents import RandomOpponent, EvolutionOpponent


# ---------------------------------------------------------------------------

def load_evo_agent(npy_path: str):
    """Load an evolution .npy checkpoint as a game-compatible agent."""
    import numpy as np
    from training.policy_network import PolicyNetwork
    from training.config import NetworkConfig
    from training.self_play import AgentPlayer

    weights = np.load(npy_path)
    net_cfg = NetworkConfig()
    net     = PolicyNetwork(net_cfg)
    net.set_weights(weights)
    return AgentPlayer(net)


def collect_evo_agents(dirs: list, max_per_dir: int = 3) -> dict:
    """Load up to max_per_dir evolution agents per directory."""
    agents = {}
    for d in dirs:
        # Try best_genome patterns
        patterns = [
            os.path.join(d, "best_genome_g*.npy"),
            os.path.join(d, "best_*.npy"),
            os.path.join(d, "genome_*.npy"),
        ]
        found = []
        for pat in patterns:
            found += sorted(glob.glob(pat))
        if not found:
            continue
        # Take the last N (highest generation)
        for path in found[-max_per_dir:]:
            tag   = os.path.basename(os.path.dirname(path))
            fname = os.path.splitext(os.path.basename(path))[0]
            name  = f"{tag}/{fname}"
            try:
                agents[name] = load_evo_agent(path)
            except Exception as e:
                print(f"  [warn] could not load {path}: {e}")
    return agents


# ---------------------------------------------------------------------------

def main():
    p = argparse.ArgumentParser(
        description="Cross-paradigm tournament: PPO vs evolution agents.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--ppo-checkpoint", type=str, default=None,
                   help="Path to PPO .pt checkpoint.")
    p.add_argument("--ppo-device",     type=str, default="cpu")
    p.add_argument("--evo-checkpoints", nargs="*", default=[],
                   help="One or more .npy evolution checkpoint files.")
    p.add_argument("--hof-dir",  type=str, default=None,
                   help="Hall-of-fame directory; loads all .npy files.")
    p.add_argument("--evo-dirs", nargs="*", default=[],
                   help="Checkpoint subdirectories to scan for .npy files.")
    p.add_argument("--mode",     choices=["hu", "mt"], default="hu")
    p.add_argument("--num-hands", type=int, default=500)
    p.add_argument("--seed",      type=int, default=42)
    p.add_argument("--output-dir", type=str, default="tournament_reports/RL")
    p.add_argument("--dry-run",  action="store_true")
    args = p.parse_args()

    agents = {}

    # ── PPO agent ─────────────────────────────────────────────────────
    if args.ppo_checkpoint:
        try:
            ppo_agent = PPOAgent.from_checkpoint(args.ppo_checkpoint, device=args.ppo_device)
            agents["ppo_agent"] = ppo_agent
            print(f"[load] PPO checkpoint: {args.ppo_checkpoint}")
        except Exception as e:
            print(f"[warn] Could not load PPO checkpoint: {e}")

    # ── Evolution agents: explicit files ─────────────────────────────
    for path in args.evo_checkpoints:
        tag = os.path.splitext(os.path.basename(path))[0]
        try:
            agents[f"evo_{tag}"] = load_evo_agent(path)
            print(f"[load] evo agent: {path}")
        except Exception as e:
            print(f"[warn] {path}: {e}")

    # ── Evolution agents: HoF directory ──────────────────────────────
    if args.hof_dir:
        hof_agents = collect_evo_agents([args.hof_dir], max_per_dir=5)
        agents.update(hof_agents)
        print(f"[load] HoF dir: {args.hof_dir} → {len(hof_agents)} agents")

    # ── Evolution agents: scanned directories ────────────────────────
    if args.evo_dirs:
        dir_agents = collect_evo_agents(args.evo_dirs, max_per_dir=2)
        agents.update(dir_agents)
        print(f"[load] Scanned dirs → {len(dir_agents)} agents")

    # ── Random baseline ───────────────────────────────────────────────
    agents["random_baseline"] = RandomOpponent()

    print(f"\n[tournament] {len(agents)} agents registered:")
    for name in agents:
        print(f"  {name}")

    if args.dry_run:
        print("\n[dry-run] Exiting without running tournament.")
        return

    if len(agents) < 2:
        print("[error] Need at least 2 agents to run a tournament.")
        sys.exit(1)

    # ── Run tournament ────────────────────────────────────────────────
    num_players = 2 if args.mode == "hu" else 6

    results = run_tournament(
        agents      = agents,
        num_hands   = args.num_hands,
        num_players = num_players,
        seed        = args.seed,
        verbose     = True,
    )

    # ── Save results ──────────────────────────────────────────────────
    os.makedirs(args.output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path  = os.path.join(args.output_dir, f"tournament_{timestamp}.json")

    report = {
        "timestamp":  timestamp,
        "mode":       args.mode,
        "num_hands":  args.num_hands,
        "num_agents": len(agents),
        "leaderboard": results,
    }
    with open(out_path, "w") as f:
        json.dump(report, f, indent=2)

    print(f"\n[saved] {out_path}")


if __name__ == "__main__":
    main()
