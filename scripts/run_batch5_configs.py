#!/usr/bin/env python3
"""
Run Batch 5 configurations by calling train.py script.
Each configuration runs as an isolated subprocess for clean separation.

Batch 5 strategy:
  B4 confirmed σ=0.05 dominates MultiTable and σ=0.06/m=7 dominates HeadsUp.
  B5 narrows the sigma sweep around those findings, tests h=250 for HU,
  and only runs g50 (B4 confirmed g200 offers no benefit at σ≤0.06).

  Tracks:
    MT  — fine-sweep σ=0.04/0.045/0.05/0.06, seeded from B4 MT champion
    HU  — sweep h=250/375 × σ=0.05/0.06/0.07, seeded from B4 HU champion
    Cold-start control — best MT and HU configs without seeding (calibration)
    Cross-batch survivors — B3 survivor configs to confirm regression is real

  Seeds (B4 champions):
    MT seed: p12_m8_h500_s0.05_g50_b4_champion.npy  (#1 MT 98.5%, #1 Overall)
    HU seed: p12_m7_h375_s0.06_g50_b4_champion.npy  (#1 HU 82.7%)

  Why g50 only:
    B4 showed g50 beats g200 decisively at σ=0.05 (98.5% vs 48.7%).
    At σ≤0.06 the fitness landscape is smooth — 50 gens is sufficient to converge.
    Running g200 would cost 4× the compute for no gain.

  Total runs: 13 configs × g50 = 13 runs  (down from B4's 36)
"""
import sys
import subprocess
from pathlib import Path

# ── B4 champion seeds ────────────────────────────────────────────────────────
_CHAMP_DIR = Path(__file__).parent / 'hall_of_fame' / 'champions'
_CHAMP = {
    # B4 MultiTable champion — #1 MT (98.5%), #1 Overall (68.4%)
    'mt': str(_CHAMP_DIR / 'p12_m8_h500_s0.05_g50_b4_champion.npy'),
    # B4 HeadsUp champion — #1 HU (82.7%)
    'hu': str(_CHAMP_DIR / 'p12_m7_h375_s0.06_g50_b4_champion.npy'),
}

