"""Run the simulation, with a window or headless.

    python main.py                 # watch it live
    python main.py --headless      # run fast, print a summary, save CSVs to runs/
"""

import argparse
from pathlib import Path

from emergent_world.config import Config
from emergent_world.sim import Simulation


def main():
    parser = argparse.ArgumentParser(description="Emergent World simulation")
    parser.add_argument("--seed", type=int, default=0, help="random seed; same seed = same run")
    parser.add_argument("--ticks", type=int, default=5000, help="maximum ticks to run")
    parser.add_argument("--agents", type=int, default=None, help="starting agent count")
    parser.add_argument("--headless", action="store_true", help="no window, run as fast as possible")
    parser.add_argument("--random", action="store_true", help="random actions instead of brains (baseline)")
    parser.add_argument("--instincts", default="instincts.npz",
                        help="brain file from `python -m emergent_world.instincts` to start from")
    parser.add_argument("--blank", action="store_true", help="start from random brains, no instincts")
    parser.add_argument("--progress", type=int, default=1000, help="headless: print a progress line every N ticks")
    args = parser.parse_args()

    config = Config()
    if args.agents is not None:
        config.initial_agents = args.agents
    if args.random:
        config.policy = "random"
    if not args.blank and not args.random and Path(args.instincts).exists():
        config.instincts_path = args.instincts
        print(f"Starting from instincts in {args.instincts}")
    sim = Simulation(config, seed=args.seed)

    if args.headless:
        sim.run(args.ticks, progress_every=args.progress)
    else:
        from emergent_world.viewer import run_viewer
        run_viewer(sim, args.ticks)

    out = Path("runs") / f"seed_{args.seed}"
    sim.stats.save(out)
    print(f"Ran {sim.tick_count} ticks, {len(sim.living)} agents alive.")
    print(sim.stats.summary())
    print(f"Logs saved to {out}/")


if __name__ == "__main__":
    main()
