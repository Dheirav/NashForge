#!/usr/bin/env python3
"""
Training script for evolutionary poker AI.

Usage:
    python scripts/train.py                  # Default settings
    python scripts/train.py --quick          # Quick test (5 generations)
    python scripts/train.py --production     # Full production run
    python scripts/train.py --resume PATH    # Resume from checkpoint

Examples:
    # Quick test run
    python3 scripts/train.py --quick --seed 42
    
    # Full training with custom settings
    python3 scripts/train.py --pop 30 --gens 200 --hands 1000
    
    # Resume from checkpoint
    python3 scripts/train.py --resume checkpoints/evolution_run
"""
import os
import sys

# Check if TensorFlow logging should be disabled (faster startup)
disable_tf_logs = '--disable-tensorflow-logs' in sys.argv or '--disable-tf-logs' in sys.argv

# Suppress TensorFlow startup messages if requested (saves ~2-3 seconds)
if disable_tf_logs:
    os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'  # Suppress all TF logging
    import warnings
    warnings.filterwarnings('ignore')

# Optimize numpy for multiprocessing - prevent thread conflicts
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['NUMEXPR_NUM_THREADS'] = '1'

import argparse
import sys

# Add project root to path (go up 2 levels from scripts/training/train.py to reach project root)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from training import (
    EvolutionTrainer,
    TrainingConfig,
    NetworkConfig,
    EvolutionConfig,
    FitnessConfig,
)


def parse_args():
    parser = argparse.ArgumentParser(
        description='Train poker AI via evolutionary self-play',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    # Mode selection
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--quick', action='store_true',
                      help='Quick test run (5 generations)')
    mode.add_argument('--production', action='store_true',
                      help='Full production training')
    mode.add_argument('--resume', type=str, default=None,
                      help='Resume from checkpoint directory')
    mode.add_argument('--phase1', action='store_true',
                      help='Phase 1: Stabilization and Debug Phase')
    mode.add_argument('--phase2', action='store_true',
                      help='Phase 2: Strategy Refinement Phase')

    # Curriculum argument (not mutually exclusive)
    parser.add_argument('--curriculum', action='store_true',
                       help='Curriculum learning: gradually increase difficulty')

    # Evolution parameters
    parser.add_argument('--pop', type=int, default=20,
                        help='Population size')
    parser.add_argument('--gens', type=int, default=100,
                        help='Number of generations')
    parser.add_argument('--elite', type=float, default=0.1,
                        help='Elite fraction to preserve')
    parser.add_argument('--sigma', type=float, default=0.1,
                        help='Mutation strength (sigma)')
    
    # Fitness evaluation
    parser.add_argument('--hands', type=int, default=500,
                        help='Hands per matchup')
    parser.add_argument('--matchups', type=int, default=4,
                        help='Matchups per agent')
    parser.add_argument('--players', type=int, default=6,
                        help='Players per table (2-6)')
    parser.add_argument('--heads-up-fraction', type=float, default=0.0,
                        help='Fraction of matchups run as heads-up (2-player). '
                             '0 = pure multi-table, 1 = pure heads-up, 0.3 = mixed.')
    parser.add_argument('--hu-hands', type=int, default=None,
                        help='Hands per heads-up matchup (defaults to --hands if not set)')
    
    # Network architecture
    parser.add_argument('--hidden', type=int, nargs='+', default=[64, 32],
                        help='Hidden layer sizes')
    
    # Other settings
    parser.add_argument('--seed', type=int, default=42,
                        help='Random seed')
    parser.add_argument('--output', type=str, default='checkpoints',
                        help='Output directory')
    parser.add_argument('--name', type=str, default='evolution_run',
                        help='Experiment name')
    parser.add_argument('--workers', type=int, default=4,
                        help='Parallel workers (default 4 for speedup)')
    parser.add_argument('--checkpoint-interval', type=int, default=10,
                        help='Checkpoint every N generations (default 10, use 999 to disable during sweeps)')
    
    parser.add_argument('--seed-weights', type=str, default=None,
                        help='Path to .npy file with weights to seed initial population')
    
    # Performance optimization
    parser.add_argument('--disable-tensorflow-logs', '--disable-tf-logs', action='store_true',
                        help='Suppress TensorFlow startup messages (saves ~2-3 seconds per run)')
    
    # Hall of Fame pre-loading options
    hof_group = parser.add_argument_group('Hall of Fame Pre-loading')
    hof_group.add_argument('--hof-dir', type=str, default=None,
                          help='Directory containing checkpoints to pre-load into Hall of Fame')
    hof_group.add_argument('--hof-paths', nargs='+', default=None,
                          help='Specific .npy files to pre-load into Hall of Fame')
    hof_group.add_argument('--hof-count', type=int, default=5,
                          help='Number of models to load from hof-dir (default: 5)')
    return parser.parse_args()


