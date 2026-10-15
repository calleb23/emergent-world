"""Physics: what happens when things meet. General rules over material properties,
never scripted outcomes (see world/items.py for the properties).

- Strike: a held thing at least as hard as what's underfoot can break it into
  what it breaks into (rock on rock chips a sharp flake; a hard thing cracks a nut).
- Rub: rubbing one burnable thing on another builds heat on that spot; enough heat,
  kept up, sets it alight. Heat fades quickly when the rubbing stops.
- Recipes: some pairings make something particular (a flake whittles a stick
  sharp, strips a reed to fibre, butchers a cug; a stick knocks honeycomb from a
  hive). Stinging things sting whoever strikes them. Flint struck on something
  hard throws sparks that can light dry tinder beside it.
- Fire: burns a tile's fuel (burnable items, stick piles, shelters), spreads its
  heat to burnable neighbours, is put out by rain, and leaves ash. Lightning in a
  storm can start one. Food left in a fire for a few hours cooks. Anyone standing
  in it is burned; anyone next to it is kept warm on a cold night.
"""

import numpy as np

FIRE_COLOR = (255, 125, 35)
COOK_HOURS = 3
HEAT_FADE = 0.8           # heat kept each hour
RUB_HEAT = 1.5            # heat added per hour of rubbing
SPREAD_HEAT = 2.0         # heat a fire adds to each burnable neighbour per hour
RAIN_QUENCH = 3           # fuel lost per hour of rain, storm or snow
LIGHTNING_CHANCE = 0.03   # per hour of storm
STICK_FUEL = 6            # hours of fire per stick in a pile
SHELTER_FUEL = 30
BURN_DAMAGE = 8.0         # health lost per hour standing in fire
SPARK_HEAT = 3.0          # heat flint sparks throw onto each burnable neighbour
SPARK_HARDNESS = 6        # flint only sparks against something this hard

NEIGHBOURS = ((1, 0), (-1, 0), (0, 1), (0, -1))


def setup(world):
    world.fire = np.zeros((world.width, world.height), dtype=np.int16)   # hours of fuel left
    world.heat = np.zeros((world.width, world.height), dtype=np.float32)
    world.cooking = np.zeros((world.width, world.height), dtype=np.int16)
    world.growing = np.zeros((world.width, world.height), dtype=np.int16)   # hours a seed has lain


def burnable(world, config, x, y) -> float:
    """Heat needed to set this tile alight, or 0 if there's nothing to burn."""
    kind = config.item(int(world.plants[x, y]))
    if kind is not None and kind.burn_hours:
        return kind.ignites_at
    if world.piles[x, y] or world.shelter[x, y]:
        return 5.0
    return 0.0


def ignite(sim, x, y, cause: str = "") -> bool:
    world, config = sim.world, sim.config
    if world.fire[x, y] or world.terrain[x, y] != 0:
        return False
    kind = config.item(int(world.plants[x, y]))
    fuel = 0
    if kind is not None and kind.burn_hours:
        fuel += kind.burn_hours
        world.plants[x, y] = 0
    fuel += int(world.piles[x, y]) * STICK_FUEL + (SHELTER_FUEL if world.shelter[x, y] else 0)
    if world.shelter[x, y]:
        sim.chronicle("A shelter burned down", once=("shelter burned", x, y))
    world.piles[x, y] = 0
    world.shelter[x, y] = False
    if fuel <= 0:
        return False
    world.fire[x, y] = fuel
    if cause:
        sim.chronicle(cause, once=("fire", cause))
    return True


def wet(sim) -> bool:
    return sim.climate is not None and sim.climate.weather in ("rain", "storm", "snow")


def tick(sim):
    """One hour of fire and heat."""
    world, config, rng = sim.world, sim.config, sim.rng
    world.heat *= HEAT_FADE
    climate = sim.climate
    if climate is not None and climate.weather == "storm" and rng.random() < LIGHTNING_CHANCE:
        x, y = int(rng.integers(0, world.width)), int(rng.integers(0, world.height))
        if burnable(world, config, x, y):
            ignite(sim, x, y, "Lightning struck, and a fire started")
    burning = np.argwhere(world.fire > 0)
    rain = wet(sim)
    for x, y in burning:
        x, y = int(x), int(y)
        world.fire[x, y] -= 1 + (RAIN_QUENCH if rain else 0)
        kind = config.item(int(world.plants[x, y]))
        if kind is not None and kind.cooks_into:
            world.cooking[x, y] += 1
            if world.cooking[x, y] >= COOK_HOURS:
                world.plants[x, y] = config.item_id(kind.cooks_into)
                world.cooking[x, y] = 0
                sim.chronicle(f"Fire turned a {kind.look} into a {kind.cooks_into}", once=("cooked", kind.look))
        if not rain:
            for dx, dy in NEIGHBOURS:
                nx, ny = x + dx, y + dy
                if world.in_bounds(nx, ny) and not world.fire[nx, ny]:
                    needed = burnable(world, config, nx, ny)
                    if needed:
                        world.heat[nx, ny] += SPREAD_HEAT
                        if world.heat[nx, ny] >= needed:
                            ignite(sim, nx, ny)
        if world.fire[x, y] <= 0:
            world.fire[x, y] = 0
            world.cooking[x, y] = 0
            if world.plants[x, y] == 0:
                world.plants[x, y] = config.item_id("ash")


