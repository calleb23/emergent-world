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
    PICK_UP = 7   # take the item underfoot into the hands
    DROP = 8      # put down what's in the hands (sticks dropped on one spot pile up)
    GIVE = 9      # hand what's held to the nearest person next to you
    STRIKE = 10   # hit what's underfoot with what's held
    RUB = 11      # rub what's held against what's underfoot (friction makes heat)


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
    brain: object = None    # the living brain, which learns; None when using the random policy
    genome: object = None   # the brain they were born with, which is what children inherit
    reward: float = 0.0     # how much better or worse they've felt since their last choice
    mood: float = 0.0       # a slow average of reward: how life is going lately
    last_choice: tuple | None = None   # (hidden, action, expected value), for learning
    comfort: float | None = None   # last hour's overall need satisfaction, for working out reward
    last_health: float = 100.0
    generation: int = 0
    parent_id: int = -1     # mother; -1 for agents with no parents (founders, top-ups)
    other_parent_id: int = -1  # father, when there was one
    sex: str = "f"          # "f" bears children; "m" fathers them
    lineage: str = ""       # a family tag children inherit, for tracking whose descendants win
    name: str = ""          # given name, for stories (agents never perceive names)
    line: str = ""          # family line, named after the founder it descends from
    kin: set = field(default_factory=set)        # ids of parent, children and siblings
    offspring: list = field(default_factory=list)  # ids of this agent's children
    memory: FoodMemory = field(default_factory=FoodMemory)
    aversion_gain: float = 0.0  # gene: how strongly bad food memories hold back eating
    events: list = field(default_factory=list)   # (tick, text): this agent's life story
    firsts: set = field(default_factory=set)  # first-time experiences already logged
    out_of: set = field(default_factory=set)     # needs currently at zero ("water", "food")
    fatigue: float = 0.0    # 0 rested .. 1 exhausted
    fat: float = 0.0        # stored energy for lean times
    grief: int = 0          # hours of grieving left
    known: dict = field(default_factory=dict)  # id -> bond 0..1: people met, and how close
    hands: int = 0          # item id being carried (0 = nothing)
    activity: str = ""      # what they're doing right now, for the viewer
    boredom: float = 0.0    # 0..1: builds while stuck in a small patch
    recent: list = field(default_factory=list)   # recent positions, for boredom
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