def create_config(args) -> TrainingConfig:
    if getattr(args, 'curriculum', False):
        # Start with simple config, then increase complexity in main()
        return TrainingConfig(
            network=NetworkConfig(hidden_sizes=[32]),
            evolution=EvolutionConfig(
                population_size=12,
                elite_fraction=0.2,
                mutation_sigma=0.1,
                hof_size=4,
            ),
            fitness=FitnessConfig(
                hands_per_matchup=300,
                matchups_per_agent=4,
                num_players=2,
                starting_stack=2000,
                small_blind=5,
                big_blind=10,
                ante=0,
                num_workers=2,
            ),
            num_generations=40,
            seed=args.seed,
            output_dir=args.output,
            experiment_name=args.name + '_curriculum',
        )
    """Create training config from arguments."""
    if args.quick:
        config = TrainingConfig.for_quick_test()
        config.seed = args.seed
        return config
    if args.production:
        return TrainingConfig.for_production(seed=args.seed)
    if args.phase1:
        return TrainingConfig.for_phase_1(seed=args.seed)
    if args.phase2:
        return TrainingConfig.for_phase_2(seed=args.seed)
    return TrainingConfig(
        network=NetworkConfig(
            hidden_sizes=args.hidden,
        ),
        evolution=EvolutionConfig(
            population_size=args.pop,
            elite_fraction=args.elite,
            mutation_sigma=args.sigma,
        ),
        fitness=FitnessConfig(
            hands_per_matchup=args.hands,
            matchups_per_agent=args.matchups,
            num_players=args.players,
            num_workers=args.workers,
            heads_up_fraction=getattr(args, 'heads_up_fraction', 0.0),
            hu_hands_per_matchup=getattr(args, 'hu_hands', None) or args.hands,
        ),
        num_generations=args.gens,
        checkpoint_interval=args.checkpoint_interval,
        seed=args.seed,
        output_dir=args.output,
        experiment_name=args.name,
    )


