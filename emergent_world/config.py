"""All tunable numbers in one place, so experiments change config, not code.

The clock: 1 tick = 1 hour. Body needs are set on that clock (thirst kills in
about 10 days, hunger in about 2-3 weeks, poison acts within a day). Lifespans
vary by phase: short in prehistory so generations fly by, long in the real world.
"""

from dataclasses import dataclass, field

from emergent_world.world.items import DEFAULT_ITEMS, ItemKind

TICKS_PER_DAY = 24
TICKS_PER_YEAR = TICKS_PER_DAY * 365


def days(n: float) -> int:
    return int(round(n * TICKS_PER_DAY))


def years(n: float) -> int:
    return int(round(n * TICKS_PER_YEAR))


def format_time(ticks: int) -> str:
    """'year 2, day 140' style, for progress lines and the viewer."""
    year, rest = divmod(ticks, TICKS_PER_YEAR)
    return f"year {year + 1}, day {rest // TICKS_PER_DAY + 1}"


@dataclass
class Config:
    # World
    width: int = 64
    height: int = 64
    water_lakes: int = 12           # number of ponds scattered on the map
    lake_radius: tuple = (2, 4)     # min/max pond radius in tiles
    initial_item_density: float = 0.15    # share of grass tiles that start with an item
    regrow_chance: float = 0.0009         # per empty grass tile, per tick; sets how many agents food supports
    near_water: int = 3                   # tiles from water that count as damp ("near_water" items)
    dry_distance: int = 8                 # tiles from water beyond which it's dry ("dry" items)
    items: tuple = field(default_factory=lambda: DEFAULT_ITEMS)  # every kind of item: see world/items.py


    # Agents
    initial_agents: int = 50
    max_energy: float = 100.0
    max_water: float = 100.0
    max_health: float = 100.0
    energy_drain: float = 0.25      # per tick
    water_drain: float = 0.4        # per tick
    starvation_damage: float = 2.0  # health lost per tick at zero energy
    dehydration_damage: float = 3.0 # health lost per tick at zero water
    healing: float = 0.2            # health regained per tick when fed and watered
    lifespan: tuple = (days(33), days(50))  # min/max ticks before old age (prehistory scale)

    # Food and drink
    drink_amount: float = 40.0

    # Day and night, seasons, weather and sleep (see world/climate.py)
    climate: bool = True            # False: endless clear daylight, no sleep (old behavior)
    fatigue_rate: float = 0.05      # tiredness gained per waking hour (exhausted after 20 hours)
    rest_rate: float = 0.12         # tiredness lost per hour asleep (about 8 hours of sleep)
    sleep_threshold: float = 0.6    # tired enough to fall asleep once it's dark
    wake_threshold: float = 0.4     # rested enough to get up once it's light
    sleep_drain: float = 0.6        # hunger and thirst slow to this share while asleep
    sleep_healing: float = 2.0      # healing runs this many times faster while asleep
    exhaustion_damage: float = 0.5  # health lost per hour while awake and exhausted

    # Senses and brain
    policy: str = "brain"           # "brain" or "random" (a baseline to compare against)
    vision_range: int = 8           # tiles each vision ray reaches
    action_selection: str = "argmax"  # "argmax": take the brain's top action; "sample": draw by probability
    exploration: float = 0.1        # argmax only: chance of a random action instead

    # Reproduction and evolution (asexual for now; two parents comes later)
    maturity_fraction: float = 0.15 # share of average lifespan before an agent can reproduce
    reproduce_energy: float = 70.0  # energy needed to reproduce
    reproduce_water: float = 50.0   # water needed too: parched agents don't breed
    reproduce_cost_energy: float = 40.0
    reproduce_cost_water: float = 20.0
    cooldown_fraction: float = 0.10 # share of average lifespan between children
    child_energy: float = 60.0
    child_water: float = 60.0
    mutation_scale: float = 0.05    # size of random changes to inherited weights
    mutation_rate: float = 0.05     # share of weights changed per child; too high and good
                                    # brains slowly drift apart ("mutational meltdown")
    max_population: int = 1000      # safety cap; food should normally limit population first

    # Food memory (learning within a lifetime). See agents/memory.py.
    aversion_window: int = 48       # ticks: meals this recent get blamed for sickness
    sickness_aversion: float = 0.8  # aversion added to foods blamed for getting sick
    witness_aversion: float = 0.6   # added to foods a relative ate before dying of poison
    inedible_aversion: float = 0.3  # added each time an agent bites something it can't eat
    learned_safety: float = 0.3     # share of aversion removed when a food proves safe
    aversion_fade: float = 0.995    # daily multiplier; aversion halves in about 140 days
    aversion_gain: float = 10.0     # starting value of the gene that turns aversion into not eating
    steer_strength: float = 0.5     # share of that pull used to steer away from foods in sight
    desperation_below: float = 0.5  # below this share of energy, hunger starts overriding wariness
    aversion_gain_mutation: float = 0.5  # how much that gene varies between parent and child

    # Instincts: a brain file from `python -m emergent_world.instincts`. When set,
    # new agents start as mutated copies of it instead of random brains.
    instincts_path: str = ""

    # Founders: a population file from `python -m emergent_world.prehistory`.
    # When set, the world starts with these brains (and tops up from them).
    founders_path: str = ""
    founder_count: int = 0          # how many founders enter the world (0 = all of them)

    # Bootstrapping: early random brains die fast, so top the population up
    # until reproduction can sustain it. Most new agents are mutated copies
    # of the longest-lived brains so far; the rest are fresh random brains.
    min_population: int = 20
    hall_of_fame_size: int = 20     # top-up parents: the best of the recent deaths
    hall_of_fame_window: int = 200  # how many recent deaths count; old champions age out
    child_fitness: float = 100.0    # fitness = age at death + this per child
    reseed_from_best: float = 0.5   # share of top-up agents copied from the hall of fame

    # Garden-first curriculum: hunger and thirst drain slowly at the start and
    # ramp up to full strength, so blank brains survive long enough to breed.
    garden_start: float = 0.4       # drain multiplier at tick 0
    garden_ticks: int = 30000       # ticks to reach full difficulty (0 = no garden)

    def item(self, item_id: int) -> ItemKind | None:
        """The kind of item with this map id (0 = nothing)."""
        return self.items[item_id - 1] if 0 < item_id <= len(self.items) else None

    def look_of(self, color) -> str:
        for kind in self.items:
            if kind.color == color:
                return kind.look
        return "something"

    # The two original plants, by name, for code and tests that use them directly.
    @property
    def food_color(self) -> tuple:
        return self.items[0].color

    @property
    def poison_color(self) -> tuple:
        return self.items[1].color

    @property
    def average_lifespan(self) -> float:
        return (self.lifespan[0] + self.lifespan[1]) / 2

    @property
    def maturity_age(self) -> int:
        return int(self.average_lifespan * self.maturity_fraction)

    @property
    def reproduce_cooldown(self) -> int:
        return int(self.average_lifespan * self.cooldown_fraction)

    def with_lifespan_years(self, average_years: float, spread: float = 0.2) -> "Config":
        """Set lifespans to average_years, give or take `spread` (0.2 = 20%)."""
        self.lifespan = (years(average_years * (1 - spread)), years(average_years * (1 + spread)))
        return self

    @classmethod
    def small_world(cls, people: int = 12, max_people: int = 40, children: float = 3.0,
                    years: float = 2.0) -> "Config":
        """The default world for following individual lives: a few founders, long
        lives, about `children` children per lifetime, and top-ups only to
        prevent extinction."""
        config = cls(garden_ticks=0, founder_count=people, initial_agents=people,
                     max_population=max_people, min_population=2).with_lifespan_years(years)
        # Children are spaced so a full life fits about `children` of them after adulthood.
        config.cooldown_fraction = (1 - config.maturity_fraction) / max(children, 0.1)
        return config
