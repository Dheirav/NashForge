"""
Evaluate a trained genome against the baseline agents.

This script was previously a stub: `evaluate_vs_baseline()` returned
`{'heuristic': 0, 'random': 0}` unconditionally with a comment saying the game
logic still had to be written, and `main()` crashed before even reaching it by
calling a `TrainingConfig.from_dict` that does not exist. It is now a working
evaluation.

Usage
-----
    python scripts/evaluation/eval_baseline.py GENOME.npy
    python scripts/evaluation/eval_baseline.py GENOME.npy --hands 5000 --players 6
    python scripts/evaluation/eval_baseline.py GENOME.npy --arch 17 64 32 6

Results are reported in BB/100 — the hero's own chip result, in big blinds, per
100 hands — with the standard error, because a single number over a few hundred
hands of poker is not a measurement.
"""
import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from agents.heuristic_agent import HeuristicAgent
from agents.random_agent import RandomAgent
from engine import PokerGame
from engine.features import FeatureCache, get_abstract_action_mask
from training.config import NetworkConfig
from training.fitness import (abstract_action_to_engine_action, apply_action_or_fold,
                              chip_deltas, finish_hand, hand_start_stacks,
                              ILLEGAL_ACTIONS)
from training.policy_network import PolicyNetwork


class GenomeAgent:
    """Wraps a trained genome so it plays through the same path as training."""

    def __init__(self, network: PolicyNetwork, temperature: float = 1.0):
        self.network = network
        self.temperature = temperature
        self._cache = None
        self._cache_seat = None

    def begin_hand(self, game, seat):
        self._cache = FeatureCache(game, seat)
        self._cache_seat = seat

    def act(self, game, seat, rng):
        features = self._cache.get_features(game)
        mask = get_abstract_action_mask(game, seat)
        idx = self.network.select_action(features, mask, rng, self.temperature)
        return abstract_action_to_engine_action(idx, game, seat)


class BaselineAgent:
    """Wraps RandomAgent / HeuristicAgent, which choose engine actions directly."""

    def __init__(self, inner):
        self.inner = inner

    def begin_hand(self, game, seat):
        pass

    def act(self, game, seat, rng):
        return self.inner.select_action(game, seat)


def play_session(hero, opponent, hands, num_players, rng,
                 starting_stack=1000, small_blind=5, big_blind=10):
    """
    Play `hands` hands with the hero in seat 0 and copies of `opponent`
    elsewhere, rotating the hero's seat so position is not a confound.

    Returns the per-hand result in big blinds.
    """
    per_hand = []
    for hand_idx in range(hands):
        game = PokerGame(
            player_stacks=[starting_stack] * num_players,
            small_blind=small_blind, big_blind=big_blind,
            seed=int(rng.integers(0, 2 ** 31)),
        )
        hero_seat = hand_idx % num_players
        seats = {s: (hero if s == hero_seat else opponent) for s in range(num_players)}
        for seat, agent in seats.items():
            agent.begin_hand(game, seat)

        start = hand_start_stacks(game)
        guard = 0
        while not game.is_hand_over() and guard < 200:
            seat = game.state.current_player
            if seat is None:
                break
            player = game.players[seat]
            if player.has_folded or player.is_all_in:
                break
            if not apply_action_or_fold(game, seat, seats[seat].act(game, seat, rng)):
                break
            guard += 1

        finish_hand(game)
        per_hand.append(chip_deltas(game, start)[hero_seat] / big_blind)

    return np.array(per_hand)


def summarise(name, per_hand):
    n = len(per_hand)
    bb100 = per_hand.mean() * 100
    stderr = (per_hand.std(ddof=1) / np.sqrt(n)) * 100 if n > 1 else float('nan')
    return {
        'opponent': name,
        'hands': n,
        'bb_per_100': round(float(bb100), 2),
        'stderr_bb_per_100': round(float(stderr), 2),
        'ci95_low': round(float(bb100 - 1.96 * stderr), 2),
        'ci95_high': round(float(bb100 + 1.96 * stderr), 2),
    }


def parse_args():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('genome', help='path to a .npy genome file')
    p.add_argument('--arch', type=int, nargs='+', default=[17, 64, 32, 6],
                   help='layer sizes, e.g. 17 64 32 6')
    p.add_argument('--hands', type=int, default=2000, help='hands per opponent')
    p.add_argument('--players', type=int, default=2, help='table size (2-6)')
    p.add_argument('--seed', type=int, default=42)
    p.add_argument('--temperature', type=float, default=1.0)
    p.add_argument('--output', help='optional path to write JSON results')
    return p.parse_args()


def main():
    args = parse_args()

    weights = np.load(args.genome)
    network = PolicyNetwork(NetworkConfig(input_size=args.arch[0],
                                          hidden_sizes=args.arch[1:-1],
                                          output_size=args.arch[-1]))
    if weights.size != network.genome_size:
        raise SystemExit(
            f"genome has {weights.size} parameters but architecture {args.arch} "
            f"needs {network.genome_size}. Pass the right --arch."
        )
    network.set_weights_from_genome(weights)

    ILLEGAL_ACTIONS.reset()
    hero = GenomeAgent(network, args.temperature)
    opponents = [('random', BaselineAgent(RandomAgent(seed=args.seed))),
                 ('heuristic', BaselineAgent(HeuristicAgent()))]

    print(f"Genome:  {args.genome}")
    print(f"Setting: {args.players}-handed, {args.hands} hands per opponent, seed {args.seed}\n")
    print(f"{'opponent':<12}{'BB/100':>10}{'std err':>10}{'95% CI':>20}")

    results = []
    for name, opponent in opponents:
        rng = np.random.default_rng(args.seed)
        per_hand = play_session(hero, opponent, args.hands, args.players, rng)
        row = summarise(name, per_hand)
        results.append(row)
        ci = f"[{row['ci95_low']:+.1f}, {row['ci95_high']:+.1f}]"
        print(f"{name:<12}{row['bb_per_100']:>+10.2f}{row['stderr_bb_per_100']:>10.2f}{ci:>20}")

    if ILLEGAL_ACTIONS.total:
        print(f"\nWarning: {ILLEGAL_ACTIONS} — results may be affected.")

    print("\nA 95% interval spanning zero means this run cannot tell the agent "
          "apart from break-even against that opponent.")

    if args.output:
        with open(args.output, 'w') as f:
            json.dump({'genome': args.genome, 'players': args.players,
                       'hands': args.hands, 'seed': args.seed,
                       'results': results}, f, indent=2)
        print(f"Wrote {args.output}")


if __name__ == '__main__':
    main()
