"""
Is the Phase 4 intransitivity real, and if so where does it come from?

Two candidate explanations are already dead. `check_instrument.py` showed the
two families' rows are on one instrument, bit-for-bit. `check_raise_cap.py`
showed that lifting the one-raise-per-street cap widens the gap rather than
closing it. What is left is that the intransitivity is genuine, and this asks
the two questions that would establish it.

1. The edge nobody measured
---------------------------
Phase 4's tournament graph has a hole in it. CFR against PPO is measured, CFR
against evolutionary search is measured, and **PPO against evolutionary search
never was** — both learned families were only ever scored against the solver and
the two baselines, never against each other.

That edge is the test. PPO draws level with the solver, and the solver beats the
evolved genome by 370 BB/100. If strength were a scalar, PPO should beat it by
about the same. If PPO beats it by substantially less, the ordering is not a
ordering, and the non-transitivity shows up on an edge that was never part of the
observation that raised the question.

2. Where the gap against a calling station comes from
------------------------------------------------------
The widest gap in Phase 4 is against always-call: the solver takes +722.9 and PPO
+293.5, while the two are level with each other. A station that never folds can
only be beaten by betting for value, so the natural hypothesis is that the two
agents bet at different rates against it.

This counts what each actually does. PPO trained by self-play against snapshots
of itself and never met a calling station in training; the solver was fitted for
a game where the opponent folds sometimes. If PPO checks and calls where the
solver raises, that is the mechanism, and it is a fact about what self-play
optimises rather than a fact about poker.

Usage
-----
    venv/bin/python scripts/diagnostics/check_intransitivity.py
    venv/bin/python scripts/diagnostics/check_intransitivity.py --hands 4000
"""
import argparse
import glob
import os
import pickle
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import numpy as np
import torch

torch.set_num_threads(1)

from evaluation import always_call_agent, benchmark, cfr_agent
from rl.ppo.agent import PPOAgent
from train_ppo import ppo_as_benchmark_agent
from training.config import (EvolutionConfig, FitnessConfig, NetworkConfig,
                             TrainingConfig)
from training.evolution import EvolutionTrainer  # noqa: F401  (config parity)
from training.policy_network import PolicyNetwork

EVAL_SEED = 20260820
HANDS = 40_000
RUNG = 2_000_000                     # the rung that draws level with the solver
STRATEGY = os.path.join(ROOT, "results", "cfr", "nolimit_strategy.pkl")
PPO_SCRATCH = os.path.expanduser("~/pokerbot-scratch/phase3")
PHASE2 = sorted(glob.glob(os.path.expanduser(
    "~/pokerbot-scratch/phase2/phase2/runs/run_*")))

ACTIONS = ["fold", "check/call", "raise ½", "raise pot", "raise 2×", "all-in"]


def genome_agent(weights, network_config, rng):
    """Phase 2's agent, built exactly as `endpoint_test.py` builds it."""
    from engine.features import FeatureCache
    net = PolicyNetwork(network_config)
    net.set_weights_from_genome(weights)
    caches = {}

    def act(game, player_id, mask, history):
        key = (id(game), player_id)
        if key not in caches:
            caches.clear()
            caches[key] = FeatureCache(game, player_id)
        return int(net.select_action(caches[key].get_features(game),
                                     np.asarray(mask), rng))
    return act


def evolved():
    if not PHASE2:
        raise SystemExit("no Phase 2 run under ~/pokerbot-scratch/phase2")
    weights = np.load(os.path.join(PHASE2[-1], "best_genome.npy"))
    config = TrainingConfig(
        network=NetworkConfig(hidden_sizes=[64, 32]),
        evolution=EvolutionConfig(population_size=30, mutation_sigma=0.1),
        fitness=FitnessConfig(num_players=2, starting_stack=200,
                              small_blind=1, big_blind=2, num_workers=1),
        num_generations=1, seed=0, experiment_name="intransitivity",
        output_dir="/tmp/intransitivity")
    return genome_agent(weights, config.network, np.random.default_rng(4))


def ppo(seed):
    path = os.path.join(PPO_SCRATCH, f"seed{seed}", f"ppo_rung{RUNG}.pt")
    return ppo_as_benchmark_agent(PPOAgent.from_checkpoint(path, device="cpu"))


def solver():
    with open(STRATEGY, "rb") as handle:
        saved = pickle.load(handle)
    return cfr_agent(saved["strategy"], saved["abstraction"],
                     np.random.default_rng(4), raise_cap=1)


