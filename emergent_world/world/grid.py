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

        self._make_lakes()
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
                    k.spawn_weight if (first_fill or k.regrows) and self._fits(k.habitat, zone) else 0.0
                    for k in c.items])
                self._odds[first_fill, zone] = weights / weights.sum() if weights.sum() else None
        self._wilt = np.array([0.0] + [k.wilt_chance for k in c.items])

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
        self.plants[wilt] = NO_PLANT
        empty = (self.terrain == GRASS) & (self.plants == NO_PLANT)
        self._sprout(empty & (self.rng.random(empty.shape) < self.config.regrow_chance * growth), False)

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
