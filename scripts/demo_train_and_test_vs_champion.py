"""
Demo script to train a simple agent for a few generations and return the best genome and fitness history.
"""
import numpy as np
from training.evolution import EvolutionTrainer
from training.config import TrainingConfig, NetworkConfig, EvolutionConfig, FitnessConfig

def train_simple_agent(format_mode, generations=5):
    """
    Trains an agent using the evolutionary trainer and returns the best genome and fitness history.
    Args:
        format_mode (str): 'heads-up' or 'multi-table'
        generations (int): Number of generations to train
    Returns:
        best_genome (np.ndarray): The best genome found
        fitness_history (list): List of fitness values per generation
    """
    # Set up config based on format
    if format_mode == 'heads-up':
        num_players = 2
        heads_up_fraction = 1.0
    else:
        num_players = 5
        heads_up_fraction = 0.0

    config = TrainingConfig(
        network=NetworkConfig(input_size=17, hidden_sizes=[64, 32], output_size=6),
        evolution=EvolutionConfig(population_size=8),
        fitness=FitnessConfig(
            hands_per_matchup=50,
            matchups_per_agent=2,
            num_players=num_players,
            heads_up_fraction=heads_up_fraction,
            starting_stack=1000,
            small_blind=5,
            big_blind=10,
            ante=0,
            num_workers=1,
            temperature=1.0
        ),
        num_generations=generations,
        seed=42,
        output_dir='checkpoints',
        experiment_name='demo_train',
        log_interval=1,
        checkpoint_interval=generations
    )

    trainer = EvolutionTrainer(config)
    trainer.initialize()
    best_genome_obj = trainer.train()
    # Save fitness history (mean fitness per generation)
    fitness_history = [gen['mean_fitness'] for gen in trainer.history]
    # Return the best genome weights as np.ndarray
    best_genome = best_genome_obj.weights if hasattr(best_genome_obj, 'weights') else np.array([])
    return best_genome, fitness_history

if __name__ == "__main__":
    best_genome, fitness_history = train_simple_agent('heads-up', 5)
    print("Best genome shape:", best_genome.shape)
    print("Fitness history:", fitness_history)
