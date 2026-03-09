#!/usr/bin/env python3
"""
Run Batch 6 aggression-fix experiment by calling train.py script.
Each configuration runs as an isolated subprocess for clean separation.

Batch 6 strategy (2 configs only):
  B5 confirmed that the best architectures are:
    MT:  p12 / m=8 / h=500 / σ=0.04 / seeded — 100% MT win rate
    HU:  p12 / m=7 / h=375 / σ=0.06 / hu100 / seeded — 88.0% HU win rate

  B6 tests ONE structural change: fix for features[15].
    BEFORE: features[15] = 0.5  (constant placeholder, no information)
    AFTER:  features[15] = 1.0 if to_call > big_blind else 0.0  (facing_raise)

  This aligns the get_state_vector() inference path with the FeatureCache
  training path, which already used a real facing_raise signal at index 15.
  Self-play evaluation and tournament code now see a consistent, informative
  aggression signal instead of the dead 0.5 constant.

  Only the top B5 config per format is re-trained so we get a clean A/B:
    deep_p12_m8_h500_s0.04_seeded_hof3_g50       (B5 MT champion, fixed=False)
    deep_p12_m8_h500_s0.04_aggfix_seeded_hof4_g50  (B6 MT, fixed=True)
    ---
    deep_p12_m7_h375_s0.06_hu100_seeded_hof3_g50     (B5 HU champion, fixed=False)
    deep_p12_m7_h375_s0.06_hu100_aggfix_seeded_hof4_g50 (B6 HU, fixed=True)

  Seeds: B5 champions (start close to the proven policy basin).
  HoF:   All 4 active champions are used as fixed opponents (hof4).

  If aggfix agents beat their B5 counterparts in tournament → the fix matters.
  If they match → the training path already compensated for the dead feature.

  Total runs: 2 configs × g50 = 2 runs
"""
import sys
import subprocess
from pathlib import Path

# ── B5 champion seeds ────────────────────────────────────────────────────────
_CHAMP_DIR = Path(__file__).parent / 'hall_of_fame' / 'champions'
_CHAMP = {
    # B5 MultiTable champion — 100% MT win rate
    'mt': str(_CHAMP_DIR / 'p12_m8_h500_s0.04_g50_b5_champion.npy'),
    # B5 HeadsUp champion — 88.0% HU win rate
    'hu': str(_CHAMP_DIR / 'p12_m7_h375_s0.06_hu100_g50_b5_champion.npy'),
}

