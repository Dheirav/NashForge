# Hyperparameter Sweep Workflow Guide

## Quick Start

### Running a Hyperparameter Sweep

```bash
# Basic sweep with Hall of Fame opponents
python3 scripts/training/hyperparam_sweep_with_hof.py \
  --pop 12 20 \
  --matchups 6 8 \
  --hands 375 500 \
  --sigma 0.08 0.1 \
  --tournament-winners \
  --gens 50
```

The sweep will automatically:
1. Load tournament-winning champions from `hall_of_fame/champions/`
2. Run all 2×2×2×2 = 16 configuration combinations
3. Save results to `hyperparam_results/sweep_hof_YYYYMMDD_HHMMSS/`
4. Embed sweep configuration in `results.json`

### Checking for Missing Configurations

After a sweep is interrupted or incomplete:

```bash
# Check which configs are missing
python3 scripts/utilities/check_sweep_missing.py hyperparam_results/sweep_hof_20260129_062341
```

Output example:
```
Directory:        hyperparam_results/sweep_hof_20260129_062341
Total Expected:   216
Completed:        180
Missing:          36
Progress:         83% (180/216)

To complete missing configs:
python3 scripts/training/hyperparam_sweep_with_hof.py \
  --pop 12 \
  --matchups 7 \
  --hands 375 \
  --sigma 0.07 0.08 \
  --tournament-winners \
  --gens 40
```

The script automatically extracts which specific values are missing and suggests the exact re-run command!

### Analyzing Results

```bash
# Visualize all results with plots and statistics
python3 scripts/analysis/visualize_hyperparam_sweep.py hyperparam_results/sweep_hof_20260129_062341

# Analyze convergence patterns
python3 scripts/analysis/analyze_convergence.py hyperparam_results/sweep_hof_20260129_062341

# Deep training runs for best configs
python3 scripts/training/deep_hyperparam_sweep.py --top 5 --generations 200
```

---

## Advanced Usage

### Using Latest Sweep Automatically

```bash
# Check latest sweep for missing configs
python3 scripts/utilities/check_sweep_missing.py

# Analyze latest sweep
python3 scripts/analysis/visualize_hyperparam_sweep.py
```

### Custom Sweep Without Hall of Fame

```bash
# Pure self-play (no HoF)
python3 scripts/training/hyperparam_sweep.py \
  --pop 40 \
  --matchups 8 \
  --hands 375 500 \
  --sigma 0.1 0.12 \
  --gens 100
```

### Benchmark Comparison Sweep

```bash
# Evaluate against fixed benchmark opponents
python3 scripts/training/hyperparam_sweep_with_benchmark.py \
  --pop 20 30 40 \
  --matchups 6 8 10 \
  --hands 375 500 \
  --sigma 0.1 \
  --gens 50
```

### Deep Dives on Best Configs

```bash
# Train top 5 from latest sweep for 200 generations
python3 scripts/training/deep_hyperparam_sweep.py \
  --top 5 \
  --generations 50 200

# Only train configs that are still improving
python3 scripts/training/deep_hyperparam_sweep.py \
  --strongly-improving-only \
  --generations 100 200

# Custom grid for deep dive
python3 scripts/training/deep_hyperparam_sweep.py \
  --pop 40 \
  --matchups 8 10 \
  --hands 375 500 \
  --sigma 0.08 0.1 \
  --generations 200
```

---

## Understanding the New Results Format

### Old Format (Deprecated)
```json
[
  { "name": "p12_...", "config": {...}, ... },
  { "name": "p20_...", "config": {...}, ... },
  ...
]
```

### New Format (Current)
```json
{
  "sweep_input": {
    "pop": [12, 20, 40],
    "matchups": [6, 8, 10],
    "hands": [375, 500],
    "sigmas": [0.08, 0.1],
    "generations": 50,
    "hof_count": 3,
    "timestamp": "2026-02-02T10:30:45.123456"
  },
  "results": [
    { "name": "p12_m6_...", "config": {...}, ... },
    { "name": "p12_m8_...", "config": {...}, ... },
    ...
  ]
}
```

**Benefits**:
- Complete sweep specification is preserved
- No need to remember/type parameters for follow-up sweeps
- Easy to reproduce the exact same sweep later
- Automatic detection of missing configs

---

## Common Workflows

### Scenario 1: Interrupted Sweep

```bash
# Sweep got interrupted at 60% completion
python3 scripts/utilities/check_sweep_missing.py hyperparam_results/sweep_hof_20260129_062341

# Output suggests exact re-run command with missing configs only
python3 scripts/training/hyperparam_sweep_with_hof.py \
  --pop 20 40 \
  --matchups 7 9 \
  --hands 300 600 \
  --sigma 0.075 0.085 \
  --tournament-winners \
  --gens 40
```

### Scenario 2: Quick Exploration

```bash
# Run quick sweep
python3 scripts/training/hyperparam_sweep_with_hof.py \
  --pop 30 \
  --matchups 8 \
  --hands 375 \
  --sigma 0.08 0.1 \
  --tournament-winners \
  --gens 20

# Analyze results
python3 scripts/analysis/visualize_hyperparam_sweep.py

# Deep dive on best config
python3 scripts/training/deep_hyperparam_sweep.py --top 1 --generations 200
```

