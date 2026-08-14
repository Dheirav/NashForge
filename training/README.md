# Training System

**Evolutionary poker AI training through self-play**

**See Also**: 
- [HOF_IMPACT_ANALYSIS.md](../docs/HOF_IMPACT_ANALYSIS.md) - Hall of Fame training provides +52% win rate improvement
- [TRAINING_FINDINGS_REPORT.md](../docs/TRAINING_FINDINGS_REPORT.md) - Comprehensive formal research report

---

## Overview

This module implements an evolutionary algorithm for training poker AI agents. Networks compete in self-play poker games, with successful strategies propagating to future generations through mutation and selection.

**Key Features**:
- 🧬 Evolutionary algorithm with elitism and Hall of Fame
- 🎲 Self-play fitness evaluation  
- 🧠 Neural network policy agents
- 📊 Population diversity maintenance
- 🏆 **Hall of Fame pre-loading** for training with strong opponents (+52% win rate)
- ⚡ Parallel evaluation with multiprocessing
- 🎯 Configurable hyperparameters
- ⚡ **Numba JIT-optimized** for 2-3× speedup

**Performance**: ~4-6 sec/generation with Numba, ~13 sec without

**New Feature**: `EvolutionTrainer.initialize()` now accepts `hof_weights` parameter to pre-load Hall of Fame opponents. This prevents small populations from overfitting to weak self-play opponents. Analysis shows HoF training provides **+52.2% relative improvement** in win rate.

---

## Module Structure

```
training/
├── __init__.py              # Module exports
├── config.py                # Configuration dataclasses
├── genome.py                # Genome representation and factory (Numba-optimized)
├── policy_network.py        # Neural network policy with forward pass
├── policy_network_fast.py   # Legacy fast neural network (deprecated, use policy_network.py)
├── fitness.py               # Fitness evaluation through self-play
├── evolution.py             # Evolutionary algorithm orchestration
├── self_play.py             # Self-play game utilities
└── README.md                # This file
```

**Note**: `policy_network_fast.py` is a legacy file kept for reference. All optimizations have been integrated into `policy_network.py` with Numba JIT compilation.

---

## Core Components

### 1. Configuration (`config.py`)

```python
from training import NetworkConfig, EvolutionConfig, FitnessConfig

# Neural network architecture
network_config = NetworkConfig(
    input_size=17,              # State features
    hidden_layers=[64, 32],     # Two hidden layers
    output_size=6,              # Abstract actions
    activation='relu'
)

# Evolution parameters
evolution_config = EvolutionConfig(
    population_size=20,         # Number of agents
    elite_fraction=0.1,         # Keep top 10%
    mutation_sigma=0.1,         # Mutation strength
    mutation_decay=0.99,        # Decay per generation
    diversity_bonus=0.0,        # Diversity preservation
    num_parents=1               # Mutation-only (no crossover)
)

# Fitness evaluation
fitness_config = FitnessConfig(
    hands_per_matchup=3000,     # Hands per opponent
    matchups_per_agent=12,      # Different opponents
    players_per_table=6,        # 6-max poker
    starting_stack=1000,        # Initial chips
    small_blind=5,              # SB amount
    big_blind=10,               # BB amount
    ante=0,                     # Ante (0 = none)
    temperature=1.0             # Sampling temperature
)
```

---

### 2. Genome (`genome.py`)

A genome is a flat numpy array representing all neural network weights.

**New Feature**: Enhanced genome tracking with `hof_opponents_used` field for Hall of Fame analysis.

```python
from training import Genome, GenomeFactory

# Create factory
factory = GenomeFactory(network_config, evolution_config)

# Create random genome
genome = factory.create_random_genome(generation=0)
print(f"Genome size: {genome.weights.shape}")  # (3430,)

# Mutate
offspring = factory.mutate(genome, generation=1)

# Crossover (if using multiple parents)
child = factory.crossover(parent1, parent2, generation=1)
```

**Genome Attributes**:
- `genome_id`: Unique identifier
- `weights`: Flat numpy array of all network parameters
- `fitness`: Evaluated fitness score (BB/100)
- `generation`: Generation this genome was created
- `parent_id`: Parent genome ID

---

### 3. Policy Network (`policy_network.py`)

Neural network that maps game state → action probabilities.

