"""Agent bodies: position, needs, health, and the actions they can take."""

from dataclasses import dataclass, field
from enum import IntEnum

from emergent_world.agents.memory import FoodMemory


class Action(IntEnum):
    NORTH = 0
    SOUTH = 1
    EAST = 2
    WEST = 3
    EAT = 4
    DRINK = 5
    REST = 6


MOVES = {
    Action.NORTH: (0, -1),
    Action.SOUTH: (0, 1),
    Action.EAST: (1, 0),
    Action.WEST: (-1, 0),
}


@dataclass
class Sickness:
    """A pending poisoning: starts after `delay` ticks, lasts `duration` ticks."""
    delay: int
    duration: int
    damage: float
    felt: bool = False   # has the agent started feeling it yet?


@dataclass
class Agent:
    id: int
    x: int
    y: int
    energy: float
    water: float
    health: float
    lifespan: int
    brain: object = None    # a Brain; None when using the random policy
    generation: int = 0
    parent_id: int = -1     # -1 for agents spawned by the bootstrap
    lineage: str = ""       # a family tag children inherit, for tracking whose descendants win
    kin: set = field(default_factory=set)        # ids of parent, children and siblings
    offspring: list = field(default_factory=list)  # ids of this agent's children
    memory: FoodMemory = field(default_factory=FoodMemory)
    aversion_gain: float = 0.0  # gene: how strongly bad food memories hold back eating
    events: list = field(default_factory=list)   # (tick, text): this agent's life story
    firsts: set = field(default_factory=set)  # first-time experiences already logged
    out_of: set = field(default_factory=set)     # needs currently at zero ("water", "food")
    fatigue: float = 0.0    # 0 rested .. 1 exhausted
    asleep: bool = False
    children: int = 0
    reproduce_cooldown: int = 0
    age: int = 0
    alive: bool = True
    cause_of_death: str = ""
    sicknesses: list = field(default_factory=list)
    last_damage: str = ""   # what hurt this agent most recently

    def take_damage(self, amount: float, source: str):
        self.health -= amount
        self.last_damage = source
