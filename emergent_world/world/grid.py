"""The physical world: terrain, water and plants on a 2D grid."""

import numpy as np

from emergent_world.config import Config

# Terrain types
GRASS = 0
WATER = 1

# Plant types
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
        self._seed_plants()

    def _make_lakes(self):
        xs, ys = np.meshgrid(np.arange(self.width), np.arange(self.height), indexing="ij")
        lo, hi = self.config.lake_radius
        for _ in range(self.config.water_lakes):
            cx = self.rng.integers(0, self.width)
            cy = self.rng.integers(0, self.height)
            radius = self.rng.integers(lo, hi + 1)
            self.terrain[(xs - cx) ** 2 + (ys - cy) ** 2 <= radius ** 2] = WATER

    def _random_plant_types(self, count: int) -> np.ndarray:
        is_poison = self.rng.random(count) < self.config.poison_share
        return np.where(is_poison, POISON, FOOD).astype(np.int8)

    def _seed_plants(self):
        grass = self.terrain == GRASS
        sprout = grass & (self.rng.random(grass.shape) < self.config.initial_plant_density)
        self.plants[sprout] = self._random_plant_types(int(sprout.sum()))

    def tick(self):
        """Old plants wilt, then new plants sprout on empty grass tiles."""
        wilt = (self.plants != NO_PLANT) & (self.rng.random(self.plants.shape) < self.config.wilt_chance)
        self.plants[wilt] = NO_PLANT
        empty = (self.terrain == GRASS) & (self.plants == NO_PLANT)
        sprout = empty & (self.rng.random(empty.shape) < self.config.regrow_chance)
        self.plants[sprout] = self._random_plant_types(int(sprout.sum()))

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    def is_walkable(self, x: int, y: int) -> bool:
        return self.in_bounds(x, y) and self.terrain[x, y] == GRASS

    def next_to_water(self, x: int, y: int) -> bool:
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if self.in_bounds(nx, ny) and self.terrain[nx, ny] == WATER:
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
        return {
            "food": int((self.plants == FOOD).sum()),
            "poison": int((self.plants == POISON).sum()),
        }
