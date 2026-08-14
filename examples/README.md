# Examples

**Practical example scripts demonstrating advanced usage patterns**

---

## Overview

This directory contains complete, runnable examples that demonstrate how to use the PokerBot training system for various use cases. Each example is self-contained and can be run directly or used as a template for your own scripts.

---

## Available Examples

### train_vs_champions.py

**Purpose**: Train new agents against proven Hall of Fame opponents

**What it demonstrates**:
- Loading tournament winner genomes from checkpoints
- Pre-loading HoF opponents before training starts
- Configuring training with small populations + strong adversaries
- Using the `EvolutionTrainer` API directly (not through CLI)

**When to use this approach**:
- Training small populations (p12-p20) that would overfit to weak self-play
- Want to ensure agents face strong opponents from generation 0
- Experimenting with elite training strategies
- Creating custom training pipelines

**Usage**:
```bash
# Edit the script to specify your HoF model paths
python examples/train_vs_champions.py
```

**Configuration shown**:
- Population: 12 agents
- Matchups: 6 per agent
- Hands: 500 per matchup
- Generations: 50
- HoF opponents: 4 tournament winners

**Expected output**:
- Training runs with HoF opponents included from start
- Results saved to `checkpoints/vs_tournament_winners/`
- Can compare against standard training without HoF

**Key insight**: Tournament data shows p12 with HoF opponents can match larger populations while training 3× faster!

---

## Creating Your Own Examples

### Template Structure

```python
#!/usr/bin/env python3
"""
Brief description of what this example demonstrates.
"""

import numpy as np
from pathlib import Path
from training.evolution import EvolutionTrainer
from training.config import TrainingConfig, NetworkConfig, EvolutionConfig, FitnessConfig

# 1. Load any pre-trained models or HoF opponents
# ...

# 2. Configure training
config = TrainingConfig(
    network=NetworkConfig(...),
    evolution=EvolutionConfig(...),
    fitness=FitnessConfig(...),
    num_generations=50,
    experiment_name='my_experiment',
)

# 3. Initialize trainer
trainer = EvolutionTrainer(config)

# 4. (Optional) Add HoF opponents
# trainer.hall_of_fame.extend(hof_weights)

# 5. Run training
trainer.train()

# 6. Analyze results
print(f"Best fitness: {trainer.best_fitness}")
```

### Common Patterns

**Loading checkpoints**:
```python
from pathlib import Path
import numpy as np

checkpoint_path = Path('checkpoints/my_run/best_genome.npy')
if checkpoint_path.exists():
    weights = np.load(checkpoint_path)
```

**Multiple HoF opponents**:
```python
hof_models = [
    'checkpoints/agent1/best_genome.npy',
    'checkpoints/agent2/best_genome.npy',
]
hof_weights = [np.load(p) for p in hof_models if Path(p).exists()]
```

**Transfer learning (seed weights)**:
```python
seed_weights = np.load('checkpoints/pretrained/best_genome.npy')
config = TrainingConfig(
    # ... other config
    seed_weights=seed_weights,
)
```

---

## Comparison with CLI Scripts

### CLI Approach (scripts/training/train.py)
- Best for standard workflows
- Command-line interface
- Pre-configured defaults
- Automatic checkpoint management

### Python API Approach (examples/)
- Best for custom experiments
- Full programmatic control
- Easy to extend and modify
- Can integrate with notebooks or pipelines

**Both approaches use the same underlying training system**, so results are equivalent.

---

## Recommended Workflows

### 1. Quick Experiments
Use CLI scripts for standard training:
```bash
python scripts/training/train.py --pop 20 --gens 50
```

### 2. Advanced Customization
Use examples as templates:
```bash
# Copy and modify an example
cp examples/train_vs_champions.py my_experiment.py
# Edit my_experiment.py
python my_experiment.py
```

### 3. Integration with Analysis
Combine Python API with analysis scripts:
```python
# In your script
trainer.train()
# Then use CLI tools
# python scripts/analysis/plot_history.py checkpoints/my_experiment
```

---

## Tips

**Reproducibility**:
- Always set `seed` in TrainingConfig for reproducible results
- Save your config: `config.to_json('experiment_config.json')`

**Performance**:
- Install Numba for 2-3× speedup: `pip install numba`
- Use more workers: `config.num_workers = 8`
- Profile before optimizing: `python -m cProfile my_script.py`

**Debugging**:
- Start with small populations (p10-p12) for faster iteration
- Use fewer generations (--gens 5) to test changes quickly
- Enable verbose logging if needed

---

## Related Documentation

- [scripts/README.md](../scripts/README.md) - Complete CLI scripts reference
- [training/README.md](../training/README.md) - Training system internals
- [SWEEP_WORKFLOW_GUIDE.md](../docs/SWEEP_WORKFLOW_GUIDE.md) - Hyperparameter optimization workflows
- [HOF_IMPACT_ANALYSIS.md](../docs/HOF_IMPACT_ANALYSIS.md) - Hall of Fame training benefits

---

## Contributing Examples

Have a useful example? Add it here!

**Good examples**:
- Demonstrate a specific use case or pattern
- Include clear documentation and comments
- Are self-contained and runnable
- Show practical applications

**Example ideas**:
- Transfer learning from pre-trained models
- Multi-stage training pipelines
- Custom fitness functions
- Integration with external tools
- Specific poker scenarios (tournaments, heads-up, etc.)
