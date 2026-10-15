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
- Reach: a spear or bow strikes a critter a few tiles off when nothing is underfoot.
  Anything sharp kills a critter, leaving its carcass.
- Force and bonds: heavier tools hit harder. A joined tool's bond takes strain with
  every blow, and can give way, dropping it back into its parts.
- Joining (tension and adhesion): pressing one thing onto another can join them, if
  a binder holds: flexible things tie with their tensile strength, sticky things
  glue with their adhesion. A binder must bear twice the weight it holds. Wet glue
  barely holds.
- Wetness: rain soaks the ground and what's on it; sun dries it. Wet tinder is
  hard to light. Spilled water soaks a tile.
- Wind: storms can blow a shelter apart, unless it's lashed with cord or daubed
  with mud. Daubed shelters don't burn.
- Nature: animals bite people who come too close; mushrooms spring up on soaked
  ground; rain fills open pots; fruiting follows the seasons; ponds hold fish that
  a spear or bow can take.
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
SNAP_STRAIN = 0.02        # chance per blow a bond gives, per point of target hardness over bond
WIND_CHANCE = 0.004       # chance per storm hour that wind tears apart an unreinforced shelter
LASHED, DAUBED = 1, 2     # shelter reinforcement bits
FISH_STOCK = 120          # fish the ponds hold when full
FISH_CHANCE = 0.25        # chance a reaching strike at the water takes a fish (when the ponds are full)

NEIGHBOURS = ((1, 0), (-1, 0), (0, 1), (0, -1))


def setup(world):
    world.fire = np.zeros((world.width, world.height), dtype=np.int16)   # hours of fuel left
    world.heat = np.zeros((world.width, world.height), dtype=np.float32)
    world.cooking = np.zeros((world.width, world.height), dtype=np.int16)
    world.growing = np.zeros((world.width, world.height), dtype=np.int16)   # hours a seed has lain
    world.wet = np.zeros((world.width, world.height), dtype=np.float32)     # 0 dry .. 1 soaked
    world.reinforced = np.zeros((world.width, world.height), dtype=np.int8)
    world.fish = float(FISH_STOCK)


def burnable(world, config, x, y) -> float:
    """Heat needed to set this tile alight, or 0 if there's nothing to burn."""
    kind = config.item(int(world.plants[x, y]))
    soak = 1.0 + 3.0 * float(world.wet[x, y])   # wet things take far more heat
    if kind is not None and kind.burn_hours:
        return kind.ignites_at * soak
    if world.shelter[x, y] and world.reinforced[x, y] & DAUBED:
        return 0.0
    if world.piles[x, y] or world.shelter[x, y]:
        return 5.0 * soak
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
    world.reinforced[x, y] = 0
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
    weather(sim)
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
    growth = sim.climate.growth if sim.climate is not None else 1.0
    for item_id, kind in enumerate(config.items, start=1):
        if not kind.drops:
            continue
        spots = np.argwhere(world.plants == item_id)
        for look, chance in kind.drops:
            if kind.seasonal:
                chance *= growth if growth >= 0.5 else 0.0   # nothing in winter
            for x, y in spots[rng.random(len(spots)) < chance]:
                dx, dy = NEIGHBOURS[int(rng.integers(0, 4))]
                nx, ny = int(x) + dx, int(y) + dy
                if world.is_walkable(nx, ny) and world.plants[nx, ny] == 0 and not world.fire[nx, ny]:
                    world.plants[nx, ny] = config.item_id(look)


def nature(sim) -> None:
    """One hour of the living world: bites, rain-fed mushrooms and pots, fish breeding."""
    world, config, rng = sim.world, sim.config, sim.rng
    world.fish = min(FISH_STOCK, world.fish + 0.02 + 0.002 * world.fish * (1 - world.fish / FISH_STOCK))
    biters = {i: k for i, k in enumerate(config.items, start=1) if k.bites}
    if biters:
        for agent in sim.agents:
            if not agent.alive:
                continue
            x0, y0 = max(0, agent.x - 1), max(0, agent.y - 1)
            near = world.plants[x0:agent.x + 2, y0:agent.y + 2]
            for item_id, kind in biters.items():
                if (near == item_id).any() and rng.random() < kind.bite_chance:
                    bite(sim, agent, kind)
                    break
    raining = wet(sim)
    soaked = (world.wet > 0.6) & (world.terrain == 0) & (world.plants == 0)
    for item_id, kind in enumerate(config.items, start=1):
        if kind.after_rain and soaked.any():
            sprout = soaked & (rng.random(soaked.shape) < kind.after_rain)
            world.plants[sprout] = item_id
            if sprout.any():
                sim.chronicle(f"After the rain, {kind.look}s sprang up", once=("after rain", kind.look))
        if raining and kind.holds_water:
            pots = (world.plants == item_id) & (rng.random(soaked.shape) < 0.1)
            world.plants[pots] = config.item_id(kind.holds_water)
    if raining:
        for agent in sim.agents:
            held = config.item(agent.hands)
            if held is not None and held.holds_water and rng.random() < 0.1:
                agent.hands = config.item_id(held.holds_water)
                sim._first(agent, ("rain filled",), f"Rain filled the {held.look} they were holding")


