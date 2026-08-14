# Hall of Fame

This directory contains the best performing agent genomes from tournament play and training.

## Storage Format

Each genome file should be stored with a descriptive name following this pattern:
```
{agent_name}_gen{generation}.npy
```

For example:
- `p12_m8_h500_s0.08_g200_best.npy`
- `p12_m6_h750_s0.1_g200_hof.npy`

## Selection Criteria

Agents should be included in the Hall of Fame if they meet one or more of these criteria:

1. **Tournament Champions**: Won or placed highly in round-robin tournaments
2. **High Win Rate**: Consistently achieve >60% win rate against diverse opponents
3. **Generation Milestones**: Best performers at key generation checkpoints (50, 100, 200, etc.)
4. **Hyperparameter Representatives**: Best example of specific hyperparameter configurations

## Directory Structure

```
hall_of_fame/
├── README.md                    # This file
├── champions/                   # Tournament winners
├── milestones/                  # Generation milestone best performers
└── archived/                    # Previously top performers, now superseded
```

## Usage

These genomes can be loaded and used as:
- Training opponents for new agents
- Baseline comparisons for new hyperparameter configurations
- Starting points for continued evolution
- Reference implementations for behavior analysis

## Maintenance

Regularly review and update this collection based on tournament results and training checkpoints.

### Automated Update Checking

Use the Hall of Fame update checker to automatically identify candidates:
```bash
# Check for any updates needed
python scripts/utilities/check_hof_updates.py

# Only check recent runs (last 7 days)
python scripts/utilities/check_hof_updates.py --days 7

# Generate shell script to update HoF automatically
python scripts/utilities/check_hof_updates.py --generate-script
```

The checker analyzes:
- Recent training checkpoints for high-fitness genomes
- Tournament results for consistent winners
- Milestone generations (50, 100, 200, etc.)

### Manual Analysis

Use the tournament history analyzer to identify candidates:
```bash
python scripts/analysis/analyze_tournament_history.py --top-n 10
```

## Performance Impact

**Hall of Fame training provides significant benefits** - see detailed analyses:
- [HOF_IMPACT_ANALYSIS.md](../docs/HOF_IMPACT_ANALYSIS.md) - Focused HoF impact study
- [TRAINING_FINDINGS_REPORT.md](../docs/TRAINING_FINDINGS_REPORT.md) - Comprehensive research report

**Key Results**:
- **+52.2% relative improvement** in average win rate
- **+59.8% more chips** earned on average
- **Top 7 agents all use HoF training**
- **Champion agent (80.2% win rate)** trained with HoF opponents

**Key Finding**: Training with Hall of Fame opponents prevents overfitting to self-play and enables smaller populations to achieve excellent generalization.