def grow(sim) -> None:
    """Seeds lying on open grass take root, and after a while become what they grow into."""
    world, config = sim.world, sim.config
    seeds = np.zeros(world.plants.shape, dtype=bool)
    for item_id, kind in enumerate(config.items, start=1):
        if kind.grows_into:
            here = world.plants == item_id
            seeds |= here
            ready = here & (world.growing >= kind.grow_days * 24 - 1)
            if ready.any():
                world.plants[ready] = config.item_id(kind.grows_into)
                world.growing[ready] = 0
                seeds &= ~ready
    world.growing[seeds & (world.terrain == 0)] += 1
    world.growing[~seeds] = 0


def shed(sim) -> None:
    """Things that drop things (trees: apples, branches) shed them onto open ground beside them."""
    world, config, rng = sim.world, sim.config, sim.rng
    for item_id, kind in enumerate(config.items, start=1):
        if not kind.drops:
            continue
        spots = np.argwhere(world.plants == item_id)
        for look, chance in kind.drops:
            for x, y in spots[rng.random(len(spots)) < chance]:
                dx, dy = NEIGHBOURS[int(rng.integers(0, 4))]
                nx, ny = int(x) + dx, int(y) + dy
                if world.is_walkable(nx, ny) and world.plants[nx, ny] == 0 and not world.fire[nx, ny]:
                    world.plants[nx, ny] = config.item_id(look)


def fire_near(world, x, y, reach: int = 1) -> bool:
    x0, x1 = max(0, x - reach), min(world.width, x + reach + 1)
    y0, y1 = max(0, y - reach), min(world.height, y + reach + 1)
    return bool(world.fire[x0:x1, y0:y1].any())


def strike(sim, agent) -> None:
    """Hit what's underfoot with what's held."""
    from emergent_world.world.items import STRIKE_RECIPES
    world, config = sim.world, sim.config
    held = config.item(agent.hands)
    target = config.item(int(world.plants[agent.x, agent.y]))
    if held is None or target is None:
        return
    if target.stings:
        agent.take_damage(target.stings, "stings")
        agent.memory.burned(target.color, 0.5)
        sim._first(agent, ("stung", target.look), f"Struck a {target.look} and was stung")
    if held.sparks and target.hardness >= SPARK_HARDNESS:
        sparks(sim, agent.x, agent.y)
        sim._first(agent, ("sparks",), f"Struck a {held.look} on a {target.look}; sparks flew")
    result = STRIKE_RECIPES.get((held.look, target.look)) or target.breaks_into
    if not result or held.hardness < target.hardness or sim.rng.random() > 0.5:
        return
    world.plants[agent.x, agent.y] = config.item_id(result)
    sim._first(agent, ("broke", target.look, result),
               f"Struck a {target.look} with a {held.look}, and got a {result}")
    sim.chronicle(f"{sim_label(agent)} struck a {target.look} with a {held.look} and made the first "
                  f"{result}", once=("made", result))


def sparks(sim, x, y) -> None:
    """Sparks land on the tiles around (x, y): dry tinder can catch."""
    world, config = sim.world, sim.config
    if wet(sim):
        return
    for dx, dy in NEIGHBOURS:
        nx, ny = x + dx, y + dy
        if world.in_bounds(nx, ny) and not world.fire[nx, ny]:
            needed = burnable(world, config, nx, ny)
            if needed:
                world.heat[nx, ny] += SPARK_HEAT
                if world.heat[nx, ny] >= needed and ignite(sim, nx, ny):
                    sim.chronicle("Sparks from struck flint caught, and a fire started", once="spark fire")


def rub(sim, agent) -> None:
    """Rub what's held against what's underfoot: friction builds heat."""
    world, config = sim.world, sim.config
    held = config.item(agent.hands)
    x, y = agent.x, agent.y
    needed = burnable(world, config, x, y)
    if held is None or not held.burn_hours or not needed or world.fire[x, y]:
        return
    world.heat[x, y] += RUB_HEAT
    sim._first(agent, ("rubbed",), f"Rubbed a {held.look} against something; it grew warm")
    if world.heat[x, y] >= needed and not wet(sim):
        if ignite(sim, x, y):
            sim.log(agent, "Rubbed sticks together until fire leapt up")
            sim.chronicle(f"{sim_label(agent)} made fire by rubbing sticks together", once="made fire")


def sim_label(agent) -> str:
    from emergent_world.agents.names import label
    return label(agent)
