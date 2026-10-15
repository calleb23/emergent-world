"""A hand-written teacher used to give first-generation brains basic instincts.

It decides from exactly the senses agents get, so a brain can learn to copy it.
Its instincts are about what things physically are, not what they look like:

- try to eat any loose solid object it's standing on
- drink any liquid it's touching
- when hungry or thirsty, walk toward the nearest loose object or liquid in sight
- (breathing gases will be automatic once the world has gases)

It has no idea which solids are actually food. Poison gets eaten like anything
else, so learning what's worth eating is left to the agents.
"""

import numpy as np

from emergent_world.agents.agent import Action
from emergent_world.agents.senses import (AGENT_COLOR, GRASS_COLOR, RAY_DIRECTIONS, RAY_SIZE,
                                          TOUCH_LIQUID, UNDERFOOT, _norm, sense_all)

ENERGY_LEVEL, WATER_LEVEL = TOUCH_LIQUID + 1, TOUCH_LIQUID + 2


def _step_toward(dx: int, dy: int) -> Action:
    """Diagonals step sideways first."""
    if dx:
        return Action.EAST if dx > 0 else Action.WEST
    return Action.SOUTH if dy > 0 else Action.NORTH


def teacher_action(x: np.ndarray, rng: np.random.Generator) -> Action:
    """The teacher's choice for one agent's sense vector."""
    # Anything underfoot other than the bare ground is a loose solid object.
    on_object = not np.allclose(x[UNDERFOOT:UNDERFOOT + 3], _norm(GRASS_COLOR))
    if x[TOUCH_LIQUID] and x[WATER_LEVEL] < 0.9:
        return Action.DRINK
    if on_object and x[ENERGY_LEVEL] < 0.9:
        return Action.EAT

    if x[WATER_LEVEL] < x[ENERGY_LEVEL]:
        # Thirstier than hungry: head for the closest liquid in sight.
        closeness = [x[r * RAY_SIZE + 3] for r in range(len(RAY_DIRECTIONS))]
    else:
        # Hungrier: head for the closest loose object in sight (not other creatures).
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

    def choose_actions(self, agents: list, world, config, reach: int | None = None) -> list:
        inputs = sense_all(agents, world, config, reach)
        return [teacher_action(x, self.rng) for x in inputs]