### Scenario 3: Systematic Exploration

```bash
# Phase 1: Coarse sweep (quick, few generations)
python3 scripts/training/hyperparam_sweep_with_hof.py \
  --pop 20 40 60 \
  --matchups 6 8 10 \
  --hands 375 500 \
  --sigma 0.08 0.1 0.12 \
  --tournament-winners \
  --gens 50

# Analyze and identify promising configs
python3 scripts/analysis/analyze_convergence.py

# Phase 2: Fine sweep around best configs
python3 scripts/training/deep_hyperparam_sweep.py \
  --top 3 \
  --generations 50 200 \
  --tournament-winners
```

---

## Output Structure

### After Running a Sweep:
```
hyperparam_results/
└── sweep_hof_20260202_103045/
    ├── results.json              # New format with sweep_input + results
    ├── report.txt                # Human-readable summary
    └── visualizations/           # (if analysis ran)
        ├── final_metrics_comparison.png
        ├── fitness_progression.png
        ├── hyperparameter_heatmaps.png
        └── analysis_report.txt
```

### After Checking for Missing:
```
hyperparam_results/
└── missing_sweeps/
    └── sweep_hof_20260202_103045/
        ├── missing_20260202T103045Z.json      # Missing config list (JSON)
        ├── missing_20260202T103045Z.txt       # Missing config list (TXT)
        ├── run_input_20260202T103045Z.json    # Re-run instructions
        ├── latest_missing.json                # Pointer to latest
        └── latest_missing.txt                 # Pointer to latest
```

---

## Tips & Best Practices

### 1. Always Use Tournament Winners for Small Populations
```bash
# ✅ Good: p12 with HoF (prevents overfitting)
python3 scripts/training/hyperparam_sweep_with_hof.py \
  --pop 12 \
  --matchups 8 \
  --hands 500 \
  --tournament-winners \
  --gens 100

# ❌ Avoid: p12 without HoF (will overfit to self-play opponents)
```

### 2. Check Convergence Status Before Deep Dives
```bash
# Analyze which configs are still improving
python3 scripts/analysis/analyze_convergence.py

# Then deep dive only on promising ones
python3 scripts/training/deep_hyperparam_sweep.py \
  --strongly-improving-only \
  --generations 200
```

### 3. Use Consistent Naming for Easy Tracking
```bash
# Good: Descriptive directory names
sweep_hof_population_exploration_20260202
sweep_sigma_tuning_20260202
sweep_matchups_optimization_20260202

# Track experiments with different purposes
```

### 4. Save Missing Configs Before Restarting
```bash
# Save to persistent location before restarting machine
python3 scripts/utilities/check_sweep_missing.py \
  hyperparam_results/sweep_XXX \
  --out-dir /backup/missing_sweeps

# Later, re-run from backup:
cat /backup/missing_sweeps/sweep_XXX/missing_latest.txt
```

---

## Troubleshooting

### "sweep_input not found in results.json"
This means the results.json was created with an old version of the sweep runner.
- **Solution**: Re-run the sweep with the updated scripts
- **Workaround**: Manually specify parameters with `--pops`, `--matchups`, etc. (old interface - deprecated)

### "No HoF opponents loaded"
- **Check**: `hall_of_fame/champions/` directory exists
- **Check**: Contains `.npy` files
- **Solution**: Run `python3 scripts/training/train.py --output hall_of_fame/champions/` to create champions

### Script errors with old results.json
- **Status**: Old results still work with analysis scripts
- **Note**: `check_sweep_missing.py` requires new format with embedded sweep_input
- **Migration**: No action needed - keep both old and new results

---

## API Reference

### check_sweep_missing.py

```bash
python3 scripts/utilities/check_sweep_missing.py [sweep_path] [--out-dir OUTPUT_DIR]

Arguments:
  sweep_path      Path to sweep folder or results.json (optional, uses latest if omitted)
  --out-dir       Where to save missing lists (default: hyperparam_results/missing_sweeps)

Returns:
  - Prints completion report to stdout
  - Saves missing configuration lists
  - Generates re-run suggestion command
```

### New results.json Structure

```python
{
  "sweep_input": {
    "pop": List[int],
    "matchups": List[int],
    "hands": List[int],
    "sigmas": List[float],
    "generations": int,
    "hof_count": Optional[int],
    "timestamp": str  # ISO format
  },
  "results": List[Dict]  # Same as before
}
```

---

## Questions?

See the main documentation:
- [GLOBAL_SYNTHESIS_REPORT.md](GLOBAL_SYNTHESIS_REPORT.md) - Overall training findings
- [HYPERPARAMETER_RELATIONSHIPS.md](HYPERPARAMETER_RELATIONSHIPS.md) - Validated parameter relationships
- [SWEEP_REFACTORING_SUMMARY.md](SWEEP_REFACTORING_SUMMARY.md) - Technical changes
