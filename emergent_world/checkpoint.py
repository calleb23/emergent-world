"""Save a whole world at any moment, and carry on from it later.

    from emergent_world import checkpoint
    checkpoint.save(sim, "runs/world.ckpt")
    sim = checkpoint.load("runs/world.ckpt")

A resumed world continues exactly as it would have without stopping (same
random stream, same people, same history). Checkpoints are gzipped pickles:
only load files you made yourself, as unpickling can run code.
"""

import gzip
import pickle
from pathlib import Path

FORMAT = 1


def save(sim, path, note: str = "") -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    from emergent_world.experiment import git_state
    header = {"format": FORMAT, "tick": sim.tick_count, "seed": sim.seed, "note": note, **git_state()}
    with gzip.open(path, "wb", compresslevel=6) as f:
        pickle.dump(header, f, protocol=5)
        pickle.dump(sim, f, protocol=5)
    return path


def header(path) -> dict:
    with gzip.open(path, "rb") as f:
        return pickle.load(f)


def load(path):
    with gzip.open(path, "rb") as f:
        head = pickle.load(f)
        if head.get("format") != FORMAT:
            raise ValueError(f"{path} is checkpoint format {head.get('format')}, expected {FORMAT}")
        return pickle.load(f)