# ── Batch 5 configurations ───────────────────────────────────────────────────
configs = [

    # ── MultiTable track — fine-sweep σ below B4's winner ─────────────────
    # B4: σ=0.05 dominated MT. Does σ=0.04/0.045 do better? Does g50 still
    # converge, or does very low σ need more generations?
    # All seeded from B4 MT champion to start close to the proven policy basin.
    {
        'pop': 12, 'matchups': 8, 'hands': 500, 'sigma': 0.04,
        'seed_weights': _CHAMP['mt'],
        'note': 'MT track — below B4 floor, seeded. Confirms σ floor.',
    },
    {
        'pop': 12, 'matchups': 8, 'hands': 500, 'sigma': 0.045,
        'seed_weights': _CHAMP['mt'],
        'note': 'MT track — midpoint between 0.04 and 0.05, seeded.',
    },
    {
        'pop': 12, 'matchups': 8, 'hands': 500, 'sigma': 0.05,
        'seed_weights': _CHAMP['mt'],
        'note': 'MT track — B4 winning sigma, seeded. Expected best MT.',
    },
    {
        'pop': 12, 'matchups': 8, 'hands': 500, 'sigma': 0.06,
        'seed_weights': _CHAMP['mt'],
        'note': 'MT track — one step above B4 winner, seeded.',
    },

    # ── MultiTable cold-start controls ────────────────────────────────────
    # Verify that the seeded advantage is real, not just σ=0.05 being good
    # in general. If cold-start σ=0.05 also wins, seeding adds less value.
    {
        'pop': 12, 'matchups': 8, 'hands': 500, 'sigma': 0.04,
        'note': 'MT cold-start — σ=0.04 without seeding. Seeding benefit check.',
    },
    {
        'pop': 12, 'matchups': 8, 'hands': 500, 'sigma': 0.05,
        'note': 'MT cold-start — replicates B4 winner without seeding.',
    },

    # ── HeadsUp track — sweep σ and h, seeded from B4 HU champion ─────────
    # B4 HU: m=7 + σ=0.06 + h=375 won. Questions:
    #   1. Does h=250 (shorter matchups, faster feedback) help or hurt?
    #   2. Is σ=0.05 or σ=0.07 ever better at different hands counts?
    {
        'pop': 12, 'matchups': 7, 'hands': 375, 'sigma': 0.05,
        'seed_weights': _CHAMP['hu'],
        'heads_up_fraction': 1.0,
        'note': 'HU track — one below B4 HU sigma, h=375, seeded.',
    },
    {
        'pop': 12, 'matchups': 7, 'hands': 375, 'sigma': 0.06,
        'seed_weights': _CHAMP['hu'],
        'heads_up_fraction': 1.0,
        'note': 'HU track — B4 winning HU config, seeded. Expected best HU.',
    },
    {
        'pop': 12, 'matchups': 7, 'hands': 375, 'sigma': 0.07,
        'seed_weights': _CHAMP['hu'],
        'heads_up_fraction': 1.0,
        'note': 'HU track — one above B4 HU sigma, h=375, seeded.',
    },
    {
        'pop': 12, 'matchups': 7, 'hands': 250, 'sigma': 0.06,
        'seed_weights': _CHAMP['hu'],
        'heads_up_fraction': 1.0,
        'note': 'HU track — h=250 test. Faster per-gen feedback for HU.',
    },
    {
        'pop': 12, 'matchups': 7, 'hands': 250, 'sigma': 0.05,
        'seed_weights': _CHAMP['hu'],
        'heads_up_fraction': 1.0,
        'note': 'HU track — h=250 + lower sigma. Tests if h=250 enables tighter σ.',
    },

    # ── Cross-batch survivors — confirm B3→B4 regression is sustained ─────
    # These are the B3 survivor configs carried into B4. They underperformed.
    # Running them again in B5 confirms the regression isn't a one-off
    # and gives a stable performance floor for comparison.
    {
        'pop': 12, 'matchups': 8, 'hands': 500, 'sigma': 0.09,
        'note': 'B3 survivor — expect continued decline vs σ=0.05. Calibration.',
    },
    {
        'pop': 12, 'matchups': 7, 'hands': 500, 'sigma': 0.08,
        'note': 'B3 survivor — expect continued decline vs σ=0.06. Calibration.',
    },
]


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description='Run Batch 5 configs — σ fine-sweep + HU h-sweep'
    )
    parser.add_argument('--gens', '--generations', type=int, nargs='+', default=[50],
                        help='Generations to run (default: 50 — g200 not needed at low σ)')
    parser.add_argument('--output', default='hyperparam_results',
                        help='Output directory for sweep results')
    parser.add_argument('--seed', type=int, default=42,
                        help='Random seed base')
    parser.add_argument('--hof-count', type=int, default=3,
                        help='Maximum HoF opponents to load per run (default: 3)')
    parser.add_argument('--skip-existing', action='store_true',
                        help='Skip configs whose checkpoint directory already exists')
    parser.add_argument('--dry-run', action='store_true',
                        help='Print commands without running them')
    args = parser.parse_args()

    # Always load all current HoF champions as opponents
    champions_dir = Path(__file__).parent / 'hall_of_fame' / 'champions'
    champion_files = sorted(champions_dir.glob('*.npy'))
    if not champion_files:
        print("⚠️  No HoF champions found — training without fixed opponents")
        hof_args = []
    else:
        hof_args = ['--hof-paths'] + [str(f) for f in champion_files]
        print(f"📂 Will load {len(champion_files)} HoF champions as fixed opponents:")
        for f in champion_files:
            print(f"      {f.name}")

    print("=" * 70)
    print(f"BATCH 5 — {len(configs)} CONFIGS × {args.gens} GENS = "
          f"{len(configs) * len(args.gens)} RUNS")
    print("=" * 70)
    if args.dry_run:
        print("DRY RUN — commands will be printed but not executed")
    print()

    from datetime import datetime
    import json
    import time

    out_dir = Path(args.output) / f"b5_sweep_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    if not args.dry_run:
        out_dir.mkdir(parents=True, exist_ok=True)

    results = []
    total = len(configs) * len(args.gens)
    current = 0

    for gen_count in args.gens:
        for cfg in configs:
            current += 1

            # Build canonical checkpoint name
            seed_suffix = "_seeded" if cfg.get('seed_weights') else ""
            hu_suffix = ""
            if cfg.get('heads_up_fraction') == 1.0:
                hu_suffix = "_hu100"
            elif cfg.get('heads_up_fraction'):
                hu_suffix = f"_hu{int(cfg['heads_up_fraction'] * 100)}"
            name = (
                f"p{cfg['pop']}_m{cfg['matchups']}_h{cfg['hands']}"
                f"_s{cfg['sigma']}{hu_suffix}{seed_suffix}_hof3_g{gen_count}"
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

            # Auto-select workers
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
                    'config': {
                        'pop': cfg['pop'], 'matchups': cfg['matchups'],
                        'hands': cfg['hands'], 'sigma': cfg['sigma'],
                        'gens': gen_count, 'seeded': bool(cfg.get('seed_weights')),
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
        return

    # Summary
    completed = [r for r in results if r['status'] == 'completed' and r.get('final_fitness')]
    failed    = [r for r in results if r['status'] == 'failed']

    print("\n" + "=" * 70)
    print("BATCH 5 TRAINING SUMMARY")
    print("=" * 70)
    print(f"✅ Completed: {len(completed)}/{len(results)}")
    if failed:
        print(f"❌ Failed: {len(failed)}/{len(results)}")

    if completed:
        by_fitness = sorted(completed, key=lambda x: x['final_fitness'], reverse=True)
        print("\n🎯 Top 5 by Final Fitness:")
        for r in by_fitness[:5]:
            seeded = "seeded" if r['config']['seeded'] else "cold"
            print(f"  {r['name']:50s}  {r['final_fitness']:+7.1f}  [{seeded}]")

    print(f"\n📊 Results saved to: {out_dir}/results.json")
    print("\n✅ Done! Next step: run_batch5_tournament.py")


if __name__ == '__main__':
    main()
