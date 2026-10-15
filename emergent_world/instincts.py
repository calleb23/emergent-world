"""Give first-generation brains instincts by training them to copy the teacher.

    python -m emergent_world.instincts            # writes instincts.npz

The teacher plays the world while we record what it senses and what it does.
A brain is then trained to predict the teacher's action from the senses
(behavior cloning). Runs started with --instincts begin from mutated copies of
that brain, the way animals are born with instincts, and evolution carries on.
"""

import argparse
from pathlib import Path

import numpy as np

from emergent_world.agents.agent import Action
from emergent_world.agents.brain import HIDDEN_SIZE, OUTPUT_SIZE, Brain
from emergent_world.agents.senses import INPUT_SIZE, sense_all
from emergent_world.agents.teacher import teacher_action
from emergent_world.config import Config
from emergent_world.sim import Simulation


def collect(samples: int, seed: int, noise: float = 0.2) -> tuple:
    """Run the teacher and record (senses, teacher action) pairs.

    With probability `noise` the agent actually does something random, but the
    teacher's choice is still recorded. That shows the brain how to recover from
    situations the teacher itself would never get into.
    """
    config = Config(garden_ticks=0, initial_agents=100, min_population=100)
    sim = Simulation(config, seed=seed)
    rng = np.random.default_rng(seed)
    xs, ys = [], []
    count = 0
    while count < samples:
        living = sim.living
        inputs = sense_all(living, sim.world, config)
        labels = [teacher_action(x, rng) for x in inputs]
        actions = [Action(int(rng.integers(0, len(Action)))) if rng.random() < noise else a
                   for a in labels]
        xs.append(inputs)
        ys.append(np.array(labels))
        count += len(labels)

        # Advance the world one tick using those actions.
        sim.world.tick()
        for agent, action in zip(living, actions):
            sim._act(agent, action)
            sim._update_body(agent)
            if agent.alive:
                sim._maybe_reproduce(agent)
        sim.agents = [a for a in sim.agents if a.alive]
        sim._bootstrap()
        sim.tick_count += 1
    return np.concatenate(xs)[:samples], np.concatenate(ys)[:samples]


def train(xs: np.ndarray, ys: np.ndarray, epochs: int = 30, lr: float = 0.01,
          batch: int = 256, seed: int = 0) -> Brain:
    """Fit one brain to the teacher's choices (cross-entropy, Adam, plain NumPy)."""
    rng = np.random.default_rng(seed)
    brain = Brain.random(rng)
    params = [brain.w1, brain.b1, brain.w2, brain.b2]
    m = [np.zeros_like(p) for p in params]
    v = [np.zeros_like(p) for p in params]
    t = 0
    for epoch in range(epochs):
        order = rng.permutation(len(xs))
        for start in range(0, len(xs), batch):
            idx = order[start:start + batch]
            x, y = xs[idx], ys[idx]
            hidden = np.tanh(x @ brain.w1 + brain.b1)
            logits = hidden @ brain.w2 + brain.b2
            logits -= logits.max(axis=1, keepdims=True)
            probs = np.exp(logits)
            probs /= probs.sum(axis=1, keepdims=True)

            grad_logits = probs
            grad_logits[np.arange(len(y)), y] -= 1
            grad_logits /= len(y)
            grad_w2 = hidden.T @ grad_logits
            grad_b2 = grad_logits.sum(axis=0)
            grad_hidden = (grad_logits @ brain.w2.T) * (1 - hidden ** 2)
            grad_w1 = x.T @ grad_hidden
            grad_b1 = grad_hidden.sum(axis=0)

            t += 1
            for p, g, mi, vi in zip(params, [grad_w1, grad_b1, grad_w2, grad_b2], m, v):
                mi[:] = 0.9 * mi + 0.1 * g
                vi[:] = 0.999 * vi + 0.001 * g * g
                p -= lr * (mi / (1 - 0.9 ** t)) / (np.sqrt(vi / (1 - 0.999 ** t)) + 1e-8)
    return brain


def accuracy(brain: Brain, xs: np.ndarray, ys: np.ndarray) -> float:
    logits = np.tanh(xs @ brain.w1 + brain.b1) @ brain.w2 + brain.b2
    return float((logits.argmax(axis=1) == ys).mean())


def save(brain: Brain, path: Path):
    np.savez(path, w1=brain.w1, b1=brain.b1, w2=brain.w2, b2=brain.b2)


def load(path: Path) -> Brain:
    data = np.load(path)
    brain = Brain(data["w1"], data["b1"], data["w2"], data["b2"])
    if brain.w1.shape != (INPUT_SIZE, HIDDEN_SIZE) or brain.w2.shape != (HIDDEN_SIZE, OUTPUT_SIZE):
        raise ValueError(f"{path} doesn't match the current brain shape; retrain it.")
    return brain


def main():
    parser = argparse.ArgumentParser(description="Train instinct brains by copying the teacher")
    parser.add_argument("--samples", type=int, default=200_000)
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--out", default="instincts.npz")
    args = parser.parse_args()

    print(f"Recording {args.samples} teacher decisions...")
    xs, ys = collect(args.samples, seed=0)
    split = int(len(xs) * 0.9)
    print("Training...")
    brain = train(xs[:split], ys[:split], epochs=args.epochs)
    print(f"Copies the teacher on {accuracy(brain, xs[split:], ys[split:]):.1%} of unseen decisions")
    save(brain, Path(args.out))
    print(f"Saved {args.out}")


if __name__ == "__main__":
    main()