```python
from training import PolicyNetwork

# Create from config
network = PolicyNetwork(network_config)

# Or from genome weights
network = PolicyNetwork.from_genome(genome, network_config)

# Forward pass
features = np.array([...])  # 17 features
logits = network.forward(features)

# Select action
mask = np.array([1, 1, 1, 0, 0, 1])  # Legal actions
action_idx = network.select_action(features, mask, rng, temperature=1.0)

# Batched forward pass (1.4-1.5× faster)
features_batch = np.array([[...], [...], [...]])  # (batch_size, 17)
logits_batch = network.forward_batch(features_batch)
```

**Architecture**:
- Input: 17 state features
- Hidden layer 1: 64 neurons (ReLU)
- Hidden layer 2: 32 neurons (ReLU)
- Output: 6 action logits

**Abstract Actions**:
0. Fold
1. Check/Call
2. Raise 0.5× pot
3. Raise 1.0× pot
4. Raise 2.0× pot
5. All-in

---

### 4. Fitness Evaluation (`fitness.py`)

Evaluate agents through self-play poker games.

```python
from training import evaluate_matchup

# Evaluate one genome against opponents
fitness_bb100, hands_played = evaluate_matchup(
    genome_weights=genome.weights,
    opponent_weights=[opp1.weights, opp2.weights, ...],
    network_config=network_config,
    fitness_config=fitness_config,
    hand_seeds=None  # None = random hands
)

print(f"Fitness: {fitness_bb100:.2f} BB/100")
```

**Fitness Metric**: Big blinds won per 100 hands (BB/100)
- Positive = winning player
- Negative = losing player
- Standard poker performance metric

**Process**:
1. Create table with genome + opponents
2. Play specified number of hands
3. Track chip changes for genome
4. Return BB/100 = (chips_won / big_blind) * 100 / hands_played

---

### 5. Evolution (`evolution.py`)

Main evolutionary algorithm orchestrator with Hall of Fame support.

```python
from training import EvolutionTrainer, TrainingConfig

# Create evolution trainer
config = TrainingConfig(
    network=network_config,
    evolution=evolution_config,
    fitness=fitness_config,
    num_generations=100,
    seed=42
)

trainer = EvolutionTrainer(config)

# Option 1: Standard initialization
trainer.initialize()

# Option 2: Initialize with Hall of Fame opponents (NEW!)
# Prevents small populations from overfitting to weak self-play
hof_weights = [
    np.load('checkpoints/champion1/best_genome.npy', allow_pickle=True).item(),
    np.load('checkpoints/champion2/best_genome.npy', allow_pickle=True).item(),
    np.load('checkpoints/champion3/best_genome.npy', allow_pickle=True).item(),
]
trainer.initialize(hof_weights=hof_weights)

# Run training
for generation in range(100):
    stats = trainer.train_generation()
    
    print(f"Gen {generation}: Mean = {stats['mean_fitness']:.2f}, "
          f"Best = {trainer.best_fitness:.2f}")
```

**Evolution Steps**:
1. **Evaluate**: Play poker games vs population + HoF, measure BB/100
2. **Update HoF**: Add top performers if sufficiently novel
3. **Select**: Keep elite performers
4. **Mutate**: Add Gaussian noise to create offspring
5. **Replace**: Form new population
6. **Repeat**: Next generation

**Hall of Fame Benefits**:
- Prevents overfitting to weak self-play opponents
- Enables smaller populations to achieve good performance
- Tournament data: p12 without HoF = 33.8% win rate, with HoF can match larger populations

---

## Training Pipeline

### Full Training Process

```python
from training import EvolutionTrainer, TrainingConfig, NetworkConfig, EvolutionConfig, FitnessConfig

# 1. Configure
config = TrainingConfig(
    network=NetworkConfig(input_size=17, hidden_sizes=[128, 128], output_size=6),
    evolution=EvolutionConfig(population_size=20, mutation_sigma=0.1),
    fitness=FitnessConfig(hands_per_matchup=500, matchups_per_agent=8, num_players=2),
    num_generations=100,
    seed=42,
    output_dir='checkpoints/evolution_run'
)

# 2. Initialize trainer
trainer = EvolutionTrainer(config)
trainer.initialize()

# 3. Train
for gen in range(config.num_generations):
    stats = trainer.train_generation()
    print(f"Gen {gen}: Mean = {stats['mean_fitness']:.2f}, Best = {trainer.best_fitness:.2f}")

# 4. Get best agent
best_genome = trainer.population.get_best()
network = PolicyNetwork.from_genome(best_genome, config.network)
```