def bite(sim, agent, kind) -> None:
    agent.take_damage(kind.bites, "bites")
    agent.memory.burned(kind.color, 0.6)
    sim._first(agent, ("bitten", kind.look), f"Bitten by a {kind.look}")
    sim.chronicle(f"{sim_label(agent)} was the first to be bitten by a {kind.look}", once=("bitten", kind.look))


def fire_near(world, x, y, reach: int = 1) -> bool:
    x0, x1 = max(0, x - reach), min(world.width, x + reach + 1)
    y0, y1 = max(0, y - reach), min(world.height, y + reach + 1)
    return bool(world.fire[x0:x1, y0:y1].any())


def strike(sim, agent) -> None:
    """Hit what's underfoot with what's held; a long tool can reach a critter nearby."""
    from emergent_world.world.items import STRIKE_RECIPES, TAP_RECIPES
    world, config = sim.world, sim.config
    held = config.item(agent.hands)
    if held is None:
        return
    x, y = agent.x, agent.y
    target = config.item(int(world.plants[x, y]))
    distance = 0
    if target is None and held.reach:
        found = _critter_within(world, config, x, y, held.reach)
        if found is None:
            _fish(sim, agent, held)
            return
        x, y, distance = found
        target = config.item(int(world.plants[x, y]))
    if target is None:
        return
    if target.stings and not distance:
        agent.take_damage(target.stings, "stings")
        agent.memory.burned(target.color, 0.5)
        sim._first(agent, ("stung", target.look), f"Struck a {target.look} and was stung")
    if held.sparks and target.hardness >= SPARK_HARDNESS:
        sparks(sim, x, y)
        sim._first(agent, ("sparks",), f"Struck a {held.look} on a {target.look}; sparks flew")
    if held.parts and held.bond and _bond_gives(sim, agent, held, target):
        return
    if held.hardness < target.hardness:
        return
    force = min(0.9, 0.3 + 0.2 * held.mass) / (1 + 0.5 * distance)   # heavier hits harder; far is harder
    if sim.rng.random() > force:
        return
    tapped = TAP_RECIPES.get((held.look, target.look))
    if tapped:
        if _place_beside(sim, x, y, tapped):
            sim._first(agent, ("tapped", target.look), f"Cut into a {target.look}; {tapped} oozed out")
            sim.chronicle(f"{sim_label(agent)} cut a {target.look} and got the first {tapped}",
                          once=("made", tapped))
        return
    result = STRIKE_RECIPES.get((held.look, target.look))
    if not result and held.sharp and target.carcass:
        result = target.carcass
    result = result or target.breaks_into
    if not result:
        return
    world.plants[x, y] = config.item_id(result)
    how = f"threw down a {target.look} from {distance} tiles away" if distance else f"struck a {target.look}"
    sim._first(agent, ("broke", target.look, result), f"{how.capitalize()} with a {held.look}, and got a {result}")
    sim.chronicle(f"{sim_label(agent)} {how} with a {held.look} and made the first {result}",
                  once=("made", result))


def _fish(sim, agent, held) -> None:
    """A spear or bow thrust at the water beside you can take a fish."""
    world = sim.world
    if not held.sharp or not world.next_to_liquid(agent.x, agent.y) or world.plants[agent.x, agent.y]:
        return
    if sim.rng.random() >= FISH_CHANCE * world.fish / FISH_STOCK:
        return
    world.fish -= 1
    world.plants[agent.x, agent.y] = sim.config.item_id("fish")
    sim._first(agent, ("fished",), f"Struck at the water with a {held.look} and pulled out a fish")
    sim.chronicle(f"{sim_label(agent)} speared the first fish", once="fished")


def _critter_within(world, config, x, y, reach):
    """The nearest critter within `reach` tiles of (x, y), as (x, y, distance), or None."""
    best = None
    for item_id, kind in enumerate(config.items, start=1):
        if not kind.wanders:
            continue
        x0, y0 = max(0, x - reach), max(0, y - reach)
        for cx, cy in np.argwhere(world.plants[x0:x + reach + 1, y0:y + reach + 1] == item_id):
            cx, cy = int(cx) + x0, int(cy) + y0
            d = max(abs(cx - x), abs(cy - y))
            if best is None or d < best[2]:
                best = (cx, cy, d)
    return best


