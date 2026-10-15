"""What an agent perceives. Only surfaces: colors, distances, its own body.

No labels and no object IDs: a poison plant is just a slightly different green.
"""

import numpy as np

from emergent_world.world.grid import FOOD, LIQUIDS, POISON, WATER

# Eight compass directions, one vision ray each.
RAY_DIRECTIONS = ((0, -1), (1, -1), (1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1))

WATER_COLOR = (40, 90, 160)
AGENT_COLOR = (230, 230, 230)
GRASS_COLOR = (34, 52, 30)

# Each ray has two layers, because short plants shouldn't hide a lake:
#   ground layer: the first water it reaches (red, green, blue, closeness)
#   object layer: the first plant or agent it reaches (red, green, blue, closeness)
# Then underfoot RGB, touching liquid, energy, water, health, pain.
RAY_SIZE = 8
INPUT_SIZE = len(RAY_DIRECTIONS) * RAY_SIZE + 3 + 1 + 4
UNDERFOOT = len(RAY_DIRECTIONS) * RAY_SIZE
TOUCH_LIQUID = UNDERFOOT + 3


def _norm(color) -> tuple:
    return tuple(channel / 255.0 for channel in color)


def build_occupancy(world, agents) -> np.ndarray:
    """A grid marking which tiles hold a living agent, for vision."""
    occupied = np.zeros((world.width, world.height), dtype=bool)
    for agent in agents:
        occupied[agent.x, agent.y] = True
    return occupied


def sense_all(agents: list, world, config) -> np.ndarray:
    """Senses for every agent at once, shape (agents, INPUT_SIZE).

    The same result as calling `sense` per agent, but each ray step is one NumPy
    operation across all agents instead of a Python loop per agent.
    """
    n = len(agents)
    inputs = np.zeros((n, INPUT_SIZE), dtype=np.float32)
    if n == 0:
        return inputs
    xs = np.array([a.x for a in agents])
    ys = np.array([a.y for a in agents])
    occupied = build_occupancy(world, agents)
    food, poison = np.array(_norm(config.food_color)), np.array(_norm(config.poison_color))
    water, others = np.array(_norm(WATER_COLOR)), np.array(_norm(AGENT_COLOR))

    for r, (dx, dy) in enumerate(RAY_DIRECTIONS):
        i = r * RAY_SIZE
        ground_found = np.zeros(n, dtype=bool)
        object_found = np.zeros(n, dtype=bool)
        for step in range(1, config.vision_range + 1):
            px, py = xs + dx * step, ys + dy * step
            inside = (px >= 0) & (px < world.width) & (py >= 0) & (py < world.height)
            cx, cy = np.clip(px, 0, world.width - 1), np.clip(py, 0, world.height - 1)
            closeness = 1.0 - (step - 1) / config.vision_range

            new_ground = inside & ~ground_found & (world.terrain[cx, cy] == WATER)
            inputs[new_ground, i:i + 3] = water
            inputs[new_ground, i + 3] = closeness
            ground_found |= new_ground

            agent_there = occupied[cx, cy]
            plant = world.plants[cx, cy]
            new_object = inside & ~object_found & (agent_there | (plant == FOOD) | (plant == POISON))
            color = np.where(agent_there[:, None], others,
                             np.where((plant == FOOD)[:, None], food, poison))
            inputs[new_object, i + 4:i + 7] = color[new_object]
            inputs[new_object, i + 7] = closeness
            object_found |= new_object

    i = UNDERFOOT
    underfoot = world.plants[xs, ys]
    inputs[:, i:i + 3] = np.where((underfoot == FOOD)[:, None], food,
                                  np.where((underfoot == POISON)[:, None], poison,
                                           np.array(_norm(GRASS_COLOR))))
    touching = np.zeros(n, dtype=bool)
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        px, py = xs + dx, ys + dy
        inside = (px >= 0) & (px < world.width) & (py >= 0) & (py < world.height)
        cx, cy = np.clip(px, 0, world.width - 1), np.clip(py, 0, world.height - 1)
        touching |= inside & np.isin(world.terrain[cx, cy], LIQUIDS)
    inputs[:, TOUCH_LIQUID] = touching
    inputs[:, TOUCH_LIQUID + 1] = [a.energy / config.max_energy for a in agents]
    inputs[:, TOUCH_LIQUID + 2] = [a.water / config.max_water for a in agents]
    inputs[:, TOUCH_LIQUID + 3] = [a.health / config.max_health for a in agents]
    inputs[:, TOUCH_LIQUID + 4] = [1.0 if any(s.delay == 0 for s in a.sicknesses) else 0.0
                                  for a in agents]
    return inputs


def sense(agent, world, occupied: np.ndarray, config) -> np.ndarray:
    """Senses for one agent. The readable reference version of `sense_all`."""
    inputs = np.zeros(INPUT_SIZE, dtype=np.float32)
    plant_colors = {FOOD: _norm(config.food_color), POISON: _norm(config.poison_color)}
    water, others = _norm(WATER_COLOR), _norm(AGENT_COLOR)

    i = 0
    for dx, dy in RAY_DIRECTIONS:
        ground_found = object_found = False
        for step in range(1, config.vision_range + 1):
            x, y = agent.x + dx * step, agent.y + dy * step
            if not world.in_bounds(x, y) or (ground_found and object_found):
                break
            closeness = 1.0 - (step - 1) / config.vision_range
            if not ground_found and world.terrain[x, y] == WATER:
                inputs[i:i + 3] = water
                inputs[i + 3] = closeness
                ground_found = True
            if not object_found:
                seen = None
                if occupied[x, y]:
                    seen = others
                elif world.plants[x, y] in plant_colors:
                    seen = plant_colors[int(world.plants[x, y])]
                if seen is not None:
                    inputs[i + 4:i + 7] = seen
                    inputs[i + 7] = closeness
                    object_found = True
        i += RAY_SIZE

    underfoot = world.plants[agent.x, agent.y]
    inputs[i:i + 3] = plant_colors.get(int(underfoot), _norm(GRASS_COLOR))
    i += 3
    inputs[i] = 1.0 if world.next_to_liquid(agent.x, agent.y) else 0.0
    i += 1
    inputs[i] = agent.energy / config.max_energy
    inputs[i + 1] = agent.water / config.max_water
    inputs[i + 2] = agent.health / config.max_health
    inputs[i + 3] = 1.0 if any(s.delay == 0 for s in agent.sicknesses) else 0.0
    return inputs