### Training with Hall of Fame Opponents (NEW!)

**Problem**: Small populations (p12, p16) overfit to weak self-play opponents  
**Solution**: Pre-load strong opponents into Hall of Fame before training

```python
from training import EvolutionTrainer, TrainingConfig
import numpy as np

# Load tournament winners as HoF opponents
hof_weights = [
    np.load('checkpoints/deep_p40_m8_h375_s0.1/evolution_run/best_genome.npy', allow_pickle=True).item(),
    np.load('checkpoints/deep_p40_m6_h500_s0.15/evolution_run/best_genome.npy', allow_pickle=True).item(),
    np.load('checkpoints/deep_p20_m6_h500_s0.15/evolution_run/best_genome.npy', allow_pickle=True).item(),
]

# Configure small population training
config = TrainingConfig(
    network=NetworkConfig(input_size=17, hidden_sizes=[128, 128], output_size=6),
    evolution=EvolutionConfig(population_size=12, mutation_sigma=0.1),  # Small population!
    fitness=FitnessConfig(hands_per_matchup=500, matchups_per_agent=8, num_players=2),
    num_generations=100,
    seed=42
)

# Initialize with HoF opponents
trainer = EvolutionTrainer(config)
trainer.initialize(hof_weights=hof_weights)

# Train normally - population will compete against strong HoF opponents
for gen in range(config.num_generations):
    stats = trainer.train_generation()
```

**Benefits**:
- 3× faster training (p12 vs p40)
- Prevents overfitting to weak opponents
- Tournament results: p12 with HoF can match p40 performance!

**Use Cases**:
- Budget-constrained training (limited compute)
- Quick experimentation with strong baselines
- Transfer learning from previous training runs

---

## Optimizations

### ✅ Implemented Optimizations

#### 1. Numba JIT Compilation (2-3× speedup) - NEW!

```python
# Forward pass automatically uses JIT when Numba is available
from training import PolicyNetwork, HAS_NUMBA

network = PolicyNetwork(config)
print(f"Numba JIT: {HAS_NUMBA}")  # True if numba installed

# JIT-compiled functions:
# - forward_pass_jit() - Single forward pass
# - forward_batch_jit() - Batched forward pass  
# - apply_mutation_jit() - Genome mutation
```

**Installation**: `pip install numba` for automatic 2-3× speedup

#### 2. Batched Forward Pass (1.4-1.5× speedup)

```python
# Process multiple decisions simultaneously
features_batch = np.array([features1, features2, features3])
masks_batch = np.array([mask1, mask2, mask3])

# Vectorized inference
actions = network.select_action_batch(features_batch, masks_batch, rng)
```

#### 3. Multiprocessing (4× speedup)

```python
# Parallel genome evaluation
evolution = Evolution(..., num_workers=4)

# Fitness evaluation distributed across workers
# Each worker evaluates subset of population
```

#### 4. Memory Pooling (1.2-1.4× speedup)

```python
# Reuse game objects
from training.fitness import GamePool

pool = GamePool(size=100)
game = pool.acquire(...)  # Get from pool
# ... play game ...
pool.release(game)  # Return to pool
```

#### 5. PCG64 RNG (1.15-1.2× speedup)

```python
from numpy.random import PCG64, Generator

# Faster than default Mersenne Twister
rng = Generator(PCG64(seed))
```

**See**: NUMBA_JIT_GUIDE.md for JIT implementation details

---

## Configuration Guide

### Network Architecture

**Small** (fast training):
```python
NetworkConfig(
    input_size=17,
    hidden_layers=[32, 16],  # Smaller layers
    output_size=6
)
```

**Medium** (balanced):
```python
NetworkConfig(
    input_size=17,
    hidden_layers=[64, 32],  # Default
    output_size=6
)
```

**Large** (better performance):
```python
NetworkConfig(
    input_size=17,
    hidden_layers=[128, 64, 32],  # Deeper network
    output_size=6
)
```

### Evolution Parameters