def counted(agent, tally):
    """Wrap an agent so what it actually chose can be counted."""
    def act(game, player_id, mask, history):
        choice = agent(game, player_id, mask, history)
        tally[choice] += 1
        return choice
    return act


def missing_edge(hands, seeds):
    print("1. The edge the tournament graph was missing\n")
    print(f"   PPO (rung {RUNG:,}) against the evolved genome, "
          f"{hands:,} hands each seed")
    scores = []
    for seed in seeds:
        torch.manual_seed(EVAL_SEED)
        result = benchmark(ppo(seed), evolved(), "evolution", hands=hands,
                           seed=EVAL_SEED)
        scores.append(result.bb_per_100)
        print(f"     seed {seed}: {result.bb_per_100:+9.1f} BB/100", flush=True)

    mean = float(np.mean(scores))
    spread = max(scores) - min(scores)
    print(f"\n   mean {mean:+.1f} BB/100, spread {spread:.1f}\n")
    return mean, spread


def report_graph(ppo_vs_evo):
    """
    The three edges together, and what transitivity would have required.

    The solver beats the evolved genome by 370.1. PPO is level with the solver.
    A scalar notion of strength therefore predicts PPO beats it by about 370 too;
    the size of the shortfall is the size of the problem with that notion.
    """
    cfr_vs_ppo, cfr_vs_evo = 10.4, 370.1
    print("   the graph, in BB/100 to the first named\n")
    print(f"     CFR      vs PPO         {cfr_vs_ppo:+9.1f}   (level)")
    print(f"     CFR      vs evolution   {cfr_vs_evo:+9.1f}")
    print(f"     PPO      vs evolution   {ppo_vs_evo:+9.1f}   <- measured here")
    shortfall = cfr_vs_evo - ppo_vs_evo
    print(f"\n   transitivity predicted about {cfr_vs_evo - cfr_vs_ppo:+.1f} "
          f"for the third edge.")
    print(f"   Shortfall: {shortfall:+.1f} BB/100.")
    if ppo_vs_evo < 0:
        print("   PPO LOSES to the genome the solver crushes: a genuine cycle.")
    elif shortfall > 100:
        print("   PPO beats it by far less than the solver does, on an edge that")
        print("   was no part of the observation that raised the question.")
    else:
        print("   The edge is roughly where a scalar strength would put it, so")
        print("   the intransitivity does not extend to this pair.")


def aggression(hands):
    """What each agent actually does against a station that never folds."""
    print("\n2. What each agent does against always-call\n")
    rows = []
    for name, make in (("CFR solver", solver), ("PPO 2M", lambda: ppo(0))):
        tally = Counter()
        torch.manual_seed(EVAL_SEED)
        result = benchmark(counted(make(), tally), always_call_agent(),
                           "always-call", hands=hands, seed=EVAL_SEED)
        total = sum(tally.values()) or 1
        raises = sum(tally[i] for i in (2, 3, 4, 5))
        rows.append((name, result.bb_per_100, raises / total, tally, total))
        print(f"   {name:<12} {result.bb_per_100:+8.1f} BB/100   "
              f"raise rate {raises / total:6.1%}   ({total:,} decisions)",
              flush=True)

    print(f"\n   {'':12} " + "".join(f"{a:>12}" for a in ACTIONS))
    for name, _, _, tally, total in rows:
        print(f"   {name:<12} " +
              "".join(f"{tally[i] / total:>11.1%}" for i in range(6)))

    (_, s_score, s_rate, _, _), (_, p_score, p_rate, _, _) = rows
    print(f"\n   The solver raises on {s_rate:.1%} of its decisions and takes "
          f"{s_score:+.0f};")
    print(f"   PPO raises on {p_rate:.1%} and takes {p_score:+.0f}.")
    if s_rate > p_rate * 1.25:
        print("   PPO is the less aggressive of the two against a station it")
        print("   cannot fold out, which is the mechanism the gap needed.")
    elif p_rate > s_rate * 1.25:
        print("   PPO is the MORE aggressive of the two and still takes less,")
        print("   so bet frequency is not the explanation -- sizing or spot")
        print("   selection is.")
    else:
        print("   The two bet at similar rates, so frequency is not the")
        print("   explanation and the difference is in which spots or sizes.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hands", type=int, default=HANDS)
    parser.add_argument("--seeds", type=int, nargs="+", default=[0, 1, 2])
    args = parser.parse_args()

    print(f"{args.hands:,} hands per matchup, seed {EVAL_SEED}\n")
    mean, _ = missing_edge(args.hands, args.seeds)
    report_graph(mean)
    aggression(args.hands)


if __name__ == "__main__":
    main()
