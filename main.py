"""Run the simulation, with a window or headless.

    python main.py                 # watch the real world live, starting from founders
    python main.py --headless      # run fast, print progress, save CSVs to runs/

The clock is 1 tick = 1 hour. The real world starts from the founders evolved in
prehistory (founders.npz) and gives them long lives (--years). Without a founders
file it falls back to instincts.npz, then to random brains.
"""

import argparse
from pathlib import Path

from emergent_world.config import TICKS_PER_YEAR, Config, format_time
from emergent_world.sim import Simulation


def main():
    parser = argparse.ArgumentParser(description="Emergent World simulation")
    parser.add_argument("--seed", type=int, default=0, help="random seed; same seed = same run")
    parser.add_argument("--years", type=float, default=2.0, help="average lifespan in years")
    parser.add_argument("--run-years", type=float, default=10.0, help="how many years to simulate")
    parser.add_argument("--people", type=int, default=12, help="how many founders start the world")
    parser.add_argument("--max-people", type=int, default=40, help="population cap")
    parser.add_argument("--children", type=float, default=3.0,
                        help="roughly how many children an agent can have in a lifetime")
    parser.add_argument("--story", action="store_true",
                        help="headless: print the followed agent's life as it happens")
    parser.add_argument("--headless", action="store_true", help="no window, run as fast as possible")
    parser.add_argument("--founders", default="founders.npz",
                        help="population file from `python -m emergent_world.prehistory`")
    parser.add_argument("--instincts", default="instincts.npz",
                        help="brain file from `python -m emergent_world.instincts` (used without founders)")
    parser.add_argument("--blank", action="store_true", help="start from random brains, no founders or instincts")
    parser.add_argument("--random", action="store_true", help="random actions instead of brains (baseline)")
    parser.add_argument("--progress", type=int, default=24 * 30,
                        help="headless: print a progress line every N ticks (default: every 30 days)")
    args = parser.parse_args()

    # min_population=2: top-ups only step in to prevent extinction, not to fill the world.
    config = Config(garden_ticks=0, founder_count=args.people, initial_agents=args.people,
                    max_population=args.max_people, min_population=2).with_lifespan_years(args.years)
    # Children are spaced so a full life fits about --children of them after adulthood.
    config.cooldown_fraction = (1 - config.maturity_fraction) / max(args.children, 0.1)
    if args.random:
        config.policy = "random"
    elif not args.blank and Path(args.founders).exists():
        config.founders_path = args.founders
        print(f"Starting from founders in {args.founders}")
    elif not args.blank and Path(args.instincts).exists():
        config.instincts_path = args.instincts
        print(f"No founders file; starting from instincts in {args.instincts}")
    else:
        config.garden_ticks = 30_000  # blank brains need the gentle start
        print("Starting from random brains")
    print(f"Average lifespan {args.years} years; adults at {format_time(config.maturity_age)}")
    sim = Simulation(config, seed=args.seed)
    sim.follow(max(sim.agents, key=lambda a: a.age, default=None))
    if args.story:
        def tell(agent, tick, text):
            print(f"{format_time(tick):<18} #{agent.id:<4} {text}", flush=True)
        sim.on_event = tell
        followed = sim.by_id.get(sim.followed_id)
        if followed is not None:
            print(f"Following #{followed.id}, aged {followed.age // 24} days")

    ticks = int(args.run_years * TICKS_PER_YEAR)
    if args.headless:
        sim.run(ticks, progress_every=0 if args.story else args.progress)
    else:
        from emergent_world.viewer import run_viewer
        run_viewer(sim, ticks)

    out = Path("runs") / f"seed_{args.seed}"
    sim.stats.save(out)
    print(f"Ran to {format_time(sim.tick_count)}, {len(sim.living)} agents alive.")
    print(sim.stats.summary())
    print(f"Logs saved to {out}/")


if __name__ == "__main__":
    main()
