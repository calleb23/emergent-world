"""Policies decide what every living agent does this tick, all at once."""

import numpy as np

from emergent_world.agents.agent import Action
from emergent_world.agents.brain import think
from emergent_world.agents.senses import sense_all


class RandomPolicy:
    """Baseline: uniformly random actions."""

    def __init__(self, rng: np.random.Generator):
        self.rng = rng

    def choose_actions(self, agents: list, world, config) -> list:
        return [Action(int(a)) for a in self.rng.integers(0, len(Action), len(agents))]


class BrainPolicy:
    """Each agent's own brain reads its senses and picks an action."""

    def __init__(self, rng: np.random.Generator):
        self.rng = rng

    def choose_actions(self, agents: list, world, config) -> list:
        if not agents:
            return []
        inputs = sense_all(agents, world, config)
        actions = think([a.brain for a in agents], inputs, self.rng,
                        config.action_selection, config.exploration)
        return [Action(int(a)) for a in actions]