**Quick exploration**:
```python
EvolutionConfig(
    population_size=10,      # Small population
    elite_fraction=0.2,      # Keep more elites
    mutation_sigma=0.2       # Large mutations
)
```

**Standard training**:
```python
EvolutionConfig(
    population_size=20,      # Medium population
    elite_fraction=0.1,      # 10% elites
    mutation_sigma=0.1       # Moderate mutations
)
```

**Fine-tuning**:
```python
EvolutionConfig(
    population_size=50,      # Large population
    elite_fraction=0.05,     # Few elites (more exploration)
    mutation_sigma=0.05      # Small mutations
)
```

### Fitness Evaluation

**Fast testing**:
```python
FitnessConfig(
    hands_per_matchup=500,   # Few hands
    matchups_per_agent=3     # Few opponents
)
```

**Standard training**:
```python
FitnessConfig(
    hands_per_matchup=3000,  # Many hands
    matchups_per_agent=12    # Multiple opponents
)
```

**High-quality evaluation**:
```python
FitnessConfig(
    hands_per_matchup=5000,  # Very many hands
    matchups_per_agent=20    # Many opponents
)
```

---

## Usage Examples

### Example 1: Basic Training

```python
from training import Evolution, NetworkConfig, EvolutionConfig, FitnessConfig

# Configure
config_network = NetworkConfig(input_size=17, hidden_layers=[64, 32], output_size=6)
config_evolution = EvolutionConfig(population_size=20)
config_fitness = FitnessConfig(hands_per_matchup=3000)

# Train
evolution = Evolution(config_network, config_evolution, config_fitness, seed=42, num_workers=4)
evolution.initialize_population()

for gen in range(100):
    evolution.evaluate_population()
    evolution.evolve()
    print(f"Generation {gen}: Best = {evolution.best_fitness:.2f} BB/100")
```

### Example 2: Resume Training

```python
# Load checkpoint
evolution = Evolution.load_checkpoint('checkpoints/evolution_run')

# Continue training
for gen in range(evolution.generation, 200):
    evolution.evaluate_population()
    evolution.evolve()
    evolution.save_checkpoint()
```

### Example 3: Custom Fitness Function

```python
from training.fitness import evaluate_matchup

def custom_fitness(genome, opponents):
    # Evaluate with custom settings
    fitness, _ = evaluate_matchup(
        genome.weights,
        opponents,
        network_config,
        custom_fitness_config,
        hand_seeds=[42, 43, 44, ...]  # Fixed hands for reproducibility
    )
    return fitness

# Use in evolution
evolution.fitness_function = custom_fitness
```

---

## 🏆 Hall of Fame Member Tracking

**New Feature**: The training system now tracks which specific Hall of Fame members are used as opponents during fitness evaluation. This enables detailed analysis of elite genome influence and opponent quality impact.

### Implementation Details

**Enhanced Genome Representation**:
```python
# Genomes now optionally track HOF opponent usage
genome.hof_opponents_used = [hof_member_1, hof_member_2, ...]  # List of HOF genome IDs
```

**Fitness Evaluation with Tracking**:
```python
# fitness.py automatically tracks HOF usage
def create_opponent_groups(population, hof_opponents=None, track_hof_usage=True):
    # Creates opponent groups and tracks which HOF members are used
    # Returns: (opponent_groups, hof_usage_tracking)
    
def evaluate_population(population, fitness_config, hof_opponents=None, track_hof_usage=True):
    # Evaluates population and updates genome.hof_opponents_used fields
    # Backward compatible - tracking is optional
```

**Integration with Analysis**:
- HOF tracking integrates seamlessly with `extract_hyperparameter_relationships.py`
- Enables quantitative analysis of which elite solutions influence training
- Maintains backward compatibility with existing code
- Zero performance overhead when tracking is disabled

**Key Benefits**:
1. **Opponent Quality Analysis**: Understand which HOF members contribute most to training
2. **Performance Correlation**: Link specific elite genomes to fitness improvements
3. **Research Insights**: Enable detailed studies of opponent selection impact
4. **Configuration Optimization**: Identify optimal HOF member combinations

**Usage in Training**:
```python
# Enable HOF tracking in evolution (automatic)
from training import Evolution

# Tracking happens automatically if HOF opponents provided
evolution = Evolution(network_config, evolution_config, fitness_config)
evolution.initialize_with_hof(hof_weights)  # Tracking enabled automatically
```