def main():
    args = parse_args()
    
    print("=" * 60)
    print("Evolutionary Poker AI Training")
    print("=" * 60)
    
    # Resume or create new config
    if args.resume:
        print(f"\nResuming from {args.resume}...")
        # Load config from checkpoint
        import json
        from pathlib import Path
        # Accept the experiment directory as well as the run directory inside
        # it; checkpoints live in <experiment>/runs/run_<timestamp>/.
        from training.evolution import resolve_checkpoint_dir
        checkpoint_path = Path(resolve_checkpoint_dir(str(args.resume)))
        if str(checkpoint_path) != str(args.resume):
            print(f"  resolved to most recent run: {checkpoint_path}")
        config_file = checkpoint_path / 'config.json'
        if not config_file.exists():
            print(f"Error: no checkpoint found at {args.resume}")
            print(f"       looked for {config_file} and under {args.resume}/runs/")
            sys.exit(1)
        
        with open(config_file) as f:
            checkpoint_config = json.load(f)
        
        # Write back into the SAME experiment directory. The checkpoint lives at
        # <output>/<experiment>/runs/run_<ts>/, so the experiment directory is
        # two levels up; older checkpoints saved no experiment_name, so it is
        # recovered from the path rather than trusted from the file.
        experiment_dir = (checkpoint_path.parent.parent
                          if checkpoint_path.parent.name == 'runs'
                          else checkpoint_path)

        # Resuming means "continue for this many more generations". Deriving the
        # target from the stored count instead meant --gens was ignored, and a
        # target already reached silently trained nothing while reporting success.
        completed = int(checkpoint_config.get('generation', 0))
        config = TrainingConfig(
            network=NetworkConfig(**checkpoint_config['network']),
            evolution=EvolutionConfig(**checkpoint_config['evolution']),
            fitness=FitnessConfig(**checkpoint_config['fitness']),
            num_generations=args.gens,   # provisional; corrected after loading
            checkpoint_interval=checkpoint_config.get('checkpoint_interval', 10),
            seed=checkpoint_config['seed'],
            output_dir=str(experiment_dir.parent),
            experiment_name=checkpoint_config.get('experiment_name', experiment_dir.name),
        )

        # Create trainer with checkpoint config
        trainer = EvolutionTrainer(config)
        trainer.load_checkpoint(str(checkpoint_path))

        # trainer.generation is now the count actually restored from state.json.
        config.num_generations = trainer.generation + args.gens
        print(f"  resumed at generation {trainer.generation}; "
              f"training {args.gens} more (through generation {config.num_generations})")
    else:
        print("\nInitializing new population...")
        # Create config
        config = create_config(args)
        
        # Create trainer
        trainer = EvolutionTrainer(config)
        seed_weights = None
        hof_weights = None
        
        # Load seed weights if provided
        if args.seed_weights:
            import numpy as np
            print(f"Loading seed weights from {args.seed_weights}...")
            seed_weights = np.load(args.seed_weights)
        
        # Load Hall of Fame weights if provided
        if args.hof_dir or args.hof_paths:
            import numpy as np
            from pathlib import Path
            hof_weights = []
            
            if args.hof_dir:
                print(f"Loading Hall of Fame from directory: {args.hof_dir}")
                hof_dir = Path(args.hof_dir)
                
                # Load best_genome.npy
                best_path = hof_dir / 'best_genome.npy'
                if best_path.exists():
                    hof_weights.append(np.load(best_path))
                    print(f"  Loaded best_genome.npy")
                
                # Load from population.npy
                pop_path = hof_dir / 'population.npy'
                if pop_path.exists() and len(hof_weights) < args.hof_count:
                    population = np.load(pop_path)
                    remaining = min(args.hof_count - len(hof_weights), len(population))
                    for i in range(remaining):
                        hof_weights.append(population[i])
                    print(f"  Loaded {remaining} genomes from population.npy")
                
                # Load from hall_of_fame.npy
                hof_path = hof_dir / 'hall_of_fame.npy'
                if hof_path.exists() and len(hof_weights) < args.hof_count:
                    hof = np.load(hof_path)
                    remaining = min(args.hof_count - len(hof_weights), len(hof))
                    for i in range(remaining):
                        hof_weights.append(hof[i])
                    print(f"  Loaded {remaining} genomes from hall_of_fame.npy")
                
                # Load champion files (*champion.npy)
                if len(hof_weights) < args.hof_count:
                    champion_files = list(hof_dir.glob("*champion.npy"))
                    remaining = min(args.hof_count - len(hof_weights), len(champion_files))
                    for i in range(remaining):
                        try:
                            champion_weights = np.load(champion_files[i])
                            hof_weights.append(champion_weights)
                        except Exception as e:
                            print(f"  Warning: Could not load {champion_files[i]}: {e}")
                    if remaining > 0:
                        print(f"  Loaded {remaining} champion genomes from *champion.npy files")
                    
            elif args.hof_paths:
                print(f"Loading Hall of Fame from {len(args.hof_paths)} paths")
                for path_str in args.hof_paths:
                    path = Path(path_str)
                    if not path.exists():
                        print(f"  Warning: {path} not found, skipping")
                        continue
                    try:
                        loaded = np.load(path)
                        if loaded.ndim == 2:  # Population/HOF file
                            hof_weights.append(loaded[0])
                            print(f"  Loaded {path} (took first genome)")
                        else:
                            hof_weights.append(loaded)
                            print(f"  Loaded {path}")
                    except Exception as e:
                        print(f"  Warning: Could not load {path}: {e}")
            
            if hof_weights:
                print(f"Successfully loaded {len(hof_weights)} Hall of Fame opponents")
            else:
                print("Warning: No Hall of Fame models loaded")
                hof_weights = None
        
        trainer.initialize(seed_weights=seed_weights, hof_weights=hof_weights)
    
    # Print config summary
    print(f"\nConfiguration:")
    print(f"  Population size: {config.evolution.population_size}")
    print(f"  Generations: {config.num_generations}")
    print(f"  Elite fraction: {config.evolution.elite_fraction}")
    print(f"  Mutation sigma: {config.evolution.mutation_sigma}")
    print(f"  Hall of Fame size: {config.evolution.hof_size}")
    if not args.resume and (args.hof_dir or args.hof_paths):
        print(f"  Pre-loaded HOF opponents: {len(trainer.population.hall_of_fame)}")
    print(f"  Hands per matchup: {config.fitness.hands_per_matchup}")
    print(f"  Matchups per agent: {config.fitness.matchups_per_agent}")
    print(f"  Players per table: {config.fitness.num_players}")
    print(f"  Network architecture: {trainer.factory._network.layer_sizes}")
    print(f"  Genome size: {trainer.factory.genome_size} parameters")
    print(f"  Seed: {config.seed}")
    print(f"  Output: {trainer.output_dir}")
    
    # Curriculum learning: phase-by-phase training
    if getattr(args, 'curriculum', False):
        curriculum_phases = [
            # (description, config overrides, generations)
            ("Phase 1: Heads-up, deep stacks", dict(
                fitness=dict(num_players=2, starting_stack=2000, small_blind=5, big_blind=10, ante=0),
                network=dict(hidden_sizes=[32]),
                evolution=dict(population_size=12, mutation_sigma=0.1, hof_size=4),
                num_generations=40,
            ), 40),
            ("Phase 2: 3 players, moderate stacks", dict(
                fitness=dict(num_players=3, starting_stack=1500, small_blind=10, big_blind=20, ante=0),
                network=dict(hidden_sizes=[64, 32]),
                evolution=dict(population_size=16, mutation_sigma=0.07, hof_size=6),
                num_generations=40,
            ), 40),
            ("Phase 3: 6-max, standard stacks", dict(
                fitness=dict(num_players=6, starting_stack=1000, small_blind=5, big_blind=10, ante=1),
                network=dict(hidden_sizes=[128, 64]),
                evolution=dict(population_size=24, mutation_sigma=0.05, hof_size=10),
                num_generations=60,
            ), 60),
        ]
        for desc, overrides, gens in curriculum_phases:
            print(f"\n{'='*60}\n{desc}\n{'='*60}")
            # Apply overrides
            for section, vals in overrides.items():
                if section == 'fitness':
                    for k, v in vals.items():
                        setattr(trainer.config.fitness, k, v)
                elif section == 'network':
                    for k, v in vals.items():
                        setattr(trainer.config.network, k, v)
                elif section == 'evolution':
                    for k, v in vals.items():
                        setattr(trainer.config.evolution, k, v)
                elif section == 'num_generations':
                    trainer.config.num_generations = v
            trainer.config.experiment_name += f"_{desc.split(':')[0].replace(' ', '')}"
            trainer.save_checkpoint()  # Save before phase
            best = trainer.train()
            trainer.save_checkpoint()  # Save after phase
        print("\nCurriculum training complete!")
        print(f"Best fitness: {trainer.best_fitness:.2f} BB/100")
        print(f"Best genome: {trainer.best_genome}")
        print(f"Checkpoint saved to: {trainer.output_dir}")
        baseline_score = trainer.evaluate_best(num_hands=2000)
        print(f"Best agent vs random: {baseline_score:.2f} BB/100")
    else:
        # Standard training
        try:
            best = trainer.train()
            print("\n" + "=" * 60)
            print("Training Complete!")
            print("=" * 60)
            print(f"Best fitness: {trainer.best_fitness:.2f} BB/100")
            print(f"Best genome: {trainer.best_genome}")
            print(f"Checkpoint saved to: {trainer.output_dir}")
            print("\nFinal evaluation against random opponents...")
            baseline_score = trainer.evaluate_best(num_hands=2000)
            print(f"Best agent vs random: {baseline_score:.2f} BB/100")

            # --- Write report.txt in checkpoint dir ---
            report_path = os.path.join(trainer.output_dir, 'report.txt')
            try:
                with open(report_path, 'w') as f:
                    f.write(f"PokerBot Training Report\n")
                    f.write(f"=======================\n\n")
                    f.write(f"Experiment: {getattr(trainer.config, 'experiment_name', 'N/A')}\n")
                    f.write(f"Population size: {trainer.config.evolution.population_size}\n")
                    f.write(f"Generations: {trainer.config.num_generations}\n")
                    f.write(f"Hands per matchup: {trainer.config.fitness.hands_per_matchup}\n")
                    f.write(f"Matchups per agent: {trainer.config.fitness.matchups_per_agent}\n")
                    f.write(f"Mutation sigma: {trainer.config.evolution.mutation_sigma}\n")
                    f.write(f"Hidden layers: {trainer.config.network.hidden_sizes}\n")
                    f.write(f"\n--- Results ---\n")
                    f.write(f"Best fitness (train): {trainer.best_fitness:.2f} BB/100\n")
                    f.write(f"Best agent vs random: {baseline_score:.2f} BB/100\n")
                    if hasattr(trainer, 'train_fitness_curve'):
                        f.write(f"\nTrain fitness curve: {getattr(trainer, 'train_fitness_curve', [])}\n")
                    if hasattr(trainer, 'eval_fitness_curve'):
                        f.write(f"Eval fitness curve: {getattr(trainer, 'eval_fitness_curve', [])}\n")
                    f.write(f"\nBest genome: {trainer.best_genome}\n")

                    # --- Action Frequency and Scenario Analysis ---
                    f.write("\n--- Action Frequency & Scenario Analysis ---\n")
                    try:
                        metrics = trainer.get_behavior_metrics(trainer.best_genome, num_hands=500, num_players=trainer.config.fitness.num_players)
                        action_counts = metrics.get('action_counts', None)
                        total_actions = int(action_counts.sum()) if action_counts is not None else 0
                        if action_counts is not None and total_actions > 0:
                            f.write("\nAction frequencies (across 500 simulated hands):\n")
                            action_labels = ['fold', 'call/check', 'raise 0.5x', 'raise 1x', 'raise 2x', 'all-in']
                            for i, count in enumerate(action_counts):
                                freq = count / total_actions
                                label = action_labels[i] if i < len(action_labels) else f'action_{i}'
                                f.write(f"  {label:10s}: {count:4d} ({freq:.2%})\n")
                            f.write("\nAggression factor: {:.2f}\n".format(metrics.get('aggression_factor', 0)))
                            f.write("Showdown frequency: {:.2%}\n".format(metrics.get('showdown_freq', 0)))
                            f.write("Showdown win rate: {:.2%}\n".format(metrics.get('showdown_win_rate', 0)))
                            f.write("All-in frequency: {:.2%}\n".format(metrics.get('allin_freq', 0)))
                            f.write("C-bet rate: {:.2%}\n".format(metrics.get('cbet_rate', 0)))
                            f.write("Bluff rate: {:.2%}\n".format(metrics.get('bluff_rate', 0)))
                            f.write("Fold to aggression rate: {:.2%}\n".format(metrics.get('fold_to_aggr_rate', 0)))
                        else:
                            f.write("\n[Could not compute action frequencies: insufficient data]\n")
                    except Exception as e:
                        f.write(f"\n[Error computing action frequencies: {e}]\n")
                print(f"\nReport written to {report_path}")
            except Exception as e:
                print(f"[Warning] Could not write report.txt: {e}")
            # --- End report.txt ---

        except KeyboardInterrupt:
            print("\n\nTraining interrupted. Saving checkpoint...")
            trainer.save_checkpoint()
            print("Checkpoint saved. You can resume with --resume flag.")
            sys.exit(1)


if __name__ == '__main__':
    main()
