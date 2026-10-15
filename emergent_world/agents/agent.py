"""Agent bodies: position, needs, health, and the actions they can take."""

from dataclasses import dataclass, field
from enum import IntEnum


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
