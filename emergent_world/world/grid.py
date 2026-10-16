"""The physical world: terrain, water and items on a 2D grid.

`plants` holds the loose item on each tile (a plant, berry, mushroom, nut,
rock or stick), as an id into the config's item table; 0 means nothing.
"""

import numpy as np

from emergent_world.config import Config

# Terrain types, and the physical state of each. Instincts act on the state,
# not the specific material: agents try to drink any liquid. When the god adds
# new liquids (juice, swamp water) they join LIQUIDS and agents will try them.
GRASS = 0
WATER = 1
LIQUIDS = (WATER,)

# Item ids. 0 is an empty tile; the first two items in the table are the
# original green plant (food) and yellow-green plant (poison).
NO_PLANT = 0
FOOD = 1
POISON = 2


class World:
    def __init__(self, config: Config, rng: np.random.Generator):
        self.config = config
        self.rng = rng
        self.width = config.width
        self.height = config.height

        # Indexed [x, y] throughout.
        self.terrain = np.full((self.width, self.height), GRASS, dtype=np.int8)
        self.plants = np.full((self.width, self.height), NO_PLANT, dtype=np.int8)

        # Shelters people build: stick piles growing into finished shelters.
        self.piles = np.zeros((self.width, self.height), dtype=np.int16)
        self.shelter = np.zeros((self.width, self.height), dtype=bool)
        from emergent_world.world import physics
        physics.setup(self)   # fire, heat and cooking layers

        self._make_lakes()
        self._make_shores()
        self._make_habitats()
        self._seed_plants()

    def _make_lakes(self):
        xs, ys = np.meshgrid(np.arange(self.width), np.arange(self.height), indexing="ij")
        lo, hi = self.config.lake_radius
        for _ in range(self.config.water_lakes):
            cx = self.rng.integers(0, self.width)
            cy = self.rng.integers(0, self.height)
            radius = self.rng.integers(lo, hi + 1)
            self.terrain[(xs - cx) ** 2 + (ys - cy) ** 2 <= radius ** 2] = WATER

    def _make_shores(self):
        """For every tile, the nearest grass tile beside water and how far it is
        (steps over grass), so people can remember water they've only seen."""
        from collections import deque
        self.shore_distance = np.full((self.width, self.height), 10**6, dtype=np.int32)
        self.nearest_shore = np.full((self.width, self.height, 2), -1, dtype=np.int32)
        queue = deque()
        for x in range(self.width):
            for y in range(self.height):
                if self.terrain[x, y] == GRASS and self.next_to_liquid(x, y):
                    self.shore_distance[x, y] = 0
                    self.nearest_shore[x, y] = (x, y)
                    queue.append((x, y))
        while queue:
            x, y = queue.popleft()
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if self.is_walkable(nx, ny) and self.shore_distance[nx, ny] > self.shore_distance[x, y] + 1:
                    self.shore_distance[nx, ny] = self.shore_distance[x, y] + 1
                    self.nearest_shore[nx, ny] = self.nearest_shore[x, y]
                    queue.append((nx, ny))

    def _make_habitats(self):
        """Sort land into damp (near water), dry (far from water) and in between."""
        water = np.argwhere(self.terrain == WATER)
        xs, ys = np.meshgrid(np.arange(self.width), np.arange(self.height), indexing="ij")
        distance = np.full((self.width, self.height), 10**6)
        for wx, wy in water:
            distance = np.minimum(distance, np.maximum(abs(xs - wx), abs(ys - wy)))
        c = self.config
        self.habitat = np.where(distance <= c.near_water, 1, np.where(distance >= c.dry_distance, 2, 0))
        # Spawn odds for each habitat (0 between, 1 damp, 2 dry), for regrowing
        # items and for the first fill (which also places rocks).
        self._odds = {}
        for first_fill in (False, True):
            for zone in (0, 1, 2):
                weights = np.array([
                    k.spawn_weight if k.spawns and (first_fill or k.regrows) and self._fits(k.habitat, zone) else 0.0
                    for k in c.items])
                self._odds[first_fill, zone] = weights / weights.sum() if weights.sum() else None
        self._wilt = np.array([0.0] + [k.wilt_chance for k in c.items])
        # What each item leaves when it wilts (a fallen tree leaves a log), and what
        # traps a critter stepping onto it becomes.
        self._rot = np.array([0] + [c.item_id(k.rots_into) for k in c.items], dtype=np.int8)
        self._trap = np.array([0] + [c.item_id(k.traps) for k in c.items], dtype=np.int8)
        self._cover = np.array([False] + [k.cover for k in c.items])   # item id -> gives cover
        self._prey = {i: {c.item_id(look) for look in k.eats} for i, k in enumerate(c.items, start=1) if k.eats}

    @staticmethod
    def _fits(habitat: str, zone: int) -> bool:
        return habitat == "anywhere" or (habitat == "near_water" and zone == 1) or (habitat == "dry" and zone == 2)

    def _sprout(self, tiles: np.ndarray, first_fill: bool):
        """Place a new item on each tile in the mask, chosen by its habitat."""
        for zone in (0, 1, 2):
            here = tiles & (self.habitat == zone)
            count = int(here.sum())
            odds = self._odds[first_fill, zone]
            if count and odds is not None:
                self.plants[here] = self.rng.choice(len(odds), size=count, p=odds) + 1

    def _seed_plants(self):
        grass = self.terrain == GRASS
        self._sprout(grass & (self.rng.random(grass.shape) < self.config.initial_item_density), True)

    def tick(self, growth: float = 1.0):
        """Items wilt or wash away at their own rates; new ones appear on empty
        grass. `growth` scales how fast things regrow (seasons and weather)."""
        wilt = self.rng.random(self.plants.shape) < self._wilt[self.plants]
        self.plants[wilt] = self._rot[self.plants[wilt]]
        empty = (self.terrain == GRASS) & (self.plants == NO_PLANT)
        self._sprout(empty & (self.rng.random(empty.shape) < self.config.regrow_chance * growth), False)

    def move_critters(self, occupied: np.ndarray, growth: float = 1.0):
        """Critters wander, scuttle away from anyone next to them, and breed.
        `occupied` marks tiles with a person on them; `growth` (season and
        weather) scales breeding, so critters boom in spring and stall in winter."""
        steps = ((1, 0), (-1, 0), (0, 1), (0, -1))
        for item_id, kind in enumerate(self.config.items, start=1):
            if not (kind.wanders or kind.flees or kind.breeds):
                continue
            spots = np.argwhere(self.plants == item_id)
            count = len(spots)
            for x, y in spots:
                x, y = int(x), int(y)
                near = any(self.in_bounds(x + dx, y + dy) and occupied[x + dx, y + dy] for dx, dy in steps)
                bolting = near and self.rng.random() < kind.flees
                if bolting or self.rng.random() < kind.wanders:
                    options = [(x + dx, y + dy) for dx, dy in steps
                               if self.is_walkable(x + dx, y + dy) and not occupied[x + dx, y + dy]
                               and (self.plants[x + dx, y + dy] == NO_PLANT or self._trap[self.plants[x + dx, y + dy]])]
                    if bolting:   # run, preferring tiles with nobody next to them
                        calm = [(a, b) for a, b in options
                                if not any(self.in_bounds(a + dx, b + dy) and occupied[a + dx, b + dy] for dx, dy in steps)]
                        options = calm or options
                    if options:
                        nx, ny = options[int(self.rng.integers(0, len(options)))]
                        self.plants[x, y] = NO_PLANT
                        caught = self._trap[self.plants[nx, ny]]
                        if caught:   # stepped into a snare: caught fast
                            self.plants[nx, ny] = caught
                            count -= 1
                            continue
                        self.plants[nx, ny] = item_id
                        x, y = nx, ny
                prey = self._prey.get(item_id)
                if prey and self.rng.random() < kind.hunger:   # graze or hunt whatever's beside it
                    for dx, dy in steps:
                        if self.in_bounds(x + dx, y + dy) and int(self.plants[x + dx, y + dy]) in prey:
                            self.plants[x + dx, y + dy] = NO_PLANT
                            break
                if count < kind.max_count and self.rng.random() < kind.breeds * growth:
                    nests = [(x + dx, y + dy) for dx, dy in steps
                             if self.is_walkable(x + dx, y + dy) and self.plants[x + dx, y + dy] == NO_PLANT]
                    if nests:
                        nx, ny = nests[int(self.rng.integers(0, len(nests)))]
                        self.plants[nx, ny] = item_id
                        count += 1

    def add_to_shelter(self, x: int, y: int, needed: int) -> bool:
        """Put a stick on the pile at (x, y). Returns True when that finishes a shelter."""
        if self.shelter[x, y]:
            return False
        self.piles[x, y] += 1
        if self.piles[x, y] >= needed:
            self.shelter[x, y] = True
            return True
        return False

    def shelter_near(self, x: int, y: int, reach: int):
        """A shelter or natural cover within `reach` tiles, or None."""
        x0, x1 = max(0, x - reach), min(self.width, x + reach + 1)
        y0, y1 = max(0, y - reach), min(self.height, y + reach + 1)
        window = self.shelter[x0:x1, y0:y1] | self._cover[self.plants[x0:x1, y0:y1]]
        if not window.any():
            return None
        found = np.argwhere(window)
        sx, sy = found[0]
        return int(sx + x0), int(sy + y0)

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    def is_walkable(self, x: int, y: int) -> bool:
        return self.in_bounds(x, y) and self.terrain[x, y] == GRASS

    def next_to_liquid(self, x: int, y: int) -> bool:
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if self.in_bounds(nx, ny) and self.terrain[nx, ny] in LIQUIDS:
                return True
        return False

    def take_plant(self, x: int, y: int) -> int:
        """Remove and return the plant at (x, y), or NO_PLANT."""
        plant = int(self.plants[x, y])
        self.plants[x, y] = NO_PLANT
        return plant

    def random_walkable_tile(self) -> tuple:
        while True:
            x = int(self.rng.integers(0, self.width))
            y = int(self.rng.integers(0, self.height))
            if self.is_walkable(x, y):
                return x, y

    def plant_counts(self) -> dict:
        """How many harmless edible items ("food") and harmful ones ("poison") are out."""
        counts = np.bincount(self.plants.ravel(), minlength=len(self.config.items) + 1)
        food = sum(int(counts[i + 1]) for i, k in enumerate(self.config.items) if k.edible and not k.harmful)
        poison = sum(int(counts[i + 1]) for i, k in enumerate(self.config.items) if k.harmful)
        return {"food": food, "poison": poison}