def _bond_gives(sim, agent, held, target) -> bool:
    """Every blow strains a joined tool's bond; hard targets strain it most."""
    strain = SNAP_STRAIN * max(0.5, target.hardness - held.bond + 1)
    if sim.rng.random() > strain:
        return False
    config = sim.config
    first, *rest = held.parts
    agent.hands = config.item_id(first)
    for look in rest:
        _place_beside(sim, agent.x, agent.y, look, here_too=True)
    sim.log(agent, f"The {held.look}'s binding gave way; it fell apart")
    sim.chronicle(f"A {held.look} came apart in {sim_label(agent)}'s hands", once=("snapped", held.look))
    return True


def _place_beside(sim, x, y, look, here_too=False) -> bool:
    world = sim.world
    spots = ([(x, y)] if here_too else []) + [(x + dx, y + dy) for dx, dy in NEIGHBOURS]
    for nx, ny in spots:
        if world.is_walkable(nx, ny) and world.plants[nx, ny] == 0 and not world.fire[nx, ny]:
            world.plants[nx, ny] = sim.config.item_id(look)
            return True
    return False


def binding_strength(world, a, b, x, y):
    """How strongly a and b would hold together, and the weight that bond must bear.
    Flexible things tie (tensile strength); sticky things glue (adhesion, which
    water ruins). The load is the heaviest part that isn't itself a binder."""
    soaked = float(world.wet[x, y]) > 0.5
    strength, load = 0.0, 0.0
    for kind in (a, b):
        holds = max(kind.tensile if kind.flexible else 0.0, kind.sticky * (0.2 if soaked else 1.0))
        if holds:
            strength = max(strength, holds)
        else:
            load = max(load, kind.mass)
    return strength, load


def join(sim, agent) -> bool:
    """Press what's held onto what's underfoot. Returns True if anything happened."""
    from emergent_world.world.items import JOIN_RECIPES
    world, config = sim.world, sim.config
    held = config.item(agent.hands)
    x, y = agent.x, agent.y
    below = config.item(int(world.plants[x, y]))
    if held is None or below is None:
        return False
    result = JOIN_RECIPES.get(frozenset({held.look, below.look}))
    if not result:
        return False
    strength, load = binding_strength(world, held, below, x, y)
    if strength < 2 * load or strength == 0:
        sim._first(agent, ("slipped", result), f"Tried to bind a {held.look} to a {below.look}; it wouldn't hold")
        return True
    agent.hands = 0
    world.plants[x, y] = config.item_id(result)
    sim._first(agent, ("joined", result), f"Pressed a {held.look} onto a {below.look}, and made a {result}")
    sim.chronicle(f"{sim_label(agent)} joined a {held.look} and a {below.look} into the first {result}",
                  once=("made", result))
    return True


def reinforce(sim, agent) -> bool:
    """Lash a shelter with something that ties, or daub it with something sticky."""
    world, config = sim.world, sim.config
    held = config.item(agent.hands)
    x, y = agent.x, agent.y
    if held is None or not world.shelter[x, y]:
        return False
    if held.flexible and held.tensile >= 4 and not world.reinforced[x, y] & LASHED:
        world.reinforced[x, y] |= LASHED
        how = "lashed"
    elif held.sticky >= 3 and not world.reinforced[x, y] & DAUBED:
        world.reinforced[x, y] |= DAUBED
        how = "daubed"
    else:
        return False
    agent.hands = 0
    sim._first(agent, ("reinforced", how), f"{how.capitalize()} a shelter with a {held.look}")
    sim.chronicle(f"{sim_label(agent)} {how} a shelter with a {held.look}", once=("reinforced", how))
    return True


def weather(sim) -> None:
    """Rain soaks things and sun dries them; storm winds pull at shelters."""
    world, rng, climate = sim.world, sim.rng, sim.climate
    if climate is None:
        world.wet *= 0.97
        return
    if wet(sim):
        world.wet += 0.15 * (1.0 - world.wet)
    else:
        world.wet *= 0.85 if climate.light > 0.5 else 0.97
    if climate.weather == "storm":
        for x, y in np.argwhere(world.shelter & (world.reinforced & LASHED == 0)):
            chance = WIND_CHANCE * (0.5 if world.reinforced[x, y] & DAUBED else 1.0)
            if rng.random() < chance:
                world.shelter[x, y] = False
                world.piles[x, y] //= 2
                world.reinforced[x, y] = 0
                sim.chronicle("A storm wind tore a shelter apart", once="wind")


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
