# Scripts Directory

**Complete guide to all training, evaluation, analysis, and utility scripts**

---

## 📋 Quick Reference

| Script | Purpose | When to Use |
|--------|---------|-------------|
| [train.py](#trainpy) | Main training | Train new poker AI agents (includes HoF support) |
| [eval_baseline.py](#eval_baselinepy) | Agent evaluation | Test trained agent vs baselines |
| [match_agents.py](#match_agentspy) | Head-to-head matches | Compare two specific agents |
| [round_robin_agents_config.py](#round_robin_agents_configpy) | Tournament | Find best agent among all trained |
| [extract_hyperparameter_relationships.py](#extract_hyperparameter_relationshipspy) | Mathematical analysis | Derive scaling laws and optimal configurations |
| [hyperparam_sweep.py](#hyperparam_sweeppy) | Standard sweep | Find good hyperparameters (self-play) |
| [hyperparam_sweep_with_benchmark.py](#hyperparam_sweep_with_benchmarkpy) | Benchmark sweep | Fair hyperparameter comparison |
| [hyperparam_sweep_with_hof.py](#hyperparam_sweep_with_hofpy) | HoF sweep | Small population optimization |
| [deep_hyperparam_sweep.py](#deep_hyperparam_sweeppy) | Extended training | Deep dive into best configs |
| [plot_history.py](#plot_historypy) | Training visualization | See fitness curves and progress |
| [analyze_top_agents.py](#analyze_top_agentspy) | Agent analysis | Deep dive into agent performance |
| [analyze_tournament_history.py](#analyze_tournament_historypy) | Tournament analysis | Analyze multiple tournament results |
| [visualize_agent_behavior.py](#visualize_agent_behaviorpy) | Behavior analysis | Understand agent decision patterns |
| [visualize_hyperparameter_relationships.py](#visualize_hyperparameter_relationshipspy) | Relationship visualization | Generate hyperparameter relationship diagrams |
| [cleanup_checkpoints.py](#cleanup_checkpointspy) | Disk management | Free up storage space |

---

## 🎯 Training Scripts

### train.py

**Purpose**: Main evolutionary training script for creating poker AI agents

**When to Use**:
- Starting a new training run from scratch
- Resuming interrupted training
- Training with specific hyperparameters

**Usage**:
```bash
# Quick test (5 generations, ~30 seconds)
python scripts/train.py --quick

# Standard training (50 generations, ~4-5 minutes)
python scripts/train.py

# Full production run (200 generations, ~15-20 minutes)
python scripts/train.py --production

# Custom configuration
python scripts/train.py \
    --pop 40 \              # Population size
    --gens 100 \            # Generations
    --hands 3000 \          # Hands per matchup
    --matchups 12 \         # Matchups per agent
    --workers 4 \           # Parallel workers
    --seed 42               # Random seed

# Resume from checkpoint
python scripts/train.py --resume checkpoints/evolution_run
```

**Output**:
- `checkpoints/evolution_run/` - Training checkpoints
- `checkpoints/evolution_run/best_genome.npy` - Best agent
- `checkpoints/evolution_run/history.json` - Training history
- `checkpoints/evolution_run/config.json` - Configuration used

**Time**: ~4-6 seconds per generation (with Numba)

---

### train.py with Hall of Fame Pre-loading

**Purpose**: Train with Hall of Fame opponents pre-loaded (prevents overfitting for small populations)

**When to Use**:
- Training small populations (p12, p16) that need strong opponents
- Want faster training without sacrificing quality
- Following tournament analysis recommendations
- Testing "Elite Training" approach (small pop + strong HoF)

**Key Benefit**: Small populations normally overfit to weak self-play opponents. Pre-loading strong HoF opponents forces training against skilled adversaries from the start.

**Usage**:
```bash
# Train p12 with HoF opponents from a checkpoint directory
python scripts/training/train.py \
    --pop 12 \
    --matchups 8 \
    --hands 500 \
    --sigma 0.1 \
    --hof-dir checkpoints/deep_p40_m6_h500_s0.15/evolution_run \
    --hof-count 5 \
    --gens 100

# Train with specific HoF opponents from multiple checkpoints
python scripts/training/train.py \
    --pop 20 \
    --matchups 6 \
    --hands 500 \
    --sigma 0.1 \
    --hof-paths \
        checkpoints/deep_p40_m8_h375_s0.1/evolution_run/best_genome.npy \
        checkpoints/deep_p40_m6_h500_s0.15/evolution_run/best_genome.npy \
        checkpoints/deep_p20_m6_h500_s0.15/evolution_run/best_genome.npy \
    --gens 100

# Combine with seed weights for transfer learning + strong opponents
python scripts/training/train.py \
    --pop 12 \
    --matchups 8 \
    --hands 500 \
    --sigma 0.1 \
    --seed-weights checkpoints/pretrained/best_genome.npy \
    --hof-dir checkpoints/champions \
    --hof-count 5 \
    --gens 100
```

**Key Parameters**:
- `--tournament-winners`: Auto-load top tournament winners (recommended)
- `--hof-dir`: Directory containing best_genome.npy, hall_of_fame.npy, or population.npy
- `--hof-paths`: Specific .npy files to load as HoF opponents
- `--hof-count`: Maximum number of HoF opponents to load
- All standard training params: --pop, --matchups, --hands, --sigma, --gens, --seed

**Output**:
- Same as train.py but with HoF opponents included from generation 0
- `checkpoints/evolution_run/` or custom --output directory

**💡 Tournament Insight**: p12 without HoF achieved 33.8% win rate. With proper HoF opponents, p12 can match larger populations while training 3x faster!

**Time**: ~2-3 seconds per generation (faster than larger populations)

---

### hyperparam_sweep.py

**Purpose**: Hyperparameter search with custom parameter grids (evaluates via self-play)

**When to Use**:
- Before starting full training runs
- Testing different population sizes, mutation rates
- Finding best hands/matchups settings
- Quick exploration of parameter space

**Usage**:
```bash
# Default parameter grid
python scripts/training/hyperparam_sweep.py

# Custom parameter grid
python scripts/training/hyperparam_sweep.py \
    --pop 16 20 30 \
    --matchups 4 6 8 \
    --hands 375 500 750 \
    --sigma 0.1 0.15 \
    --gens 30

# Explore around tournament winner (p40_m8_h375_s0.1)
python scripts/training/hyperparam_sweep.py \
    --pop 30 40 50 \
    --matchups 8 10 12 \
    --hands 300 375 450 \
    --sigma 0.08 0.1 0.12 \
    --gens 50

# Quick single config test
python scripts/training/hyperparam_sweep.py \
    --pop 20 \
    --matchups 6 \
    --hands 500 \
    --sigma 0.1 \
    --gens 10
```

**Key Parameters**:
- `--pop`: Population sizes to test
- `--matchups`: Matchups per agent to test
- `--hands`: Hands per matchup to test
- `--sigma`: Mutation sigma values to test
- `--gens`: Generations per config (default: 15)
- `--seed`: Random seed (default: 42)

**Output**:
- `hyperparam_results/sweep_YYYYMMDD_HHMMSS/results.json` - All results
- `hyperparam_results/sweep_YYYYMMDD_HHMMSS/report.txt` - Summary
- Console output with ranked configurations

**⚠️ Important**: Training fitness values are NOT comparable across configs because each trains against different self-play opponents. Use [hyperparam_sweep_with_benchmark.py](#hyperparam_sweep_with_benchmarkpy) for fair comparison.

**Follow-up**:
```bash
# Analyze convergence
python scripts/analysis/analyze_convergence.py

# Generate visualizations
python scripts/analysis/visualize_hyperparam_sweep.py
```

---

### hyperparam_sweep_with_benchmark.py

**Purpose**: Hyperparameter search WITH fixed benchmark evaluation for fair comparison

**When to Use**:
- Need directly comparable fitness values across configs
- Evaluating small vs large populations fairly
- Preparing results for publication/reporting
- Avoiding self-play fitness inflation

**Key Difference**: Each config is evaluated against the SAME fixed opponents (tournament winners), not just its own training population. This provides apples-to-apples comparison.

**Usage**:
```bash
# Default benchmark sweep
python scripts/training/hyperparam_sweep_with_benchmark.py

# Custom parameter grid with benchmark evaluation
python scripts/training/hyperparam_sweep_with_benchmark.py \
    --pop 12 20 30 40 \
    --matchups 4 6 8 \
    --hands 500 750 1000 \
    --sigma 0.1 0.15 0.2 \
    --gens 30

# Explore optimal region identified from tournaments
python scripts/training/hyperparam_sweep_with_benchmark.py \
    --pop 30 40 50 \
    --matchups 8 10 12 \
    --hands 300 375 450 \
    --sigma 0.08 0.1 0.12 \
    --gens 50 \
    --benchmark-hands 500
```

**Key Parameters**:
- `--benchmark-hands`: Hands per benchmark matchup (default: 500)
- All standard sweep parameters (--pop, --matchups, --hands, --sigma, --gens)

**Output**:
- `hyperparam_results/benchmark_sweep_YYYYMMDD_HHMMSS/results.json`
- Each result includes:
  - `training_fitness`: Fitness during training (self-play)
  - `benchmark_fitness`: Fitness vs fixed opponents (COMPARABLE)
  - `benchmark_details`: Per-opponent results

**Time**: Slower than standard sweep due to benchmark evaluation (~2x)

---

### hyperparam_sweep_with_hof.py

**Purpose**: Hyperparameter sweep WITH Hall of Fame opponents pre-loaded (critical for small populations)

**When to Use**:
- Training small populations (p12, p16) that overfit to weak self-play
- Need strong opponents during training
- Exploring budget-friendly configurations
- Testing if small pop + strong HoF = large pop performance

**Key Feature**: Loads tournament winners or checkpoint opponents into Hall of Fame before training starts. Small populations train against strong adversaries instead of weak self-play opponents.

**Usage**:
```bash
# P12 sweep with top tournament winners as HoF opponents
python scripts/training/hyperparam_sweep_with_hof.py \
    --pop 12 \
    --matchups 6 8 10 \
    --hands 375 500 750 \
    --sigma 0.08 0.1 0.12 \
    --tournament-winners \
    --gens 50

# Use top 5 tournament winners (instead of default 3)
python scripts/training/hyperparam_sweep_with_hof.py \
    --pop 12 20 \
    --matchups 8 \
    --hands 500 \
    --sigma 0.1 \
    --tournament-winners \
    --hof-count 5 \
    --gens 50

# Load HoF from specific checkpoint directory
python scripts/training/hyperparam_sweep_with_hof.py \
    --pop 12 \
    --matchups 8 \
    --hands 500 \
    --sigma 0.1 \
    --hof-dir checkpoints/deep_p40_m6_h500_s0.15/evolution_run \
    --gens 50

# Load specific checkpoint files as HoF opponents
python scripts/training/hyperparam_sweep_with_hof.py \
    --pop 12 \
    --matchups 8 \
    --hands 500 \
    --sigma 0.1 \
    --hof-paths \
        checkpoints/deep_p40_m8_h375_s0.1/evolution_run/best_genome.npy \
        checkpoints/deep_p40_m6_h500_s0.15/evolution_run/best_genome.npy \
    --gens 50
```

**Key Parameters**:
- `--tournament-winners`: Auto-load top tournament winners (recommended)
- `--hof-dir`: Directory with best_genome.npy, hall_of_fame.npy, or population.npy
- `--hof-paths`: Specific .npy files to load
- `--hof-count`: Max HoF opponents to load (default: 3 for --tournament-winners)

**Output**:
- `hyperparam_results/sweep_hof_YYYYMMDD_HHMMSS/results.json`
- `hyperparam_results/sweep_hof_YYYYMMDD_HHMMSS/report.txt`
- Each result includes `hof_opponent_count`

**💡 Pro Tip**: Tournament results show p12 without HoF = 33.8% win rate, but p12 with strong HoF can match larger populations!

---

### deep_hyperparam_sweep.py

**Purpose**: Extended training runs for best configurations (longer generations)

**When to Use**:
- After initial sweep identifies top performers
- Need to train configs for 100-200 generations
- Testing convergence and long-term performance
- Final optimization before production deployment

**Two Modes**:
1. **From Previous Sweep**: Automatically selects top N configs from latest sweep
2. **Custom Grid**: Specify your own parameter combinations

**Usage**:
```bash
# Extend top 5 configs from latest sweep to 100 generations
python scripts/training/deep_hyperparam_sweep.py \
    --top 5 \
    --generations 100

# Only include configs that are still improving
python scripts/training/deep_hyperparam_sweep.py \
    --top 5 \
    --generations 100 \
    --min-status IMPROVING

# Custom parameter grid (ignores previous sweeps)
python scripts/training/deep_hyperparam_sweep.py \
    --pop 30 40 50 \
    --matchups 8 10 12 \
    --hands 300 375 450 \
    --sigma 0.08 0.1 0.12 \
    --generations 100

# Single config deep dive (200 generations)
python scripts/training/deep_hyperparam_sweep.py \
    --pop 40 \
    --matchups 8 \
    --hands 375 \
    --sigma 0.1 \
    --generations 200

# Dry run (see commands without executing)
python scripts/training/deep_hyperparam_sweep.py \
    --top 5 \
    --generations 100 \
    --dry-run
```

**Key Parameters**:
- `--top N`: Number of configs from previous sweep to extend
- `--min-status`: Minimum convergence status (PLATEAUED, SLOW_IMPROVEMENT, IMPROVING, STRONGLY_IMPROVING)
- `--pop`, `--matchups`, `--hands`, `--sigma`: Custom parameter grid (overrides --top)
- `--generations`: Generations for deep run (default: 100)
- `--dry-run`: Print commands without running

**Output**:
- Launches `scripts/train.py` for each config
- Saves to `checkpoints/deep_p{pop}_m{matchups}_h{hands}_s{sigma}/`

**Time**: 1-3 hours depending on generations and number of configs

---

## 📊 Evaluation Scripts

### eval_baseline.py

**Purpose**: Evaluate trained agent against baseline opponents (random, heuristic)

**When to Use**:
- After training completes
- Testing agent strength
- Comparing different training runs

**Usage**:
```bash
# Evaluate best agent
python scripts/eval_baseline.py checkpoints/evolution_run/best_genome.npy

# Multiple games for more reliable results
python scripts/eval_baseline.py checkpoints/evolution_run/best_genome.npy --games 1000
```

**Output**:
- Win rates vs RandomAgent and HeuristicAgent
- BB/100 statistics
- Console summary

---

### match_agents.py

**Purpose**: Head-to-head match between two specific agents

**When to Use**:
- Comparing two training runs
- Testing which hyperparameters produced better agent
- Debugging agent performance

**Usage**:
```bash
# Basic match (10,000 hands)
python scripts/match_agents.py \
    --agent1 checkpoints/run1/best_genome.npy \
    --arch1 "17 64 32 6" \
    --agent2 checkpoints/run2/best_genome.npy \
    --arch2 "17 64 32 6"

# More hands for reliable results
python scripts/match_agents.py \
    --agent1 checkpoints/run1/best_genome.npy \
    --arch1 "17 64 32 6" \
    --agent2 checkpoints/run2/best_genome.npy \
    --arch2 "17 64 32 6" \
    --hands 50000

# Enable detailed logging (for debugging)
python scripts/match_agents.py \
    --agent1 agent1.npy \
    --arch1 "17 64 32 6" \
    --agent2 agent2.npy \
    --arch2 "17 64 32 6" \
    --log
```

**Output**:
- Final chip counts
- Winner determination
- Match logs in `match_logs/` (if --log enabled)

**Time**: ~30-60 seconds for 10,000 hands

---

### round_robin_agents_config.py

**Purpose**: Tournament between all trained agents to find the best

**When to Use**:
- After multiple training runs completed
- Comparing different hyperparameter configurations
- Finding overall best agent

**Usage**:
```bash
# Run full tournament (all agents vs all agents)
python scripts/round_robin_agents_config.py
```

**Requirements**:
- Multiple agents in `checkpoints/*/runs/*/best_genome.npy`
- Each agent folder has `config.json`

**Output**:
- `tournament_reports/tournament_YYYYMMDD_HHMMSS/` - Timestamped results
  - `report.json` - Detailed matchup data
  - `wins_losses.png` - Win/loss bar chart
  - `parameter_performance.png` - Which configs perform best
  - `head_to_head_heatmap.png` - All matchup results
  - `chip_distribution.png` - Total chips per agent

**Time**: 5-15 minutes depending on number of agents

---

## 📈 Analysis Scripts

### plot_history.py

**Purpose**: Visualize training progress with fitness curves

**When to Use**:
- After training run completes
- Checking if training converged
- Comparing multiple training runs

**Usage**:
```bash
# Plot single training run
python scripts/plot_history.py checkpoints/evolution_run/

# Compare multiple runs
python scripts/plot_history.py \
    checkpoints/run1/ \
    checkpoints/run2/ \
    checkpoints/run3/
```

**Output**:
- Fitness curves (mean, best, diversity)
- PNG files saved to checkpoint directory

---

### analyze_top_agents.py

**Purpose**: Deep performance analysis of elite agents

**When to Use**:
- Understanding why top agents perform well
- Comparing elite vs average agents
- Strategy analysis

**Usage**:
```bash
# Analyze top 5 agents from a run
python scripts/analyze_top_agents.py checkpoints/evolution_run/

# Analyze more agents
python scripts/analyze_top_agents.py checkpoints/evolution_run/ --top 10
```

**Output**:
- Performance statistics per agent
- Win rate breakdowns
- Strategy patterns
- Console report

---

### analyze_convergence.py

**Purpose**: Detect if hyperparameter sweep configs have converged

**When to Use**:
- After running hyperparameter sweeps
- Before deciding which config to use for full training
- Determining if more generations needed

**Usage**:
```bash
# Analyze most recent sweep
python scripts/analyze_convergence.py

# Analyze specific sweep
python scripts/analyze_convergence.py --sweep-dir hyperparam_results/sweep_20260126_120000
```

**Output**:
- `convergence_analysis.txt` - Detailed convergence patterns
- Warnings if configs still improving
- Recommendations for full training

---

### analyze_tournament_history.py

**Purpose**: Comprehensive analysis of multiple tournament results to identify patterns and trends

**When to Use**:
- After running multiple tournament rounds (Batch 1, Batch 2, etc.)
- Need cumulative statistics across all tournaments
- Want to identify consistently strong performers
- Need hyperparameter correlation analysis with visual charts
- Comparing head-to-head matchup statistics

**What it Analyzes**:
- Cumulative win rates across all tournaments
- Agent consistency (chip variance)
- Hyperparameter performance patterns
- Head-to-head matchup matrices
- Development recommendations

**Usage**:
```bash
# Analyze all tournaments (default)
python scripts/analysis/analyze_tournament_history.py

# Only include agents that played in 3+ tournaments
python scripts/analysis/analyze_tournament_history.py --min-tournaments 3

# Show top 15 agents instead of default 10
python scripts/analysis/analyze_tournament_history.py --top-n 15

# Both filters combined
python scripts/analysis/analyze_tournament_history.py --min-tournaments 5 --top-n 20
```

**Requirements**:
- Tournament reports in `tournament_reports/*/tournament_*/report.json`
- Optional: `matplotlib`, `numpy` for visualizations

**Output**:
- `tournament_reports/overall_reports/[Batch]_Report/`
  - `analysis_report.txt` - Comprehensive text report
  - `analysis_report.json` - Machine-readable data
  - `head_to_head_analysis.txt` - Matchup statistics
- Console summary with ranked agents

**Generated Report Sections**:
1. **Agent Rankings**: Win rates, chip earnings, consistency metrics
2. **Hyperparameter Correlations**: Which parameters correlate with success
3. **Development Recommendations**: Best performers, configs to retire
4. **Head-to-Head Analysis**: Detailed matchup statistics

**Visualizations** (if matplotlib available):
- Win rate distribution charts
- Hyperparameter performance heatmaps
- Agent consistency plots
- Head-to-head matchup matrices

**Time**: 5-30 seconds depending on number of tournaments

---

### visualize_agent_behavior.py

**Purpose**: Understand agent decision-making patterns

**When to Use**:
- Debugging strange agent behavior
- Understanding learned strategies
- Comparing aggressive vs conservative agents

**Usage**:
```bash
# Visualize single agent
python scripts/visualize_agent_behavior.py checkpoints/evolution_run/best_genome.npy

# Compare multiple agents
python scripts/visualize_agent_behavior.py \
    checkpoints/run1/best_genome.npy \
    checkpoints/run2/best_genome.npy
```

**Output**:
- Action distribution heatmaps
- Position-based strategy charts
- Hand strength vs action plots
- PNG visualizations

---

### visualize_hyperparam_sweep.py

**Purpose**: Generate comprehensive visualizations from hyperparameter sweeps

**When to Use**:
- After running hyperparam_sweep.py or deep_hyperparam_sweep.py
- Need visual comparison of configurations
- Presenting results

**Usage**:
```bash
# Visualize most recent sweep
python scripts/visualize_hyperparam_sweep.py

# Visualize specific sweep
python scripts/visualize_hyperparam_sweep.py --sweep-dir hyperparam_results/sweep_20260126_120000
```

**Requirements**:
- `matplotlib`, `seaborn` installed
- Sweep results in `hyperparam_results/`

**Output**:
- `visualizations/` folder with multiple plots:
  - Comparison plots (box plots, violin plots)
  - Parameter heatmaps
  - Learning curves
  - Best configuration highlights

---

### extract_hyperparameter_relationships.py

**Purpose**: Derive mathematical scaling laws and optimal hyperparameter configurations from empirical sweep data

**When to Use**:
- After collecting substantial sweep data (multiple sweep directories)
- Need mathematical formulas for optimal hyperparameter selection
- Want to understand Hall of Fame impact quantitatively
- Research and publication of scaling laws
- Designing optimal configurations for new population sizes

**Key Features**:
1. **Mathematical Relationship Derivation**: Fits curves to derive formulas like σ_optimal = 0.458/√p
2. **Hall of Fame Impact Analysis**: Quantifies HOF performance boost (+144% improvement)
3. **Population-Specific Optimization**: Finds optimal configurations for each population size
4. **Predictive Modeling**: Extrapolates to untested hyperparameter combinations
5. **Comprehensive Visualizations**: Generates 6 different charts and heatmaps
6. **Research-Quality Reports**: Produces detailed markdown reports with mathematical formulations

**Usage**:
```bash
# Analyze single sweep (basic analysis)
python scripts/analysis/extract_hyperparameter_relationships.py hyperparam_results/sweep_20260129_062341

# Multi-sweep analysis (recommended - more comprehensive)
python scripts/analysis/extract_hyperparameter_relationships.py \
    hyperparam_results/sweep_20260123_211525 \
    hyperparam_results/sweep_hof_20260127_133129 \
    hyperparam_results/sweep_hof_20260129_062341 \
    hyperparam_results/sweep_hof_20260202_181109

# Auto-detect latest sweep
python scripts/analysis/extract_hyperparameter_relationships.py
```

**Requirements**:
- `scipy` for mathematical curve fitting
- `matplotlib`, `seaborn` for visualizations (optional)
- Sweep data in `hyperparam_results/` directories
- Each sweep must contain `results.json` files

**Output** (saved to `hyperparam_results/analysis/`):
- **Report**: `hyperparameter_analysis_report.md` - Comprehensive mathematical analysis
- **Visualizations**: 6 charts showing relationships and predictions
  - `hyperparameter_effects.png` - Individual parameter effects
  - `mathematical_relationships.png` - Fitted curves and formulas
  - `population_specific_optima.png` - Optimal configs per population
  - `predictions.png` - Extrapolations to untested configurations
  - `heatmap_*.png` - Interaction heatmaps
- **HOF Analysis**: `hall_of_fame_members_analysis.txt` - Elite genome tracking

**Mathematical Relationships Discovered**:
- **Population ↔ Sigma**: σ_optimal = 0.458/√p (mutation rate scales with population)
- **Population ↔ Matchups**: Small pops (p≤20): m≈0.64p, Large pops (p≥40): m≈0.17p
- **Matchups ↔ Hands**: Variety > Depth (prioritize matchups over hands)
- **Hall of Fame Impact**: +144% fitness improvement over non-HOF configurations

**Key Insights**:
- **Champion Configuration**: p12_m6_h375_s0.1_hof3 (5213.36 BB/100)
- **Population Optimum**: 12 agents provide +117% improvement
- **HOF Critical**: Hall of Fame is the single most important hyperparameter
- **Scaling Laws**: Provides mathematical formulas for designing untested configurations

**Prediction Capabilities**:
- Optimal sigma for any population size using σ = 0.458/√p
- Optimal matchups using population-dependent scaling rules
- Expected fitness for untested hyperparameter combinations
- Resource allocation guidance (matchups vs hands budget)

**HOF Member Tracking**:
- Tracks specific Hall of Fame genomes used during training
- Shows which elite solutions influenced each configuration
- Enables understanding of opponent quality impact
- Compatible with enhanced training system HOF tracking

**Time**: 10-30 seconds depending on data size

**See Also**: 
- [HOF_MEMBER_TRACKING_IMPLEMENTATION.md](../HOF_MEMBER_TRACKING_IMPLEMENTATION.md) - HOF tracking system
- [HYPERPARAMETER_RELATIONSHIPS.md](../docs/HYPERPARAMETER_RELATIONSHIPS.md) - Detailed mathematical analysis

---

### visualize_hyperparameter_relationships.py

**Purpose**: Generate publication-quality visualizations showing empirical hyperparameter relationships

**When to Use**:
- After completing multiple tournament rounds
- Need to understand proven design rules
- Presenting research findings
- Designing new configurations based on data

**What it Shows**:
1. **Population ↔ Matchups**: How population size affects optimal matchup count
2. **Matchups ↔ Hands**: Tradeoff between variety and depth in fitness evaluation
3. **Population ↔ Sigma**: Inverse relationship between diversity and mutation rate
4. **Comprehensive Overview**: Box plots, scatter plots, and top config rankings

**Usage**:
```bash
# Generate all relationship visualizations
python scripts/analysis/visualize_hyperparameter_relationships.py
```

**Requirements**:
- `matplotlib`, `seaborn` installed
- Tournament data from Batch 1 & 2 (built-in)

**Output** (saved to `tournament_reports/hyperparameter_analysis/`):
- `relationship_1_population_vs_matchups.png` - Ratio analysis and optimal zones
- `relationship_2_matchups_vs_hands.png` - Total evaluations sweet spot
- `relationship_3_population_vs_sigma.png` - Empirical formula: σ ≈ 0.5/√pop
- `comprehensive_overview.png` - All relationships and top configurations

**Key Findings Visualized**:
- Large populations (p40+) use 15-25% matchup ratio
- Small populations (p12) need 50-67% matchup ratio
- Optimal total evaluations: 3,000-4,500 (matchups × hands)
- More matchups better than more hands per matchup
- Sigma decreases as population increases

**See Also**: [HYPERPARAMETER_RELATIONSHIPS.md](../docs/HYPERPARAMETER_RELATIONSHIPS.md) for detailed analysis

---

### report_deep_sweep.py

**Purpose**: Generate detailed text report from deep hyperparameter sweep

**When to Use**:
- After deep_hyperparam_sweep.py completes
- Need summary of which configs performed best

**Usage**:
```bash
# Generate report from most recent deep sweep
python scripts/report_deep_sweep.py
```

**Output**:
- `deep_sweep_report.txt` - Ranked configurations by fitness
- Console summary

---

## 🧪 Testing & Debugging Scripts

### test_ai_hands.py

**Purpose**: Test agent decisions on specific poker scenarios

**When to Use**:
- Debugging agent behavior
- Testing specific situations (bluffing, pot odds, etc.)
- Validating agent logic

**Usage**:
```bash
# Test specific scenarios
python scripts/test_ai_hands.py

# Test with specific agent
python scripts/test_ai_hands.py --agent checkpoints/evolution_run/best_genome.npy
```

**Output**:
- Agent decisions for predefined scenarios
- Console output with reasoning

---

### test_ai_features.py

**Purpose**: Verify feature extraction is working correctly

**When to Use**:
- Debugging training issues
- Ensuring input features are correct
- Testing feature engineering changes

**Usage**:
```bash
# Test feature extraction
python scripts/test_ai_features.py
```

**Output**:
- Feature vector examples
- Validation checks
- Console report

---

### test_cli.py

**Purpose**: Interactive poker game for testing engine

**When to Use**:
- Testing game engine manually
- Debugging game logic
- Playing against agents interactively

**Usage**:
```bash
# Start interactive game
python scripts/test_cli.py
```

**Controls**:
- `f` - Fold
- `c` - Check/Call
- `r <amount>` - Raise
- `a` - All-in
- `q` - Quit

---

### benchmark_jit.py

**Purpose**: Measure Numba JIT compilation speedup

**When to Use**:
- Verifying Numba is installed correctly
- Measuring optimization impact
- Performance tuning

**Usage**:
```bash
# Run benchmark suite
python scripts/benchmark_jit.py
```

**Output**:
- Speedup measurements for each JIT function
- With vs without Numba comparison
- Console report

**Expected**: 2-3× speedup with Numba enabled

---

## 🛠️ Utility Scripts

### cleanup_checkpoints.py

**Purpose**: Free up disk space by removing old training runs

**When to Use**:
- Running low on disk space
- After training many experimental runs
- Before archiving project

**Usage**:
```bash
# Keep only 5 most recent checkpoints
python scripts/cleanup_checkpoints.py --keep 5

# Keep checkpoints from last 7 days
python scripts/cleanup_checkpoints.py --older-than 7

# Dry run (see what would be deleted)
python scripts/cleanup_checkpoints.py --dry-run --keep 3
```

**⚠️ Warning**: Deleted checkpoints cannot be recovered!

---

## 🔄 Typical Workflow

### 1️⃣ Initial Training
```bash
# Quick test to verify setup
python scripts/train.py --quick

# Standard training run
python scripts/train.py --pop 20 --gens 100
```

### 2️⃣ Hyperparameter Optimization
```bash
# Quick sweep to narrow options
python scripts/hyperparam_sweep.py

# Visualize results
python scripts/visualize_hyperparam_sweep.py

# Deep sweep on promising configs
python scripts/deep_hyperparam_sweep.py

# Generate report
python scripts/report_deep_sweep.py
```

### 3️⃣ Production Training
```bash
# Train with best hyperparameters
python scripts/train.py --production --pop 40 --sigma 0.15
```

### 4️⃣ Evaluation & Analysis
```bash
# Plot training progress
python scripts/plot_history.py checkpoints/evolution_run/

# Evaluate vs baselines
python scripts/eval_baseline.py checkpoints/evolution_run/best_genome.npy

# Analyze behavior
python scripts/visualize_agent_behavior.py checkpoints/evolution_run/best_genome.npy
```

### 5️⃣ Tournament
```bash
# Run tournament between all trained agents
python scripts/round_robin_agents_config.py

# View results in tournament_reports/tournament_YYYYMMDD_HHMMSS/
```

---

## 📦 Required vs Optional Scripts

### ✅ Required (Core Functionality)
- **train.py** - Essential for training
- **match_agents.py** - Used by tournament scripts
- **eval_baseline.py** - Standard evaluation

### 🎯 Highly Recommended
- **round_robin_agents_config.py** - Find best agent
- **plot_history.py** - Visualize progress
- **hyperparam_sweep.py** - Optimize training

### 📊 Analysis Tools
- **analyze_top_agents.py** - Deep analysis
- **analyze_tournament_history.py** - Multi-tournament analysis
- **visualize_agent_behavior.py** - Strategy insights
- **analyze_convergence.py** - Convergence detection

### 🔧 Utilities
- **cleanup_checkpoints.py** - Disk management
- **benchmark_jit.py** - Performance verification
- **check_hof_updates.py** - Hall of Fame update checker
- **test_*.py** - Testing and debugging

### 🏆 Hall of Fame Management
- **check_hof_updates.py** - Analyzes recent training runs and tournament results to identify genomes that should be added to the Hall of Fame. Checks for new champions (fitness ≥ 70), milestone genomes (gen 50/100/200), and strong performers. Can optionally generate a shell script to automate the updates.

**Usage:**
```bash
# Check for any updates needed
python scripts/utilities/check_hof_updates.py

# Only check recent runs (last 7 days)
python scripts/utilities/check_hof_updates.py --days 7

# Set custom fitness threshold
python scripts/utilities/check_hof_updates.py --min-fitness 65

# Generate shell script to update HoF automatically
python scripts/utilities/check_hof_updates.py --generate-script

# Verbose output
python scripts/utilities/check_hof_updates.py --verbose
```

### 🧩 Sweep Integrity Tools
- **check_sweep_missing.py** - Utility to identify which hyperparameter sweep configurations have not been run. Use this to ensure all intended parameter combinations are present in your sweep results and to catch missing or failed runs.

**Usage:**
```bash
python scripts/utilities/check_sweep_missing.py --results hyperparam_results/sweep_YYYYMMDD_HHMMSS/results.json --expected-grid <grid_spec>
```
Refer to the script for argument details and grid specification format.

### 🚀 Advanced
- **deep_hyperparam_sweep.py** - Thorough optimization
- **report_deep_sweep.py** - Report generation
- **visualize_hyperparam_sweep.py** - Visual analysis

---

## ⚡ Performance Tips

**Faster Training**:
- Install Numba: `pip install numba` (2-3× speedup)
- Increase workers: `--workers 8`
- Reduce hands for quick tests: `--hands 1000`

**Better Results**:
- More generations: `--gens 200+`
- Larger population: `--pop 40+`
- More hands: `--hands 5000+`
- Use hyperparameter sweeps first

**Debugging**:

Use `--quick` flag for fast iterations
Enable logging with `--log` flag
Test with `test_ai_hands.py`
Check features with `test_ai_features.py`

---
### Batch Inference (Forward Batch Integration)

All training and evaluation scripts use batched neural network inference for major speedups. This is automatic if Numba is installed. To benchmark or verify batching:

```bash
python scripts/utilities/benchmark_jit.py
```

See [FORWARD_BATCH_INTEGRATION.md](../FORWARD_BATCH_INTEGRATION.md) for technical details.


### Convergence Status Detection

**Purpose**: Automatically detect the convergence status of each training configuration in hyperparameter sweeps and deep sweeps.

**How it works**:
- Analyzes the fitness curve of each config over the last 5 generations.
- Assigns one of four statuses:
  - **PLATEAUED**: No improvement in last 5 generations (ready for evaluation)
  - **SLOW_IMPROVEMENT**: 5-20 fitness gain in last 5 generations (almost done)
  - **IMPROVING**: 20-50 fitness gain in last 5 generations (needs more time)
  - **STRONGLY_IMPROVING**: 50+ fitness gain in last 5 generations (train longer!)
- Used by sweep analysis and deep sweep scripts to filter, select, and extend configs intelligently.

**Usage**:
  - The status is reported in sweep result summaries and can be used with `--min-status` or `--strongly-improving-only` flags in deep sweep scripts.
  - Example:
    ```bash
    python scripts/training/deep_hyperparam_sweep.py --min-status IMPROVING --generations 100
    python scripts/training/deep_hyperparam_sweep.py --strongly-improving-only --generations 100
    ```

**Benefit**: Saves compute by focusing training on configs that are still improving, and helps identify when a config is ready for evaluation or further training.

## 🆘 Troubleshooting

**Script won't run**:
- Check Python version: `python --version` (need 3.8+)
- Install dependencies: `pip install -r requirements.txt`
- Check current directory: `pwd` (should be PokerBot root)

**Out of memory**:
- Reduce `--workers`
- Reduce `--pop` (population size)
- Use `cleanup_checkpoints.py` to free space

**Slow performance**:
- Install Numba: `pip install numba`
- Verify with `benchmark_jit.py`
- Check CPU usage (should use all cores)

**Results not improving**:
- Try hyperparameter sweep
- Increase training time (more generations)
- Check convergence with `analyze_convergence.py`

---

**For more information, see main [README.md](../README.md)**

---

## 🆕 Recent Enhancements (January 2026)

### deep_hyperparam_sweep.py - New Features

**Sweep Directory Selection**
```bash
# Specify exact sweep to use instead of always using latest
python scripts/training/deep_hyperparam_sweep.py \
  --sweep-dir sweep_hof_20260127_133129 \
  --top 3 \
  --generations 100
```

**Multi-Generation Training**
```bash
# Train same configs for multiple generation counts in one command
python scripts/training/deep_hyperparam_sweep.py \
  --top 3 \
  --generations 50 200  # Trains each config for both 50 and 200 gens
```

**Strongly Improving Filter**
```bash
# Auto-select only configs that are still improving significantly
python scripts/training/deep_hyperparam_sweep.py \
  --strongly-improving-only \
  --generations 100

# Combine with --top for top N strongly improving
python scripts/training/deep_hyperparam_sweep.py \
  --strongly-improving-only \
  --top 3 \
  --generations 50 200
```

**Hall of Fame Integration**
```bash
# All deep sweep runs now support HOF opponents
python scripts/training/deep_hyperparam_sweep.py \
  --top 5 \
  --generations 100 \
  --hof-paths \
    checkpoints/champion1/best_genome.npy \
    checkpoints/champion2/best_genome.npy

# Or use a directory
python scripts/training/deep_hyperparam_sweep.py \
  --strongly-improving-only \
  --generations 50 200 \
  --hof-dir checkpoints/tournament_winner \
  --hof-count 5
```

**Optional --top Parameter**
```bash
# Without --top, trains ALL configs matching the status filter
python scripts/training/deep_hyperparam_sweep.py \
  --min-status IMPROVING \
  --generations 100  # Trains all IMPROVING and STRONGLY_IMPROVING configs
```

### train.py - Hall of Fame Integration

The main training script now has built-in HOF support (no separate `train_with_hof.py` needed):

**Loading HOF from Directory**
```bash
python scripts/training/train.py \
  --pop 12 \
  --matchups 8 \
  --hands 500 \
  --sigma 0.1 \
  --gens 100 \
  --hof-dir checkpoints/deep_p40_m8_h375_s0.1/runs/run_20260126_093215 \
  --hof-count 5
```

**Loading Specific HOF Genomes**
```bash
python scripts/training/train.py \
  --pop 12 \
  --gens 100 \
  --hof-paths \
    checkpoints/champion1/best_genome.npy \
    checkpoints/champion2/best_genome.npy \
    checkpoints/champion3/best_genome.npy
```

**Combined with Seed Weights (Transfer Learning + Strong Opponents)**
```bash
python scripts/training/train.py \
  --pop 12 \
  --gens 100 \
  --seed-weights checkpoints/pretrained/best_genome.npy \
  --hof-dir checkpoints/champions \
  --hof-count 10
```

**What HOF Loading Does**:
- Pre-loads strong agents into Hall of Fame before training starts
- Your population trains against these champions from generation 0
- Prevents overfitting to weak self-play opponents
- Especially critical for small populations (p12, p16)
- Tournament data shows p12 with HOF matches larger populations at 3× speed

### Convergence Status Detection

The sweep analysis now detects 4 convergence statuses:

- **PLATEAUED**: No improvement in last 5 generations (ready for evaluation)
- **SLOW_IMPROVEMENT**: 5-20 fitness gain in last 5 gens (almost done)
- **IMPROVING**: 20-50 fitness gain in last 5 gens (needs more time)
- **STRONGLY_IMPROVING**: 50+ fitness gain in last 5 gens (train longer!)

Use `--min-status` and `--strongly-improving-only` to filter configs intelligently.

### Best Practices

**For Small Populations (p12-p20)**:
```bash
# Always use HOF opponents to prevent overfitting
python scripts/training/train.py --pop 12 --gens 100 \
  --hof-dir checkpoints/tournament_winner --hof-count 5
```

**For Deep Sweeps**:
```bash
# 1. Find top performers with initial sweep
python scripts/training/hyperparam_sweep_with_hof.py --pop 12 --gens 50

# 2. Train top 3 + strongly improving for multiple generation counts
python scripts/training/deep_hyperparam_sweep.py \
  --top 3 --generations 50 200 --hof-paths <champions>

python scripts/training/deep_hyperparam_sweep.py \
  --strongly-improving-only --generations 100 --hof-paths <champions>

# 3. Analyze results and run tournaments
python scripts/analysis/analyze_convergence.py
python scripts/evaluation/round_robin_agents_config.py
```

**For Production Training**:
```bash
# Use proven hyperparameters with long training + HOF
python scripts/training/train.py \
  --pop 40 \
  --matchups 8 \
  --hands 375 \
  --sigma 0.1 \
  --gens 200 \
  --hof-dir checkpoints/champions \
  --hof-count 10
```