**Analysis Integration**:
```bash
# HOF tracking analysis (part of extract_hyperparameter_relationships.py)
python scripts/analysis/extract_hyperparameter_relationships.py
# Output includes HOF member usage statistics and impact analysis
```

**See Also**:
- HOF_MEMBER_TRACKING_IMPLEMENTATION.md - Complete implementation details
- [extract_hyperparameter_relationships.py](../scripts/analysis/extract_hyperparameter_relationships.py) - Analysis with HOF tracking

---

## Performance Metrics

### Training Speed

**With Numba JIT** (recommended):
- **Generation time**: ~4-6 seconds
- **100 generations**: ~7-10 minutes
- **Configuration**: 20 pop, 3000 hands/matchup, 12 matchups
- **Total speedup**: ~400-500× from original

**Without Numba**:
- **Generation time**: ~13 seconds
- **100 generations**: ~22 minutes
- **Total speedup**: ~175× from original

### Fitness Progression

Typical training run:
```
Gen   0: Mean =  200 BB/100, Best =  450 BB/100
Gen  10: Mean =  380 BB/100, Best =  620 BB/100
Gen  25: Mean =  510 BB/100, Best =  780 BB/100
Gen  50: Mean =  680 BB/100, Best =  950 BB/100
Gen 100: Mean =  850 BB/100, Best = 1200 BB/100
```

### Speedup Breakdown

| Component | Speedup | Status |
|-----------|---------|--------|
| Fast hand eval | 13-16× | ✅ Active |
| Multiprocessing | 4× | ✅ Active |
| FeatureCache | 1.5-2× | ✅ Active |
| forward_batch | 1.4-1.5× | ✅ Active |
| Memory pooling | 1.2-1.4× | ✅ Active |
| PCG64 RNG | 1.15-1.2× | ✅ Active |
| Other optimizations | 1.2-1.5× | ✅ Active |
| **Numba JIT** | **2-3×** | ✅ **Active** |

**Total with Numba**: ~400-500× faster than original  
**Total without Numba**: ~175× faster than original

---

## API Reference

### Evolution Class

```python
class Evolution:
    def __init__(self, network_config, evolution_config, fitness_config, 
                 checkpoint_dir='checkpoints/evolution_run', seed=42, num_workers=4)
    
    def initialize_population(self) -> None
    def evaluate_population(self) -> None
    def evolve(self) -> None
    def save_checkpoint(self) -> None
    
    @classmethod
    def load_checkpoint(cls, checkpoint_dir: str) -> 'Evolution'
    
    def get_best_genome(self) -> Genome
    def get_population_stats(self) -> Dict
```

### PolicyNetwork Class

```python
class PolicyNetwork:
    def __init__(self, config: NetworkConfig)
    
    @classmethod
    def from_genome(cls, genome: Genome, config: NetworkConfig) -> 'PolicyNetwork'
    
    def forward(self, features: np.ndarray) -> np.ndarray
    def forward_batch(self, features_batch: np.ndarray) -> np.ndarray
    def select_action(self, features: np.ndarray, mask: np.ndarray, 
                      rng: np.random.Generator, temperature: float = 1.0) -> int
    def select_action_batch(self, features_batch: np.ndarray, mask_batch: np.ndarray,
                           rng: np.random.Generator, temperature: float = 1.0) -> np.ndarray
    
    def to_genome(self) -> np.ndarray
```

---

## Hyperparameter Optimization

### Running Sweeps

The training system includes tools for systematic hyperparameter optimization:

```bash
# Run a hyperparameter sweep
python scripts/hyperparam_sweep.py --generations 20

# Analyze convergence patterns
python scripts/analyze_convergence.py

# Visualize results (requires matplotlib)
python scripts/visualize_hyperparam_sweep.py
```

### Convergence Analysis

The convergence analyzer identifies which configurations have plateaued vs. still improving:

```bash
python scripts/analyze_convergence.py
```

**Output** (`convergence_analysis.txt`):
- Convergence status for each configuration
- Improvement rates (early/mid/late/recent phases)
- Recommendations on which configs need longer training
- Population size comparisons
- Reliability warnings for premature conclusions

