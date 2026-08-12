"""
Verbose PokerBot run for intermediate output extraction.
Logs all required internals for technical report.
"""
import numpy as np
from training.policy_network import PolicyNetwork, create_action_mask
from training.config import NetworkConfig, FitnessConfig, EvolutionConfig
from training.genome import GenomeFactory
from engine import PokerGame
from engine.features import get_state_vector

SEED = 42
np.random.seed(SEED)

# Configs

net_config = NetworkConfig()
fitness_config = FitnessConfig()
evo_config = EvolutionConfig()
factory = GenomeFactory(net_config, evo_config)

# Create a random genome and network
genome = factory.create_random(generation=0)
network = PolicyNetwork(net_config)
network.set_weights_from_genome(genome.weights)

# Set up a 2-player game
stacks = [fitness_config.starting_stack] * 2
game = PokerGame(
    player_stacks=stacks,
    small_blind=fitness_config.small_blind,
    big_blind=fitness_config.big_blind,
    ante=fitness_config.ante,
    seed=SEED
)
rng = np.random.default_rng(SEED)

step_logs = []

while not game.is_hand_over():
    current = game.state.current_player
    player = game.players[current]
    features = get_state_vector(game, current)
    mask = create_action_mask(game, current)
    logits = network.forward(features)
    masked_logits = np.where(mask > 0.5, logits, -1e9)
    probs = network.get_action_probs(features, mask)
    action = network.select_action(features, mask, rng)
    action_name = ['fold', 'check/call', 'raise_half_pot', 'raise_pot', 'raise_2x_pot', 'all_in'][action]
    # Log all internals
    step_logs.append({
        'raw_state': {
            'hole_cards': [(c.rank, c.suit) for c in player.hole_cards],
            'position': current,
            'pot_size': game.state.pot.total,
            'call_amount': max(0, game.current_bet - player.bet),
            'num_active': sum(1 for p in game.players if not p.has_folded),
            'street': game.state.betting_round
        },
        'features': features.tolist(),
        'mask': mask.tolist(),
        'logits': logits.tolist(),
        'masked_logits': masked_logits.tolist(),
        'probs': probs.tolist(),
        'action': action,
        'action_name': action_name,
        'pot_after': game.state.pot.total
    })
    # Apply action
    from training.fitness import abstract_action_to_engine_action
    engine_action = abstract_action_to_engine_action(action, game, current)
    game.apply_action(current, engine_action)

# Print logs in required format
import json
print(json.dumps(step_logs, indent=2))