# ── Batch 6 configurations ───────────────────────────────────────────────────
configs = [

    # ── MultiTable — best B5 MT config with aggfix ────────────────────────
    # B5 winner: σ=0.04, m=8, h=500, seeded. Rerun with features[15] fixed.
    # Checkpoint suffix _aggfix_ distinguishes from identical B5 run.
    {
        'pop': 12, 'matchups': 8, 'hands': 500, 'sigma': 0.04,
        'seed_weights': _CHAMP['mt'],
        'note': (
            'MT aggfix — rerun of B5 MT champion with real facing_raise '
            'at features[15] instead of constant 0.5.'
        ),
    },

    # ── HeadsUp — best B5 HU config with aggfix ──────────────────────────
    # B5 winner: σ=0.06, m=7, h=375, hu100, seeded. Rerun with aggfix.
    {
        'pop': 12, 'matchups': 7, 'hands': 375, 'sigma': 0.06,
        'seed_weights': _CHAMP['hu'],
        'heads_up_fraction': 1.0,
        'note': (
            'HU aggfix — rerun of B5 HU champion with real facing_raise '
            'at features[15] instead of constant 0.5.'
        ),
    },
]


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description='Run Batch 6 aggfix experiment — 2 configs, aggression signal fix'
    )
    parser.add_argument('--gens', '--generations', type=int, nargs='+', default=[50],
                        help='Generations to run (default: 50)')
    parser.add_argument('--output', default='hyperparam_results',
                        help='Output directory for sweep results')
    parser.add_argument('--seed', type=int, default=42,
                        help='Random seed base')
    parser.add_argument('--skip-existing', action='store_true',
                        help='Skip configs whose checkpoint directory already exists')
    parser.add_argument('--dry-run', action='store_true',
                        help='Print commands without running them')
    args = parser.parse_args()

    # Always load all current HoF champions as opponents
    champions_dir = Path(__file__).parent / 'hall_of_fame' / 'champions'
    champion_files = sorted(f for f in champions_dir.glob('*.npy'))
    if not champion_files:
        print("⚠️  No HoF champions found — training without fixed opponents")
        hof_args = []
    else:
        hof_args = ['--hof-paths'] + [str(f) for f in champion_files]
        hof_count = len(champion_files)
        print(f"📂 Will load {hof_count} HoF champions as fixed opponents:")
        for f in champion_files:
            print(f"      {f.name}")

    hof_tag = f"hof{len(champion_files)}" if champion_files else "hof0"

    print("=" * 70)
    print(f"BATCH 6 AGGFIX — {len(configs)} CONFIGS × {args.gens} GENS = "
          f"{len(configs) * len(args.gens)} RUNS")
    print("=" * 70)
    print("Fix: features[15] = facing_raise  (was: hardcoded 0.5 placeholder)")
    print("=" * 70)
    if args.dry_run:
        print("DRY RUN — commands will be printed but not executed")
    print()

    from datetime import datetime
    import json
    import time

    out_dir = Path(args.output) / f"b6_aggfix_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    if not args.dry_run:
        out_dir.mkdir(parents=True, exist_ok=True)

    results = []
    total = len(configs) * len(args.gens)
    current = 0

    for gen_count in args.gens:
        for cfg in configs:
            current += 1

            # Build canonical checkpoint name
            # _aggfix_ tag distinguishes these B6 runs from identical B5 configs
            seed_suffix = "_seeded" if cfg.get('seed_weights') else ""
            hu_suffix = ""
            if cfg.get('heads_up_fraction') == 1.0:
                hu_suffix = "_hu100"
            elif cfg.get('heads_up_fraction'):
                hu_suffix = f"_hu{int(cfg['heads_up_fraction'] * 100)}"
            name = (
                f"p{cfg['pop']}_m{cfg['matchups']}_h{cfg['hands']}"
                f"_s{cfg['sigma']}{hu_suffix}_aggfix{seed_suffix}_{hof_tag}_g{gen_count}"
            )
            checkpoint_dir = Path("checkpoints") / f"deep_{name}"

            print(f"\n[{current}/{total}] {name}")
            if cfg.get('note'):
                print(f"  → {cfg['note']}")
            print("=" * 70)

            # Skip check
            runs_dir = checkpoint_dir / "runs"
            has_weights = runs_dir.exists() and any(runs_dir.rglob("best_genome.npy"))
            if args.skip_existing and has_weights:
                print(f"  ⏭  Skipping (checkpoint exists): {checkpoint_dir.name}")
                continue

            # Auto-select workers: >40 000 hands/gen → 8 workers (matches B5 policy)
            total_hands = cfg['pop'] * cfg['matchups'] * cfg['hands']
            workers = 8 if total_hands > 40000 else 1

            cmd = [
                'python3', 'scripts/training/train.py',
                '--pop',      str(cfg['pop']),
                '--matchups', str(cfg['matchups']),
                '--hands',    str(cfg['hands']),
                '--sigma',    str(cfg['sigma']),
                '--gens',     str(gen_count),
                '--workers',  str(workers),
                '--players',  '6',
                '--output',   str(checkpoint_dir),
                '--name',     'evolution_run',
                '--seed',     str(args.seed + current),
                '--checkpoint-interval', '999',
            ] + hof_args

            if cfg.get('heads_up_fraction'):
                cmd += ['--heads-up-fraction', str(cfg['heads_up_fraction'])]

            if cfg.get('seed_weights'):
                seed_path = cfg['seed_weights']
                if Path(seed_path).exists():
                    cmd += ['--seed-weights', seed_path]
                    print(f"  Seeded from: {Path(seed_path).name}")
                else:
                    print(f"  ⚠️  Seed weights not found: {seed_path}")
                    print(f"      Falling back to cold-start")

            print(f"  Config: pop={cfg['pop']}, m={cfg['matchups']}, "
                  f"h={cfg['hands']}, σ={cfg['sigma']}, g={gen_count}")
            print(f"  Hands/gen: {total_hands:,} | Workers: {workers}")

            if args.dry_run:
                print(f"  CMD: {' '.join(cmd)}")
                continue

            try:
                t0 = time.time()
                subprocess.run(cmd, check=True)
                elapsed = time.time() - t0
                print(f"\n  ✅ Completed in {elapsed:.1f}s")

                # Read final fitness
                final_fitness = None
                if (checkpoint_dir / 'runs').exists():
                    run_dirs = sorted((checkpoint_dir / 'runs').glob('run_*'))
                    if run_dirs:
                        state_file = run_dirs[-1] / 'state.json'
                        if state_file.exists():
                            with open(state_file) as f:
                                state = json.load(f)
                                final_fitness = state.get('best_fitness')

                results.append({
                    'name': name,
                    'note': cfg.get('note', ''),
                    'fix': 'aggfix — features[15] = facing_raise',
                    'config': {
                        'pop': cfg['pop'], 'matchups': cfg['matchups'],
                        'hands': cfg['hands'], 'sigma': cfg['sigma'],
                        'gens': gen_count, 'seeded': bool(cfg.get('seed_weights')),
                        'hu_fraction': cfg.get('heads_up_fraction', 0.0),
                    },
                    'hands_per_gen': total_hands,
                    'elapsed_s': elapsed,
                    'final_fitness': final_fitness,
                    'status': 'completed',
                })

            except subprocess.CalledProcessError as e:
                print(f"\n  ❌ Failed (exit {e.returncode})")
                results.append({'name': name, 'status': 'failed', 'error': str(e.returncode)})

            except KeyboardInterrupt:
                print("\n[Interrupted]")
                break

            # Save incrementally
            with open(out_dir / 'results.json', 'w') as f:
                json.dump(results, f, indent=2)

    if args.dry_run:
        print("\n✅ Dry run complete — 2 commands printed above.")
        print("   Run without --dry-run to execute.")
        return

    # Summary
    completed = [r for r in results if r['status'] == 'completed' and r.get('final_fitness')]
    failed    = [r for r in results if r['status'] == 'failed']

    print("\n" + "=" * 70)
    print("BATCH 6 AGGFIX TRAINING SUMMARY")
    print("=" * 70)
    print(f"✅ Completed: {len(completed)}/{len(results)}")
    if failed:
        print(f"❌ Failed: {len(failed)}/{len(results)}")

    if completed:
        by_fitness = sorted(completed, key=lambda x: x['final_fitness'], reverse=True)
        print("\n🎯 Final Fitness:")
        for r in by_fitness:
            print(f"  {r['name']:60s}  {r['final_fitness']:+7.1f}")

    print(f"\n📊 Results saved to: {out_dir}/results.json")
    print("\n✅ Done! Next step: python run_b6_tournament.py")


if __name__ == '__main__':
    main()