**Status Categories**:
- `STRONGLY_IMPROVING`: Gained >50 fitness in last 5 gens → needs much longer training
- `IMPROVING`: Gained 20-50 fitness → needs more training
- `SLOW_IMPROVEMENT`: Gained 5-20 fitness → may benefit from 10-20 more gens
- `PLATEAUED`: Gained <5 fitness → likely converged

**Example output**:
```
1. 🚀 p12_m6_h500_s0.15 - STRONGLY_IMPROVING
   Final Fitness: 1780.3
   Last 5 gen improvement: 995.4
   💡 RECOMMENDATION: Run longer! Could reach 3771+ fitness
```

### Visualization Suite

Generate comprehensive analysis plots:

```bash
python scripts/visualize_hyperparam_sweep.py
```

**Generated plots** (in `hyperparam_results/sweep_*/visualizations/`):
1. `final_metrics_comparison.png` - Bar charts comparing all metrics
2. `fitness_progression.png` - Learning curves over generations
3. `hyperparameter_heatmaps.png` - Parameter interaction effects
4. `top_configurations.png` - Detailed analysis of best performers
5. `analysis_report.txt` - Text summary with insights

### Best Practices

**For reliable hyperparameter comparison:**

1. **Run until convergence**: Use 50-100 generations, or adaptive stopping
2. **Multiple trials**: Run each config 3-5 times for statistical significance
3. **Check convergence status**: Only compare configs that have plateaued
4. **Staged approach**:
   - Phase 1: Quick sweep (20 gens) to eliminate poor configs
   - Phase 2: Extended runs (50+ gens) on top 5-10 configs  
   - Phase 3: Deep validation (3-5 trials) on top 3 configs

**Common pitfalls**:
- ✗ Comparing configs at fixed generation count (some may still be improving)
- ✗ Single trials (high variance in fitness due to opponent sampling)
- ✗ Ignoring overfitting gap (train fitness >> eval fitness)

**Recommended parameters to test**:
- `population_size`: 12, 20, 30 (larger = more diversity)
- `mutation_sigma`: 0.05, 0.1, 0.15 (exploration strength)
- `matchups_per_agent`: 2, 4, 6, 8 (evaluation robustness)
- `hands_per_matchup`: 500, 1000, 1500 (fitness variance)

---

## Testing

```bash
# Test evolution
python -m pytest tests/test_evolution.py -v

# Test policy network
python -m pytest tests/test_policy_network.py -v

# Test fitness evaluation
python scripts/test_ai_hands.py
```

---

## Troubleshooting

### Issue: Training is slow
**Solutions**:
- Increase `num_workers` (use more CPU cores)
- Reduce `hands_per_matchup` or `matchups_per_agent`
- Install `numba` for 2-3× speedup: `pip install numba`

### Issue: Poor fitness improvement
**Solutions**:
- Increase `hands_per_matchup` (more reliable evaluation)
- Increase `matchups_per_agent` (more diverse opponents)
- Adjust `mutation_sigma` (try 0.05 to 0.2)
- Increase `population_size` (more exploration)

### Issue: Overfitting warnings
**Meaning**: Training fitness much higher than evaluation fitness  
**Solutions**:
- Normal early in training (population adapting to each other)
- Increase opponent diversity in evaluation
- Use fixed evaluation opponents

---

## Related Scripts

**Training Scripts**:
- **`scripts/train.py`**: Main evolutionary training (uses this entire module)
- **`scripts/hyperparam_sweep.py`**: Quick hyperparameter search
- **`scripts/deep_hyperparam_sweep.py`**: Comprehensive hyperparameter optimization

**Analysis Scripts**:
- **`scripts/plot_history.py`**: Visualize fitness curves and training progress
- **`scripts/analyze_top_agents.py`**: Deep dive into elite agent performance
- **`scripts/analyze_convergence.py`**: Detect convergence patterns
- **`scripts/visualize_agent_behavior.py`**: Action distribution analysis

**Evaluation Scripts**:
- **`scripts/eval_baseline.py`**: Test trained agents vs baselines
- **`scripts/match_agents.py`**: Head-to-head agent comparison
- **`scripts/round_robin_agents_config.py`**: Tournament evaluation

---

## Future Enhancements

