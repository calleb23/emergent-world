"""All tunable numbers in one place, so experiments change config, not code."""

from dataclasses import dataclass


@dataclass
class Config:
    # World
    width: int = 64
    height: int = 64
    water_lakes: int = 4            # number of lakes scattered on the map
    lake_radius: tuple = (3, 6)     # min/max lake radius in tiles
    initial_plant_density: float = 0.15   # share of grass tiles that start with a plant
    regrow_chance: float = 0.002          # per empty grass tile, per tick
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
    energy_drain: float = 0.5       # per tick
    water_drain: float = 0.8        # per tick
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
