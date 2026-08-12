#!/usr/bin/env python3
"""
Visualize agent behavior: action frequencies, positional stats, and more.
Usage:
    python scripts/visualize_agent_behavior.py --genome checkpoints/runs/Phase1/best_genome.npy --arch "17 128 64 6" --hands 1000 --players 2
"""
import argparse
import numpy as np
import matplotlib.pyplot as plt
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from training.policy_network import PolicyNetwork
from engine import PokerGame
from engine.cards import Deck
from engine.state import PlayerState, GameState
from engine.actions import Action

def parse_args():
    parser = argparse.ArgumentParser(description="Visualize agent behavior")
    parser.add_argument('--genome', type=str, required=True, help='Path to .npy weights')
    parser.add_argument('--arch', type=str, required=True, help='Network architecture, e.g. "17 128 64 6"')
    parser.add_argument('--hands', type=int, default=1000, help='Number of hands to simulate')
    parser.add_argument('--players', type=int, default=2, help='Number of players at the table')
    parser.add_argument('--seed', type=int, default=42, help='Random seed')
    return parser.parse_args()

def main():
    args = parse_args()
    arch = [int(x) for x in args.arch.strip().split()]
    from training.config import NetworkConfig
    net = PolicyNetwork(NetworkConfig(input_size=arch[0], hidden_sizes=arch[1:-1], output_size=arch[-1]))
    net.set_weights_from_genome(np.load(args.genome))
    rng = np.random.default_rng(args.seed)
    action_counts = np.zeros(arch[-1], dtype=int)
    position_counts = np.zeros(args.players, dtype=int)
    from engine.features import get_state_vector
    for hand in range(args.hands):
        stacks = [1000] * args.players
        game = PokerGame(player_stacks=stacks, small_blind=5, big_blind=10, ante=0, seed=int(rng.integers(0, 2**31)))
        for pos in range(args.players):
            features = np.array(get_state_vector(game, pos), dtype=np.float32)
            from engine.features import get_action_mask, get_abstract_action_mask
            if arch[-1] == 6:
                mask = get_abstract_action_mask(game, pos)
            else:
                mask = np.array(get_action_mask(game, pos), dtype=np.float32)
            action = net.select_action(features, mask, rng)
            action_counts[action] += 1
            position_counts[pos] += 1
    actions = ['fold', 'check/call', 'raise 0.5x', 'raise 1x', 'raise 2x', 'all-in'][:arch[-1]]
    plt.figure(figsize=(8,4))
    plt.bar(actions, action_counts)
    plt.title('Agent Action Frequencies')
    plt.xlabel('Action')
    plt.ylabel('Count')
    plt.tight_layout()
    plt.show()
    plt.figure(figsize=(8,4))
    plt.bar([f'Pos {i}' for i in range(args.players)], position_counts)
    plt.title('Hands Played by Position')
    plt.xlabel('Position')
    plt.ylabel('Count')
    plt.tight_layout()
    plt.show()

if __name__ == '__main__':
    main()