**Evolutionary Algorithm Improvements**:
- [ ] **CMA-ES** (Covariance Matrix Adaptation): Better for high-dimensional search
- [ ] **Novelty search**: Encourage diverse strategies, prevent convergence
- [ ] **Multi-objective optimization**: Balance BB/100, diversity, robustness
- [ ] **Adaptive mutation rates**: Per-genome learning rate adaptation
- [ ] **Island model**: Multiple populations with migration

**Training Strategy Improvements**:
- [ ] **Coevolution with opponent modeling**: Agents learn counter-strategies
- [ ] **Transfer learning**: Initialize from pre-trained networks
- [ ] **Curriculum learning**: Gradually increase opponent difficulty
- [ ] **Self-play with historical opponents**: Prevent strategy collapse
- [ ] **Meta-learning**: Learn to adapt quickly to new opponents

**Architecture Improvements**:
- [ ] **LSTM/GRU**: Temporal game state modeling
- [ ] **Attention mechanisms**: Focus on relevant game features
- [ ] **Residual connections**: Enable deeper networks
- [ ] **Ensemble models**: Combine multiple strategies

**Infrastructure Improvements**:
- [ ] **Distributed training**: Multi-machine parallelization
- [ ] **Automatic hyperparameter tuning**: Optuna, Ray Tune integration
- [ ] **Experiment tracking**: MLflow, Weights & Biases integration
- [ ] **Model versioning**: Track and compare agent versions

---

## Performance Tuning Guide

**For faster training**:
1. Install Numba: `pip install numba` (2-3× speedup)
2. Increase workers: `--workers 8` (linear speedup up to CPU count)
3. Reduce hands: `--hands 2000` (faster but noisier fitness)
4. Smaller population: `--pop 10` (less diversity but faster)

**For better agents**:
1. More generations: `--gens 200+` (more evolution time)
2. Larger population: `--pop 40+` (more exploration)
3. More hands: `--hands 5000+` (more accurate fitness)
4. More matchups: `--matchups 20+` (diverse opponents)

**For experimentation**:
1. Save frequently: Automatic checkpointing every generation
2. Resume capability: `--resume checkpoints/run_name`
3. Multiple seeds: Run with different `--seed` values
4. Hyperparameter sweeps: Use `deep_hyperparam_sweep.py`

---

## Integration with Engine

```python
from engine import PokerGame
from training import PolicyNetwork

# Create game
game = PokerGame(player_stacks=[1000] * 6, seed=42)

# Create AI
network = PolicyNetwork.from_genome(genome, network_config)

# Play
while not game.is_hand_over():
    current = game.state.current_player
    features = get_state_vector(game, current)
    mask = get_action_mask(game, current)
    action_idx = network.select_action(features, mask, rng)
    # ... apply action
```

See [engine/README.md](../engine/README.md) for engine details.

---

**For training questions, see main [README.md](../README.md) or open an issue.**

---

## 🆕 Recent Updates (January 2026)

### Hall of Fame Pre-loading Enhancements

The `EvolutionTrainer.initialize()` method has always supported `hof_weights` parameter, and now the training scripts make it easy to use:

**What's New**:
- `train.py` now has command-line arguments for HOF loading (`--hof-dir`, `--hof-paths`, `--hof-count`)
- No need for separate `train_with_hof.py` script
- Can combine with `--seed-weights` for transfer learning + strong opponents
- `deep_hyperparam_sweep.py` supports HOF loading for all sweep runs

**Why It Matters**:
Tournament analysis shows that small populations (p12) without HOF achieve only 33.8% win rate due to overfitting to weak self-play opponents. With proper HOF opponents, p12 can match larger populations while training 3× faster.

**Usage in Code**:
```python
from training import EvolutionTrainer, TrainingConfig
import numpy as np

# Load champion genomes
hof_weights = [
    np.load('checkpoints/champion1/best_genome.npy'),
    np.load('checkpoints/champion2/best_genome.npy'),
    np.load('checkpoints/champion3/best_genome.npy'),
]

# Create trainer and initialize with HOF
config = TrainingConfig(...)
trainer = EvolutionTrainer(config)
trainer.initialize(hof_weights=hof_weights)

# Train - population will compete against champions from gen 0
best = trainer.train()
```

**Command-Line Usage**:
```bash
# Using the training script
python scripts/training/train.py \
    --pop 12 --gens 100 \
    --hof-paths \
        checkpoints/champion1/best_genome.npy \
        checkpoints/champion2/best_genome.npy
```

### Convergence Status Detection

