"""A hand-written teacher used to give first-generation brains basic instincts.

It decides from exactly the senses agents get, so a brain can learn to copy it.
It knows how to drink, eat and walk toward what it needs, and nothing else.
In particular it can't tell poison from food: it eats anything green, so
avoiding poison is still left for the agents to discover.
"""

import numpy as np

from emergent_world.agents.agent import Action
from emergent_world.agents.senses import (AGENT_COLOR, GRASS_COLOR, RAY_DIRECTIONS, RAY_SIZE,
                                          TOUCH_WATER, UNDERFOOT, _norm, sense_all)

ENERGY, WATER = TOUCH_WATER + 1, TOUCH_WATER + 2


def _step_toward(dx: int, dy: int) -> Action:
    """Diagonals step sideways first."""
    if dx:
        return Action.EAST if dx > 0 else Action.WEST
    return Action.SOUTH if dy > 0 else Action.NORTH


def teacher_action(x: np.ndarray, rng: np.random.Generator) -> Action:
    """The teacher's choice for one agent's sense vector."""
    on_plant = not np.allclose(x[UNDERFOOT:UNDERFOOT + 3], _norm(GRASS_COLOR))
    if x[TOUCH_WATER] and x[WATER] < 0.9:
        return Action.DRINK
    if on_plant and x[ENERGY] < 0.9:
        return Action.EAT

    if x[WATER] < x[ENERGY]:
        # Thirstier than hungry: head for the closest water in sight.
        closeness = [x[r * RAY_SIZE + 3] for r in range(len(RAY_DIRECTIONS))]
    else:
        # Hungrier: head for the closest plant in sight (any green, not other agents).
        agent_color = np.array(_norm(AGENT_COLOR))
        closeness = []
        for r in range(len(RAY_DIRECTIONS)):
            color = x[r * RAY_SIZE + 4:r * RAY_SIZE + 7]
            is_agent = np.allclose(color, agent_color)
            closeness.append(0.0 if is_agent else x[r * RAY_SIZE + 7])
    best = int(np.argmax(closeness))
    if closeness[best] > 0:
        return _step_toward(*RAY_DIRECTIONS[best])
    return Action(int(rng.integers(0, 4)))  # nothing useful in sight: wander


class TeacherPolicy:
    def __init__(self, rng: np.random.Generator):
        self.rng = rng

    def choose_actions(self, agents: list, world, config) -> list:
        inputs = sense_all(agents, world, config)
        return [teacher_action(x, self.rng) for x in inputs]
