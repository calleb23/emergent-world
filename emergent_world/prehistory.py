"""Prehistory: evolve founders quickly, then start long-lived worlds from them.

    python -m emergent_world.prehistory            # writes founders.npz

Creatures here have the same hourly body clock as the real world (same hunger,
thirst and poison timing) but live only about five weeks, so thousands of
generations pass quickly. They start from the teacher's instincts and evolve
under food-limited selection. The survivors at the end become the founders:
a whole population with genuinely different brains, not copies of one.

Instincts depend on how fast needs drain, not on how long a creature lives,
so what evolves here carries straight over to long lives.
"""

import argparse
from pathlib import Path

import numpy as np

from emergent_world.agents.brain import HIDDEN_SIZE, OUTPUT_SIZE, Brain
from emergent_world.agents.senses import INPUT_SIZE
from emergent_world.config import Config
from emergent_world.sim import Simulation


def save_founders(brains: list, path: Path, generations: int):
    np.savez(path,
             w1=np.stack([b.w1 for b in brains]), b1=np.stack([b.b1 for b in brains]),
             w2=np.stack([b.w2 for b in brains]), b2=np.stack([b.b2 for b in brains]),
             generations=generations)


def load_founders(path) -> list:
    data = np.load(path)
    if data["w1"].shape[1:] != (INPUT_SIZE, HIDDEN_SIZE) or data["w2"].shape[1:] != (HIDDEN_SIZE, OUTPUT_SIZE):
        raise ValueError(f"{path} doesn't match the current brain shape; rerun prehistory.")
    return [Brain(w1, b1, w2, b2) for w1, b1, w2, b2
            in zip(data["w1"], data["b1"], data["w2"], data["b2"])]


def run_prehistory(ticks: int, seed: int, instincts: str, progress_every: int = 0,
                   **overrides) -> Simulation:
    config = Config(instincts_path=instincts, initial_agents=200, **overrides)
    sim = Simulation(config, seed=seed)
    for _ in range(ticks):
        sim.tick()
        if progress_every and sim.tick_count % progress_every == 0:
            print(sim.stats.progress_line(sim), flush=True)
    return sim


def main():
    parser = argparse.ArgumentParser(description="Evolve a founder population")
    parser.add_argument("--ticks", type=int, default=200_000,
                        help="length of prehistory in ticks (hours); 200,000 is about 23 years")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--instincts", default="instincts.npz")
    parser.add_argument("--out", default="founders.npz")
    args = parser.parse_args()

    sim = run_prehistory(args.ticks, args.seed, args.instincts, progress_every=10_000)
    founders = [a.brain for a in sim.living]
    generations = max(a.generation for a in sim.living)
    save_founders(founders, Path(args.out), generations)
    print(f"Saved {len(founders)} founders (up to generation {generations}) to {args.out}")


if __name__ == "__main__":
    main()
