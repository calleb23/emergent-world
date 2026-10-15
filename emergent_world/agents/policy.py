"""Policies decide what an agent does each tick.

Step 2 uses a random policy. Step 3 replaces it with a neural-network brain
that reads the agent's senses; the simulation only needs `choose_action`.
"""

import numpy as np

from emergent_world.agents.agent import Action, Agent


class RandomPolicy:
    def __init__(self, rng: np.random.Generator):
        self.rng = rng

    def choose_action(self, agent: Agent, world) -> Action:
        return Action(int(self.rng.integers(0, len(Action))))
