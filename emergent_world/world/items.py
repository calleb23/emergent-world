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
    immovable: bool = False      # rooted or too heavy to pick up (trees, bushes, hives, logs)
    prickly: float = 0.0         # damage per hour to anyone standing on or handling it
    stings: float = 0.0          # damage to anyone who strikes it
    cures: bool = False          # eating it ends sickness
    sparks: bool = False         # struck on something very hard, it throws sparks
    holds_water: str = ""        # a container: the look it becomes when filled at water
    water: float = 0.0           # drinking it from the hands restores this much water
    empties_into: str = ""       # what a filled container becomes once drunk from
    drops: tuple = ()            # (look, chance per hour): what it sheds onto open ground beside it
    grows_into: str = ""         # dropped on open grass, it grows into this...
    grow_days: int = 0           # ...after this many days

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

    # --- Trees and wood -------------------------------------------------------
    ItemKind("tree", (34, 110, 50), edible=False, spawn_weight=1.2, regrows=False, wilt_chance=0.0,
             group="tree", immovable=True, hardness=6, mass=50, burn_hours=40, ignites_at=9,
             breaks_into="log", drops=(("apple", 0.002), ("fallen branch", 0.002))),
    ItemKind("apple", (220, 60, 45), energy=25, spawns=False, regrows=False, wilt_chance=0.003,
             group="fruit"),
    ItemKind("fallen branch", (125, 95, 60), edible=False, spawns=False, regrows=False,
             wilt_chance=0.0005, group="wood", hardness=4, mass=2, burn_hours=8, ignites_at=5),
    ItemKind("log", (95, 65, 40), edible=False, spawns=False, regrows=False, wilt_chance=0.0,
             group="wood", immovable=True, hardness=6, mass=8, burn_hours=30, ignites_at=7),
    ItemKind("dry grass tuft", (200, 185, 110), edible=False, spawn_weight=1.2, habitat="dry",
             wilt_chance=0.003, group="plant", hardness=0.5, burn_hours=1, ignites_at=2),

    # --- By the water ---------------------------------------------------------
    ItemKind("reed", (110, 150, 80), edible=False, spawn_weight=1.5, habitat="near_water",
             wilt_chance=0.002, group="plant", hardness=1, burn_hours=1, ignites_at=4),
    ItemKind("fibre", (200, 190, 150), edible=False, spawns=False, regrows=False,
             wilt_chance=0.001, group="material", burn_hours=1, ignites_at=3),
    ItemKind("clay lump", (165, 110, 85), edible=False, spawn_weight=0.8, habitat="near_water",
             regrows=False, wilt_chance=0.0, group="material", hardness=2, mass=2,
             cooks_into="clay pot"),
    ItemKind("clay pot", (190, 120, 80), edible=False, spawns=False, regrows=False, wilt_chance=0.0,
             group="tool", hardness=3, mass=1.5, breaks_into="pottery shard",
             holds_water="pot of water"),
    ItemKind("pot of water", (120, 140, 190), edible=False, spawns=False, regrows=False,
             wilt_chance=0.0, group="tool", hardness=3, mass=3, water=40, empties_into="clay pot"),
    ItemKind("pottery shard", (175, 105, 70), edible=False, spawns=False, regrows=False,
             wilt_chance=0.0, group="tool", hardness=5, mass=0.3),
    ItemKind("bird egg", (235, 230, 215), energy=20, spawn_weight=0.5, habitat="near_water",
             wilt_chance=0.003, group="egg", hardness=0.5, breaks_into="", cooks_into="cooked egg"),
    ItemKind("cooked egg", (240, 210, 120), energy=30, spawns=False, regrows=False,
             wilt_chance=0.004, group="cooked"),

    # --- Dry ground -----------------------------------------------------------
    ItemKind("flint nodule", (70, 75, 95), edible=False, spawn_weight=0.6, habitat="dry",
             regrows=False, wilt_chance=0.0, group="stone", hardness=8, mass=1.5,
             breaks_into="flint blade", sparks=True),
    ItemKind("flint blade", (40, 45, 70), edible=False, spawns=False, regrows=False,
             wilt_chance=0.0, group="tool", hardness=9, mass=0.5),
    ItemKind("beehive", (205, 160, 40), edible=False, spawn_weight=0.3, habitat="dry", regrows=False,
             wilt_chance=0.0, group="hive", immovable=True, hardness=2, stings=12.0,
             burn_hours=4, ignites_at=4),
    ItemKind("honeycomb", (245, 190, 50), energy=55, spawns=False, regrows=False,
             wilt_chance=0.001, group="sweet"),

    # --- Hazards, medicine and seeds -------------------------------------------
    ItemKind("thorn bush", (80, 105, 60), edible=False, spawn_weight=0.8, regrows=False,
             wilt_chance=0.0, group="plant", immovable=True, prickly=3.0, hardness=3,
             burn_hours=4, ignites_at=4),
    ItemKind("blue flower", (80, 110, 220), energy=5, spawn_weight=0.4, wilt_chance=0.003,
             group="plant", cures=True),
    ItemKind("grass seed", (180, 175, 95), edible=False, spawn_weight=0.8, wilt_chance=0.002,
             group="seed", grows_into="green plant", grow_days=7),

    # --- Made by hand ---------------------------------------------------------
    ItemKind("sharpened stick", (150, 115, 70), edible=False, spawns=False, regrows=False,
             wilt_chance=0.0003, group="tool", hardness=5, mass=1, burn_hours=4, ignites_at=5),
    ItemKind("cug meat", (200, 90, 90), energy=30, spawns=False, regrows=False,
             wilt_chance=0.006, group="meat", cooks_into="roasted cug"),
)

# What striking one thing with another makes, beyond plain breaking: (held, target) -> result.
# A held thing must still be at least as hard as its target. Tools aren't used up.
STRIKE_RECIPES = {
    ("sharp flake", "stick"): "sharpened stick",
    ("flint blade", "stick"): "sharpened stick",
    ("pottery shard", "stick"): "sharpened stick",
    ("sharp flake", "fallen branch"): "sharpened stick",
    ("flint blade", "fallen branch"): "sharpened stick",
    ("sharp flake", "reed"): "fibre",
    ("flint blade", "reed"): "fibre",
    ("pottery shard", "reed"): "fibre",
    ("sharp flake", "cug"): "cug meat",
    ("flint blade", "cug"): "cug meat",
    ("sharpened stick", "cug"): "cug meat",
    ("stick", "beehive"): "honeycomb",
    ("fallen branch", "beehive"): "honeycomb",
    ("sharpened stick", "beehive"): "honeycomb",
}
