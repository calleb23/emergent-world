"""Every kind of loose item in the world, as data.

Each row says how an item looks, what eating it does, where it appears and how
long it lasts. Agents never see these rows: they see colors, and learn the rest.
This table is the start of the world-law ledger the god will one day extend.

An item's id on the map is its position in the list plus one (0 = nothing).
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ItemKind:
    look: str                    # how an observer describes it in life stories
    color: tuple                 # what agents see (RGB)
    edible: bool = True          # False: biting it does nothing (rocks, sticks)
    energy: float = 0.0          # energy gained from eating it
    toxin: float = 0.0           # health lost per hour while sick (0 = harmless)
    toxin_delay: int = 0         # hours before sickness starts
    toxin_hours: int = 0         # hours the sickness lasts
    spawn_weight: float = 1.0    # how common it is among new items
    habitat: str = "anywhere"    # "anywhere", "near_water" or "dry" (far from water)
    wilt_chance: float = 0.002   # chance per hour it disappears; 0 = lasts forever
    group: str = "plant"         # for the legend: plant, berry, mushroom, nut, debris
    regrows: bool = True         # False: only placed when the world is made (rocks)
    # Critters move on their own. All zero for things that sit still.
    wanders: float = 0.0         # chance per hour of stepping to a neighbouring tile
    flees: float = 0.0           # chance per hour of scuttling away when someone is next to it
    breeds: float = 0.0          # chance per hour of making another one nearby (if there's room)
    max_count: int = 0           # the most of them the world holds at once
    # Physics. Hardness 0-10: a held thing breaks what's underfoot only if it's at
    # least as hard. Burning: things with a burn time catch fire from heat.
    hardness: float = 1.0
    mass: float = 1.0
    breaks_into: str = ""        # the look of what it becomes when struck hard enough
    burn_hours: int = 0          # 0 = doesn't burn; otherwise how long it feeds a fire
    ignites_at: float = 0.0      # heat (from rubbing or nearby fire) needed to catch fire
    cooks_into: str = ""         # the look of what it becomes after a few hours in a fire
    spawns: bool = True          # False: only ever made by physics (flakes, cooked food, ash)

    @property
    def harmful(self) -> bool:
        return self.toxin > 0


DEFAULT_ITEMS = (
    # The two original plants keep ids 1 and 2.
    ItemKind("green plant", (60, 170, 70), energy=30, spawn_weight=8.0, burn_hours=2, ignites_at=6),
    ItemKind("yellow-green plant", (90, 170, 60), energy=20, toxin=6.0,
             toxin_delay=25, toxin_hours=10, spawn_weight=1.0, burn_hours=2, ignites_at=6),
    # Berries: sweet but small. The purple ones look close enough to tempt.
    ItemKind("red berry", (205, 55, 60), energy=15, spawn_weight=2.0,
             habitat="near_water", group="berry"),
    ItemKind("purple berry", (130, 60, 165), energy=10, toxin=4.0,
             toxin_delay=6, toxin_hours=8, spawn_weight=1.0,
             habitat="near_water", group="berry"),
    # Mushrooms grow in the damp. The pale one is slow and deadly, like a death cap:
    # sickness starts 40 hours later, so it's hard to tell what caused it.
    ItemKind("brown mushroom", (140, 100, 60), energy=25, spawn_weight=1.5,
             habitat="near_water", wilt_chance=0.004, group="mushroom",
             cooks_into="roasted mushroom"),
    ItemKind("pale mushroom", (225, 220, 200), energy=20, toxin=9.0,
             toxin_delay=40, toxin_hours=10, spawn_weight=0.5,
             habitat="near_water", wilt_chance=0.004, group="mushroom",
             cooks_into="roasted mushroom"),
    # Nuts: rich and long-lasting, but rare, only away from water, and locked in
    # a hard shell. Crack one with something harder, or roast it.
    ItemKind("nut", (175, 125, 55), edible=False, spawn_weight=0.8, habitat="dry",
             wilt_chance=0.0005, group="nut", hardness=4, breaks_into="cracked nut",
             cooks_into="cracked nut"),
    # Things that can't be eaten. Instinct says try anything solid, so agents
    # will bite them until they learn better.
    ItemKind("grey rock", (128, 128, 122), edible=False, spawn_weight=1.5,
             wilt_chance=0.0, regrows=False, group="debris", hardness=7, mass=3,
             breaks_into="sharp flake"),
    ItemKind("stick", (105, 82, 52), edible=False, spawn_weight=1.0,
             wilt_chance=0.0008, group="debris", hardness=3, burn_hours=6, ignites_at=5),
    # The cug: a small, skittish, teal critter that skitters about the damp ground
    # near ponds. It wanders, bolts when someone gets close, and makes more cugs
    # when there's room. Catching one takes luck or persistence; it's a fine meal.
    ItemKind("cug", (70, 205, 190), energy=35, spawn_weight=0.6, habitat="near_water",
             wilt_chance=0.0004, regrows=False, wanders=0.35, flees=0.7,
             breeds=0.004, max_count=120, group="critter", cooks_into="roasted cug"),
    # Things only physics makes: tools, cooked food, ash.
    ItemKind("sharp flake", (190, 195, 205), edible=False, spawns=False, regrows=False,
             wilt_chance=0.0, group="tool", hardness=8, mass=0.5),
    ItemKind("cracked nut", (215, 170, 100), energy=45, spawns=False, regrows=False,
             wilt_chance=0.002, group="nut"),
    ItemKind("roasted mushroom", (120, 75, 45), energy=28, spawns=False, regrows=False,
             wilt_chance=0.004, group="cooked"),
    ItemKind("roasted cug", (165, 95, 70), energy=45, spawns=False, regrows=False,
             wilt_chance=0.004, group="cooked"),
    ItemKind("ash", (70, 68, 66), edible=False, spawns=False, regrows=False,
             wilt_chance=0.01, group="debris"),
)
