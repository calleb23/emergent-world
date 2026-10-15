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

    @property
    def harmful(self) -> bool:
        return self.toxin > 0


DEFAULT_ITEMS = (
    # The two original plants keep ids 1 and 2.
    ItemKind("green plant", (60, 170, 70), energy=30, spawn_weight=8.0),
    ItemKind("yellow-green plant", (90, 170, 60), energy=20, toxin=6.0,
             toxin_delay=25, toxin_hours=10, spawn_weight=1.0),
    # Berries: sweet but small. The purple ones look close enough to tempt.
    ItemKind("red berry", (205, 55, 60), energy=15, spawn_weight=2.0,
             habitat="near_water", group="berry"),
    ItemKind("purple berry", (130, 60, 165), energy=10, toxin=4.0,
             toxin_delay=6, toxin_hours=8, spawn_weight=1.0,
             habitat="near_water", group="berry"),
    # Mushrooms grow in the damp. The pale one is slow and deadly, like a death cap:
    # sickness starts 40 hours later, so it's hard to tell what caused it.
    ItemKind("brown mushroom", (140, 100, 60), energy=25, spawn_weight=1.5,
             habitat="near_water", wilt_chance=0.004, group="mushroom"),
    ItemKind("pale mushroom", (225, 220, 200), energy=20, toxin=9.0,
             toxin_delay=40, toxin_hours=10, spawn_weight=0.5,
             habitat="near_water", wilt_chance=0.004, group="mushroom"),
    # Nuts: rich and long-lasting, but rare and only away from water.
    ItemKind("nut", (175, 125, 55), energy=45, spawn_weight=0.8,
             habitat="dry", wilt_chance=0.0005, group="nut"),
    # Things that can't be eaten. Instinct says try anything solid, so agents
    # will bite them until they learn better.
    ItemKind("grey rock", (128, 128, 122), edible=False, spawn_weight=1.5,
             wilt_chance=0.0, regrows=False, group="debris"),
    ItemKind("stick", (105, 82, 52), edible=False, spawn_weight=1.0,
             wilt_chance=0.0008, group="debris"),
)
