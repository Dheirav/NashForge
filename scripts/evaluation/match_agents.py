"""
Script to pit two trained evolutionary agents against each other and compare performance.

Usage:
    python scripts/evaluation/match_agents.py --agent1 checkpoints/runs/SessionA/best_genome.npy --arch1 17 64 32 6 \
                                              --agent2 checkpoints/runs/SessionB/best_genome.npy --arch2 17 128 64 6 \
                                              --hands 5000 --players 2

- Automatically transforms genomes if architectures differ.
- Runs a head-to-head match and reports win rates and chip gains.
"""

import sys
import os
# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

import argparse
import numpy as np
from utils import genome_transform
from training.policy_network import PolicyNetwork
from engine.game import PokerGame

# Helper to parse architecture string

def parse_arch(arch_str):
    return [int(x) for x in arch_str.split()]

def load_agent(genome_path, arch):
    genome = np.load(genome_path)
    net = PolicyNetwork()
    net.layer_sizes = arch
    # Decode and set weights
    weights, biases = genome_transform.decode_genome(genome, arch)
    net.weights = weights
    net.biases = biases
    return net

def main():
    parser = argparse.ArgumentParser(description="Match two evolutionary agents.")
    parser.add_argument('--agent1', type=str, required=True, help='Path to agent 1 genome (.npy)')
    parser.add_argument('--arch1', type=str, required=True, help='Agent 1 architecture, e.g. "17 64 32 6"')
    parser.add_argument('--agent2', type=str, required=True, help='Path to agent 2 genome (.npy)')
    parser.add_argument('--arch2', type=str, required=True, help='Agent 2 architecture, e.g. "17 128 64 6"')
    parser.add_argument('--hands', type=int, default=5000, help='Number of hands to play')
    parser.add_argument('--players', type=int, default=2, help='Number of players (default 2)')
    parser.add_argument('--log', action='store_true', help='Enable match logging to file (default: off)')
    args = parser.parse_args()

    arch1 = parse_arch(args.arch1)
    arch2 = parse_arch(args.arch2)

    # Transform genomes if needed
    genome1 = np.load(args.agent1)
    genome2 = np.load(args.agent2)
    if arch1 != arch2:
        # Transform agent2 to agent1's architecture for fair match
        print("Transforming agent2 genome to agent1 architecture...")
        genome2, info = genome_transform.transform_genome(genome2, arch2, arch1)
        print(f"Agent2: {info['percent_copied']:.1f}% weights copied, {info['total_params']-info['copied_params']} newly initialized.")
        arch2 = arch1

    # Load agents
    import logging
    logging_enabled = args.log
    if logging_enabled:
        import datetime
        os.makedirs('match_logs', exist_ok=True)
        agent1_name = os.path.basename(args.agent1).replace('.npy','')
        agent2_name = os.path.basename(args.agent2).replace('.npy','')
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        log_filename = f"match_logs/{agent1_name}_vs_{agent2_name}_{timestamp}.log"
        logging.basicConfig(filename=log_filename, level=logging.INFO,
                            format='%(asctime)s %(message)s')
        print(f"Logging match to {log_filename}")
    else:
        logging.basicConfig(level=logging.CRITICAL)  # Suppress all logging output

    agent1 = load_agent(args.agent1, arch1)
    agent2 = load_agent(args.agent2, arch2)

    # Initial stacks
    stacks = [1000, 1000]
    small_blind = 5
    big_blind = 10
    agents = [agent1, agent2]
    # Do not set a fixed seed here; create the game object per hand with a new seed
    # game = PokerGame(stacks.copy(), small_blind=small_blind, big_blind=big_blind, seed=42)
    hand = 0
    log_header = f"Match: Agent1={args.agent1} vs Agent2={args.agent2} | Arch={arch1}\n"
    print(log_header.strip())
    if logging_enabled:
        logging.info(log_header.strip())
    while hand < args.hands and all(s > 0 for s in stacks):
        # Create a new PokerGame for each hand with a different seed
        import time
        hand_seed = int(time.time() * 1e6) % int(1e9) + hand  # microsecond time + hand index
        game = PokerGame(stacks.copy(), small_blind=small_blind, big_blind=big_blind, seed=hand_seed)
        rng = np.random.default_rng(hand_seed)
        hand_actions = []
        # Log hole cards at the start of the hand
        hole_cards_log = []
        for i, p in enumerate(game.players):
            cards_str = ', '.join(str(card) for card in getattr(p, 'hole_cards', []))
            hole_cards_log.append(f"Agent{i+1} hole cards: [{cards_str}]")
        community_cards_log = f"Community cards: [{', '.join(str(card) for card in getattr(game.state, 'community_cards', []))}]"
        # Play until hand is over
        while not game.is_hand_over():
            player_idx = game.state.current_player
            if player_idx is None or game.state.players[player_idx].has_folded or game.state.players[player_idx].is_all_in:
                break
            # Get state vector and action mask
            from engine.features import get_state_vector, get_abstract_action_mask
            features = np.array(get_state_vector(game, player_idx), dtype=np.float32)
            mask = get_abstract_action_mask(game, player_idx)
            n_actions = agents[player_idx].weights[-1].shape[1]  # Output size (should be 6)
            assert mask.shape[0] == n_actions, f"Mask shape {mask.shape} does not match network output {n_actions}"
            # Agent selects action
            agent = agents[player_idx]
            action_idx = agent.select_action(features, mask, rng)
            # Map action index to abstract action type (matches PolicyNetwork)
            abstract_action_types = [
                'fold',         # 0
                'check_call',   # 1
                'raise_half_pot', # 2
                'raise_pot',    # 3
                'raise_2x_pot', # 4
                'all_in',       # 5
            ]
            action_type = abstract_action_types[action_idx]
            def is_action_match(act, action_type):
                if action_type == 'check_call':
                    return act['type'] in ('check', 'call')
                elif action_type in ('raise_half_pot', 'raise_pot', 'raise_2x_pot'):
                    return act['type'] == 'raise'
                elif action_type == 'all_in':
                    return act['type'] == 'all-in'
                else:
                    return act['type'] == action_type
            legal_actions = game.get_legal_actions(player_idx)
            chosen = None
            for act in legal_actions:
                if is_action_match(act, action_type):
                    from engine.actions import Action
                    if action_type in ('raise_half_pot', 'raise_pot', 'raise_2x_pot'):
                        pot = game.state.pot.total
                        player = game.players[player_idx]
                        current_bet = game.current_bet
                        to_call = current_bet - player.bet
                        if action_type == 'raise_half_pot':
                            amount = max(game.state.big_blind, int(pot * 0.5))
                        elif action_type == 'raise_pot':
                            amount = max(game.state.big_blind, pot)
                        elif action_type == 'raise_2x_pot':
                            amount = max(game.state.big_blind, pot * 2)
                        else:
                            amount = act.get('min', act.get('amount', 0))
                        chosen = Action('raise', amount)
                        hand_actions.append(f"Agent{player_idx+1} action: raise({amount}) | Stack: {player.stack} | Pot: {pot}")
                    elif action_type == 'all_in':
                        amount = act.get('amount', player.stack)
                        chosen = Action('all-in', amount)
                        hand_actions.append(f"Agent{player_idx+1} action: all-in({amount}) | Stack: {player.stack}")
                    else:
                        if action_type == 'check_call':
                            chosen = Action(act['type'])
                            hand_actions.append(f"Agent{player_idx+1} action: {act['type']} | Stack: {game.players[player_idx].stack}")
                        else:
                            chosen = Action(action_type)
                            hand_actions.append(f"Agent{player_idx+1} action: {action_type} | Stack: {game.players[player_idx].stack}")
                    break
            if chosen is None:
                from engine.actions import Action
                chosen = Action('fold')
                hand_actions.append(f"Agent{player_idx+1} action: fold (forced) | Stack: {game.players[player_idx].stack}")
            game.apply_action(player_idx, chosen)
        # Hand is over: resolve showdown to distribute pot
        winnings = game.resolve_showdown()
        # Update stacks
        for i, p in enumerate(game.state.players):
            stacks[i] = p.stack
        # Log winner(s) and details
        not_folded = [i for i, p in enumerate(game.state.players) if not p.has_folded]
        total_chips = sum(stacks)
        # Log community cards at showdown
        community_cards_log = f"Community cards: [{', '.join(str(card) for card in getattr(game.state, 'community_cards', []))}]"
        if len(not_folded) == 1:
            winner = not_folded[0]
            log_line = f"Hand {hand+1}: Winner=Agent{winner+1}, Stacks={stacks}"
        else:
            log_line = f"Hand {hand+1}: Showdown, Stacks={stacks}"
        print(f"\n--- Hand Details ---")
        for h in hole_cards_log:
            print(h)
        print(community_cards_log)
        for a in hand_actions:
            print(a)
        print(f"Pot at showdown: {game.state.pot.total}")
        print(f"Winnings: {winnings}")
        print(f"Total chips after hand: {total_chips}")
        print(log_line)
        if logging_enabled:
            logging.info("; ".join(hole_cards_log))
            logging.info(community_cards_log)
            logging.info("; ".join(hand_actions))
            logging.info(f"Pot at showdown: {game.state.pot.total}")
            logging.info(f"Winnings: {winnings}")
            logging.info(f"Total chips after hand: {total_chips}")
            logging.info(log_line)
        hand += 1
    print(f"Final stacks: {stacks}")
    import json
    print(json.dumps({"final_stacks": stacks}))
    if logging_enabled:
        logging.info(f"Final stacks: {stacks}")
    if len(stacks) > 1:
        if stacks[0] <= 0:
            print("Agent 2 wins by elimination!")
            if logging_enabled:
                logging.info("Agent 2 wins by elimination!")
        elif stacks[1] <= 0:
            print("Agent 1 wins by elimination!")
            if logging_enabled:
                logging.info("Agent 1 wins by elimination!")
        else:
            print("No elimination. Chips after max hands.")
            if logging_enabled:
                logging.info("No elimination. Chips after max hands.")

if __name__ == "__main__":
    main()
