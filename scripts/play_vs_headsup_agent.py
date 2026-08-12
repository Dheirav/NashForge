import numpy as np
from training.policy_network import PolicyNetwork
from engine.game import PokerGame
from engine.features import get_state_vector, get_abstract_action_mask
import os

# Configuration
AGENT_GENOME_PATH = 'hall_of_fame/ppo_hu/p12_m7_h375_s0.06_g50_b4_champion.npy'
ARCH = [17, 64, 32, 6]
STARTING_STACK = 1000
SMALL_BLIND = 5
BIG_BLIND = 10

# Load agent
agent_genome = np.load(AGENT_GENOME_PATH)
from training.config import NetworkConfig
agent_net = PolicyNetwork(NetworkConfig(input_size=ARCH[0], hidden_sizes=ARCH[1:-1], output_size=ARCH[-1]))
agent_net.set_weights_from_genome(agent_genome)

# Action mapping
ACTION_NAMES = ['fold', 'check/call', 'raise 0.5x', 'raise 1x', 'raise 2x', 'all-in']


def human_action_input(legal_mask, game, current_player):
    print("Your move. Legal actions:")
    # Dynamically show 'check' or 'call' for action 1
    to_call = game.current_bet - game.players[current_player].bet
    for i, (name, legal) in enumerate(zip(ACTION_NAMES, legal_mask)):
        if legal:
            if i == 1:
                display_name = "check" if to_call == 0 else "call"
                print(f"  {i}: {display_name}")
            else:
                print(f"  {i}: {name}")
    while True:
        try:
            idx = int(input("Enter action number: "))
            if 0 <= idx < len(legal_mask) and legal_mask[idx]:
                return idx
            else:
                print("Invalid or illegal action. Try again.")
        except Exception:
            print("Invalid input. Enter a number.")

def main():
    stacks = [STARTING_STACK, STARTING_STACK]
    game = PokerGame(player_stacks=stacks, small_blind=SMALL_BLIND, big_blind=BIG_BLIND, ante=0, seed=None)
    human_pos = 0  # You are always player 0
    agent_pos = 1
    print("\nWelcome! You are Player 1. The agent is Player 2.")
    hand = 1
    while all(p.stack > 0 for p in game.players):
        print(f"\n=== Hand {hand} ===")
        game.reset_hand()
        while not game.is_hand_over():
            pos = game.state.current_player
            current_player = pos
            if pos is None or game.state.players[pos].has_folded or game.state.players[pos].is_all_in:
                break
            features = np.array(get_state_vector(game, pos), dtype=np.float32)
            mask = get_abstract_action_mask(game, pos)
            if pos == human_pos:
                print(f"Your stack: {game.players[human_pos].stack}, Agent stack: {game.players[agent_pos].stack}")
                print(f"Pot: {game.state.pot.total}")
                print(f"Your cards: {[str(card) for card in game.players[human_pos].hole_cards]}")
                print(f"Community cards: {[str(card) for card in game.state.community_cards]}")
                action_idx = human_action_input(mask, game, pos)
            else:
                action_idx = agent_net.select_action(features, mask, np.random.default_rng())
                print(f"Agent chooses: {ACTION_NAMES[action_idx]}")
            # Map action_idx to game action
            legal_actions = game.get_legal_actions(pos)
            def is_action_match(act, action_type):
                if action_type == 'check/call':
                    return act['type'] in ('check', 'call')
                elif action_type in ('raise 0.5x', 'raise 1x', 'raise 2x'):
                    return act['type'] == 'raise'
                elif action_type == 'all-in':
                    return act['type'] == 'all-in'
                else:
                    return act['type'] == action_type
            action_type = ACTION_NAMES[action_idx]
            chosen = None
            for act in legal_actions:
                if is_action_match(act, action_type):
                    from engine.actions import Action
                    if action_type == 'raise 0.5x':
                        pot = game.state.pot.total
                        amount = max(game.state.big_blind, int(pot * 0.5))
                        chosen = Action('raise', amount)
                    elif action_type == 'raise 1x':
                        pot = game.state.pot.total
                        amount = max(game.state.big_blind, pot)
                        chosen = Action('raise', amount)
                    elif action_type == 'raise 2x':
                        pot = game.state.pot.total
                        amount = max(game.state.big_blind, pot * 2)
                        chosen = Action('raise', amount)
                    elif action_type == 'all-in':
                        amount = act.get('amount', game.players[pos].stack)
                        chosen = Action('all-in', amount)
                    else:
                        chosen = Action(act['type'])
                    break
            if chosen is None:
                from engine.actions import Action
                chosen = Action('fold')
                print("No legal action matched, folding by default.")
            game.apply_action(pos, chosen)
        # Hand over
        print("\nHand over!")
        for i, p in enumerate(game.players):
            print(f"Player {i+1} stack: {p.stack}")
        print(f"Pot: {game.state.pot.total}")
        print(f"Community cards: {[str(card) for card in game.state.community_cards]}")
        hand += 1
        if any(p.stack <= 0 for p in game.players):
            print("\nGame over!")
            if game.players[human_pos].stack > game.players[agent_pos].stack:
                print("You win!")
            elif game.players[human_pos].stack < game.players[agent_pos].stack:
                print("Agent wins!")
            else:
                print("Draw!")
            break

if __name__ == "__main__":
    main()