The training system now tracks convergence patterns to identify when configs need more training:

**Status Levels**:
1. **PLATEAUED**: No improvement in last 5 generations (<5 fitness gain)
   - Ready for evaluation and tournaments
   - Further training unlikely to help

2. **SLOW_IMPROVEMENT**: Small improvements (5-20 fitness gain in last 5 gens)
   - Nearly converged
   - May benefit from 10-20 more generations

3. **IMPROVING**: Moderate improvements (20-50 fitness gain)
   - Still learning at reasonable pace
   - Should continue training

4. **STRONGLY_IMPROVING**: Significant improvements (50+ fitness gain)
   - Learning curve is steep
   - Definitely needs more training
   - May achieve much higher fitness with extended runs

**Detection in Analysis Scripts**:
```python
def analyze_convergence(result):
    """Detect convergence status from training history."""
    best_progress = result['best_progress']
    last_5_gens = min(5, len(best_progress))
    last_improvement = best_progress[-1] - best_progress[-last_5_gens]
    
    if last_improvement > 50:
        return "STRONGLY_IMPROVING"
    elif last_improvement > 20:
        return "IMPROVING"
    elif last_improvement > 5:
        return "SLOW_IMPROVEMENT"
    else:
        return "PLATEAUED"
```

**Usage in Hyperparameter Sweeps**:
```bash
# Train only strongly improving configs
python scripts/training/deep_hyperparam_sweep.py \
    --strongly-improving-only \
    --generations 100

# Or filter by minimum status
python scripts/training/deep_hyperparam_sweep.py \
    --min-status IMPROVING \
    --generations 100
```

### Best Practices for Training

**Small Populations (p12-p20)**:
- ✅ **Always use HOF opponents** to prevent overfitting
- ✅ Use `--hof-count 5-10` for good opponent diversity
- ✅ Check convergence status - may plateau early
- ⚠️ Without HOF: Risk of local minima and weak generalization

**Large Populations (p40+)**:
- ✅ Better self-play diversity, HOF optional but helpful
- ✅ Longer training times but stronger final agents
- ✅ More resistant to overfitting

**Multi-Stage Training**:
```python
# Stage 1: Quick exploration with small population + HOF
config1 = TrainingConfig(
    evolution=EvolutionConfig(population_size=12),
    num_generations=50
)
trainer1 = EvolutionTrainer(config1)
trainer1.initialize(hof_weights=champions)
best1 = trainer1.train()

# Stage 2: Refinement with larger population, seed from stage 1
config2 = TrainingConfig(
    evolution=EvolutionConfig(population_size=40),
    num_generations=100
)
trainer2 = EvolutionTrainer(config2)
trainer2.initialize(seed_weights=best1.weights, hof_weights=champions)
best2 = trainer2.train()
```

### Checkpoint Management

**Timestamped Run Directories**:
All checkpoints now save to timestamped subdirectories to prevent overwriting:
```
checkpoints/
└── my_experiment/
    ├── evolution_run/
    │   └── tensorboard/
    └── runs/
        ├── run_20260127_143022/
        │   ├── best_genome.npy
        │   ├── population.npy
        │   ├── hall_of_fame.npy
        │   ├── state.json
        │   └── history.json
        └── run_20260127_151445/
            └── ...
```

**Benefits**:
- ✅ Never lose previous runs
- ✅ Can compare multiple runs of same config
- ✅ Easy to resume or analyze any run
- ✅ Safe for parallel training experiments

### Performance Monitoring

**Training Speed Expectations**:
- **With Numba**: ~4-6 sec/generation (p12-p20), ~8-12 sec/gen (p40)
- **Without Numba**: ~13 sec/generation (p12-p20), ~20-30 sec/gen (p40)
- **Install Numba**: `pip install numba` for 2-3× speedup

**Fitness Progression**:
- **First 10 gens**: Rapid improvement (often 50-200 BB/100)
- **Gens 10-30**: Steady growth (20-50 BB/100 per gen)
- **Gens 30-50**: Slowing (5-20 BB/100 per gen)
- **Gens 50+**: Plateau or slow improvement (<5 BB/100 per gen)

**When to Stop**:
- PLATEAUED status for 10+ generations
- Fitness stops improving
- Validation against fixed opponents shows no gains
- Time/compute budget exhausted

