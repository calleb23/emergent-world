"""Policies decide what every living agent does this tick, all at once."""

import numpy as np

from emergent_world.agents.agent import Action
from emergent_world.agents.brain import OUTPUT_SIZE, think
from emergent_world.agents.senses import RAY_DIRECTIONS, RAY_SIZE, sense_all


class RandomPolicy:
    """Baseline: uniformly random actions."""

    def __init__(self, rng: np.random.Generator):
        self.rng = rng

    def choose_actions(self, agents: list, world, config, reach: int | None = None) -> list:
        return [Action(int(a)) for a in self.rng.integers(0, len(Action), len(agents))]


class BrainPolicy:
    """Each agent's own brain reads its senses and picks an action."""

    def __init__(self, rng: np.random.Generator):
        self.rng = rng

    def choose_actions(self, agents: list, world, config, reach: int | None = None) -> list:
        if not agents:
            return []
        inputs = sense_all(agents, world, config, reach)
        penalties = np.zeros((len(agents), OUTPUT_SIZE), dtype=np.float32)
        penalties[:, Action.EAT] = self.eat_penalty(agents, world, config)
        penalties[:, :4] = self.steer_penalty(agents, inputs, config)
        penalties *= self.desperation(agents, config)[:, None]
        actions = think([a.brain for a in agents], inputs, self.rng,
                        config.action_selection, config.exploration, penalties)
        return [Action(int(a)) for a in actions]

    @staticmethod
    def desperation(agents: list, config) -> np.ndarray:
        """Hunger overrides disgust: below half energy, wariness fades, down to a
        tenth of its strength when starving. Without this, an agent that wrongly
        blames its main food can starve rather than ever learn it was safe."""
        energy = np.array([a.energy / config.max_energy for a in agents], dtype=np.float32)
        return np.clip(energy / config.desperation_below, 0.1, 1.0)

    @staticmethod
    def steer_penalty(agents: list, inputs: np.ndarray, config) -> np.ndarray:
        """How much memories hold each agent back from walking toward foods it's
        wary of, judged from what it actually sees along each vision ray.

        Returns (agents, 4) for NORTH, SOUTH, EAST, WEST. Closer foods weigh more;
        a diagonal ray counts half toward each of its two directions.
        """
        move_of = {(0, -1): Action.NORTH, (0, 1): Action.SOUTH,
                   (1, 0): Action.EAST, (-1, 0): Action.WEST}
        penalty = np.zeros((len(agents), 4), dtype=np.float32)
        for i, agent in enumerate(agents):
            if not agent.memory.aversion:
                continue
            for r, (dx, dy) in enumerate(RAY_DIRECTIONS):
                closeness = inputs[i, r * RAY_SIZE + 7]
                if closeness <= 0:
                    continue
                seen = tuple(int(round(v * 255)) for v in inputs[i, r * RAY_SIZE + 4:r * RAY_SIZE + 7])
                wary = agent.memory.level(seen)
                if not wary:
                    continue
                push = config.steer_strength * agent.aversion_gain * wary * closeness
                moves = [move_of[(dx, 0)], move_of[(0, dy)]] if dx and dy else [move_of[(dx, dy)]]
                for move in moves:
                    penalty[i, move] += push / len(moves)
        return penalty

    @staticmethod
    def eat_penalty(agents: list, world, config) -> np.ndarray:
        """How much each agent's memories hold it back from eating what's underfoot."""
        penalty = np.zeros(len(agents), dtype=np.float32)
        for i, agent in enumerate(agents):
            kind = config.item(int(world.plants[agent.x, agent.y]))
            if kind is not None:
                penalty[i] = agent.aversion_gain * agent.memory.level(kind.color)
        return penalty
