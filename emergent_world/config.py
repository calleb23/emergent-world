"""All tunable numbers in one place, so experiments change config, not code."""

from dataclasses import dataclass


@dataclass
class Config:
    # World
    width: int = 64
    height: int = 64
    water_lakes: int = 12           # number of ponds scattered on the map
    lake_radius: tuple = (2, 4)     # min/max pond radius in tiles
    initial_plant_density: float = 0.15   # share of grass tiles that start with a plant
    regrow_chance: float = 0.002          # per empty grass tile, per tick
    wilt_chance: float = 0.002            # per plant, per tick; uneaten plants don't last forever
    poison_share: float = 0.10            # share of new plants that are poisonous

    # Plant appearance (RGB). Agents will eventually see colors, never labels,
    # so the poison plant only *looks* slightly different.
    food_color: tuple = (60, 170, 70)
    poison_color: tuple = (90, 170, 60)

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
    lifespan: tuple = (800, 1200)   # min/max ticks before death of old age

    # Food and drink
    food_energy: float = 30.0
    poison_energy: float = 20.0     # poison still tastes like food at first
    poison_delay: int = 25          # ticks before sickness starts
    poison_damage: float = 6.0      # health lost per tick while sick
    poison_duration: int = 10       # ticks of sickness
    drink_amount: float = 40.0

    # Senses and brain
    policy: str = "brain"           # "brain" or "random" (a baseline to compare against)
    vision_range: int = 8           # tiles each vision ray reaches
    action_selection: str = "argmax"  # "argmax": take the brain's top action; "sample": draw by probability
    exploration: float = 0.1        # argmax only: chance of a random action instead

    # Reproduction and evolution (asexual for now; two parents comes later)
    maturity_age: int = 150         # ticks before an agent can reproduce
    reproduce_energy: float = 70.0  # energy needed to reproduce
    reproduce_water: float = 50.0   # water needed too: parched agents don't breed
    reproduce_cost_energy: float = 40.0
    reproduce_cost_water: float = 20.0
    reproduce_cooldown: int = 100   # ticks between children
    child_energy: float = 60.0
    child_water: float = 60.0
    mutation_scale: float = 0.05    # size of random changes to inherited weights
    max_population: int = 400       # safety cap so the simulation stays fast

    # Instincts: a brain file from `python -m emergent_world.instincts`. When set,
    # new agents start as mutated copies of it instead of random brains.
    instincts_path: str = ""

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
