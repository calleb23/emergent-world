"""Policies decide what every living agent does this tick, all at once."""

import numpy as np

from emergent_world.agents.agent import Action
from emergent_world.agents.brain import think
from emergent_world.agents.senses import sense_all
from emergent_world.world.grid import FOOD, POISON


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
                        config.action_selection, config.exploration,
                        eat_penalty=self.eat_penalty(agents, world, config))
        return [Action(int(a)) for a in actions]

    @staticmethod
    def eat_penalty(agents: list, world, config) -> np.ndarray:
        """How much each agent's memories hold it back from eating what's underfoot."""
        colors = {FOOD: config.food_color, POISON: config.poison_color}
        penalty = np.zeros(len(agents), dtype=np.float32)
        for i, agent in enumerate(agents):
            color = colors.get(int(world.plants[agent.x, agent.y]))
            if color is not None:
                penalty[i] = agent.aversion_gain * agent.memory.level(color)
        return penalty
