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
    rots_into: str = ""          # what it leaves behind when it wilts (a fallen tree leaves a log)
    # Tension and adhesion. Pressing one thing onto another (dropping it on top) can
    # join them, if a binder holds: a flexible thing ties with its tensile strength,
    # a sticky thing glues with its adhesion (wet glue barely holds). Either must
    # bear at least twice the weight of what it holds together.
    tensile: float = 0.0         # pull it can take before snapping (cord, vine, fibre)
    flexible: bool = False       # bends and ties: it can lash things together
    sticky: float = 0.0          # adhesion: it glues (resin, mud); sticks to fingers too
    bond: float = 0.0            # for joined things: how strongly the parts hold together
    parts: tuple = ()            # what a joined thing falls back into when its bond gives
    brittle: float = 0.0         # chance it breaks into `breaks_into` when put down
    sharp: bool = False          # cuts: a sharp thing kills a critter, leaving its carcass
    carcass: str = ""            # what a critter leaves when killed
    reach: int = 0               # tiles a held tool can strike across (a spear, a bow)
    traps: str = ""              # a critter stepping onto it is caught, becoming this
    # Nature: animals that eat other things, bite people, and plants that follow the
    # seasons and the rain.
    eats: tuple = ()             # looks of things a critter eats when it's next to them
    hunger: float = 0.0          # chance per hour it eats one of them, if any are beside it
    bites: float = 0.0           # damage to a person next to it (or handling it), when it bites
    bite_chance: float = 0.0     # chance per hour it bites someone beside it
    seasonal: bool = False       # its drops follow the growing season (fruit in summer, none in winter)
    after_rain: float = 0.0      # chance per hour it springs up on soaked open ground
    warm: bool = False           # held, it keeps off the cold (not the wet)
    cover: bool = False          # natural shelter: anyone on or beside it is out of the weather

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
             breeds=0.004, max_count=120, group="critter", cooks_into="roasted cug",
             carcass="cug meat"),
    # Things only physics makes: tools, cooked food, ash.
    ItemKind("sharp flake", (190, 195, 205), edible=False, spawns=False, regrows=False,
             wilt_chance=0.0, group="tool", hardness=8, mass=0.5, sharp=True),
    ItemKind("cracked nut", (215, 170, 100), energy=45, spawns=False, regrows=False,
             wilt_chance=0.002, group="nut"),
    ItemKind("roasted mushroom", (120, 75, 45), energy=28, spawns=False, regrows=False,
             wilt_chance=0.004, group="cooked"),
    ItemKind("roasted cug", (165, 95, 70), energy=45, spawns=False, regrows=False,
             wilt_chance=0.004, group="cooked"),
    ItemKind("ash", (70, 68, 66), edible=False, spawns=False, regrows=False,
             wilt_chance=0.01, group="debris"),

    # --- Trees and wood -------------------------------------------------------
    ItemKind("tree", (34, 110, 50), edible=False, spawn_weight=1.2, regrows=False, wilt_chance=0.00003,
             group="tree", immovable=True, hardness=6, mass=50, burn_hours=40, ignites_at=9,
             breaks_into="log", rots_into="log", drops=(("apple", 0.002), ("fallen branch", 0.002))),
    ItemKind("apple", (220, 60, 45), energy=25, spawns=False, regrows=False, wilt_chance=0.003,
             group="fruit", rots_into="rotten apple"),
    ItemKind("fallen branch", (125, 95, 60), edible=False, spawns=False, regrows=False,
             wilt_chance=0.0005, group="wood", hardness=4, mass=2, burn_hours=8, ignites_at=5),
    ItemKind("log", (95, 65, 40), edible=False, spawns=False, regrows=False, wilt_chance=0.0003,
             group="wood", immovable=True, hardness=6, mass=8, burn_hours=30, ignites_at=7),
    ItemKind("dry grass tuft", (200, 185, 110), edible=False, spawn_weight=1.2, habitat="dry",
             wilt_chance=0.003, group="plant", hardness=0.5, burn_hours=1, ignites_at=2),

    # --- By the water ---------------------------------------------------------
    ItemKind("reed", (110, 150, 80), edible=False, spawn_weight=1.5, habitat="near_water",
             wilt_chance=0.002, group="plant", hardness=1, burn_hours=1, ignites_at=4),
    ItemKind("fibre", (200, 190, 150), edible=False, spawns=False, regrows=False,
             wilt_chance=0.001, group="material", burn_hours=1, ignites_at=3,
             flexible=True, tensile=4, mass=0.2),
    ItemKind("clay lump", (165, 110, 85), edible=False, spawn_weight=0.8, habitat="near_water",
             regrows=False, wilt_chance=0.0, group="material", hardness=2, mass=2,
             cooks_into="clay pot"),
    ItemKind("clay pot", (190, 120, 80), edible=False, spawns=False, regrows=False, wilt_chance=0.0,
             group="tool", hardness=3, mass=1.5, breaks_into="pottery shard", brittle=0.05,
             holds_water="pot of water"),
    ItemKind("pot of water", (120, 140, 190), edible=False, spawns=False, regrows=False,
             wilt_chance=0.004, rots_into="clay pot", group="tool", hardness=3, mass=3, water=40,
             empties_into="clay pot", breaks_into="pottery shard", brittle=0.05),   # left out, it dries up
    ItemKind("pottery shard", (175, 105, 70), edible=False, spawns=False, regrows=False,
             wilt_chance=0.0, group="tool", hardness=5, mass=0.3, sharp=True),
    ItemKind("bird egg", (235, 230, 215), energy=20, spawn_weight=0.2, habitat="near_water",
             wilt_chance=0.003, group="egg", hardness=0.5, breaks_into="broken egg", brittle=0.3,
             cooks_into="cooked egg"),
    ItemKind("cooked egg", (240, 210, 120), energy=30, spawns=False, regrows=False,
             wilt_chance=0.004, group="cooked"),

    # --- Dry ground -----------------------------------------------------------
    ItemKind("flint nodule", (70, 75, 95), edible=False, spawn_weight=0.6, habitat="dry",
             regrows=False, wilt_chance=0.0, group="stone", hardness=8, mass=1.5,
             breaks_into="flint blade", sparks=True),
    ItemKind("flint blade", (40, 45, 70), edible=False, spawns=False, regrows=False,
             wilt_chance=0.0, group="tool", hardness=9, mass=0.5, sharp=True),
    ItemKind("beehive", (205, 160, 40), edible=False, spawn_weight=0.3, habitat="dry", regrows=False,
             wilt_chance=0.0, group="hive", immovable=True, hardness=2, stings=12.0,
             burn_hours=4, ignites_at=4),
    ItemKind("honeycomb", (245, 190, 50), energy=55, spawns=False, regrows=False,
             wilt_chance=0.001, group="sweet", sticky=2),

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
             wilt_chance=0.0003, group="tool", hardness=5, mass=1, burn_hours=4, ignites_at=5,
             sharp=True),
    ItemKind("cug meat", (200, 90, 90), energy=30, spawns=False, regrows=False,
             wilt_chance=0.006, group="meat", cooks_into="roasted cug", rots_into="rotten meat"),
    ItemKind("broken egg", (250, 220, 90), energy=12, spawns=False, regrows=False,
             wilt_chance=0.02, group="egg"),

    # --- Pines, vines and saplings --------------------------------------------
    ItemKind("pine tree", (25, 80, 55), edible=False, spawn_weight=0.4, regrows=False, cover=True,
             wilt_chance=0.00003, rots_into="log", group="tree", immovable=True, hardness=6, mass=50,
             burn_hours=50, ignites_at=7, breaks_into="log", drops=(("pine cone", 0.002),)),
    ItemKind("pine cone", (150, 105, 75), edible=False, spawns=False, regrows=False,
             wilt_chance=0.003, group="wood", hardness=2, mass=0.3, burn_hours=2, ignites_at=3),
    ItemKind("resin", (230, 150, 30), edible=False, spawns=False, regrows=False,
             wilt_chance=0.0005, group="material", sticky=7, mass=0.3, burn_hours=3, ignites_at=2),
    ItemKind("vine", (45, 140, 30), edible=False, spawn_weight=0.3, wilt_chance=0.002,
             group="plant", flexible=True, tensile=5, mass=0.5, burn_hours=1, ignites_at=6),
    ItemKind("sapling", (120, 190, 90), edible=False, spawn_weight=0.1, wilt_chance=0.001,
             group="tree", immovable=True, hardness=2, mass=6, grows_into="tree", grow_days=120,
             burn_hours=2, ignites_at=6),
    ItemKind("springy pole", (175, 140, 85), edible=False, spawns=False, regrows=False,
             wilt_chance=0.0005, group="wood", hardness=3, mass=1.5, burn_hours=3, ignites_at=5),
    ItemKind("mud", (110, 85, 60), edible=False, spawn_weight=0.3, habitat="near_water",
             wilt_chance=0.004, group="material", sticky=4, mass=2),

    # --- Joined by hand: cord, glue and lashing --------------------------------
    ItemKind("cord", (215, 200, 160), edible=False, spawns=False, regrows=False,
             wilt_chance=0.0005, group="material", flexible=True, tensile=7, mass=0.2,
             burn_hours=1, ignites_at=3),
    ItemKind("corded stick", (140, 110, 80), edible=False, spawns=False, regrows=False,
             wilt_chance=0.0003, group="tool", flexible=True, tensile=6, hardness=3, mass=1.2,
             burn_hours=5, ignites_at=5),
    ItemKind("resin stick", (170, 115, 45), edible=False, spawns=False, regrows=False,
             wilt_chance=0.0003, group="tool", sticky=6, hardness=3, mass=1.2,
             burn_hours=7, ignites_at=3),
    ItemKind("spear", (165, 165, 185), edible=False, spawns=False, regrows=False,
             wilt_chance=0.0, group="tool", hardness=9, mass=1.5, sharp=True, reach=2,
             bond=6, parts=("stick", "flint blade")),
    ItemKind("stone hammer", (105, 105, 110), edible=False, spawns=False, regrows=False,
             wilt_chance=0.0, group="tool", hardness=8, mass=4, bond=6, parts=("stick", "grey rock")),
    ItemKind("bow", (190, 150, 95), edible=False, spawns=False, regrows=False,
             wilt_chance=0.0002, group="tool", hardness=9, mass=1.5, sharp=True, reach=4,
             bond=7, parts=("springy pole", "cord")),
    ItemKind("snare", (225, 180, 140), edible=False, spawns=False, regrows=False,
             wilt_chance=0.0003, group="tool", mass=1, traps="snared cug"),
    ItemKind("snared cug", (60, 160, 150), energy=35, spawns=False, regrows=False,
             wilt_chance=0.002, group="critter", cooks_into="roasted cug", carcass="cug meat"),

    # --- Animals --------------------------------------------------------------
    # Deer graze plants and bolt from people; too big to carry, but a fine kill.
    ItemKind("deer", (185, 135, 85), edible=False, spawn_weight=0.15, regrows=False, wilt_chance=0.0001,
             wanders=0.3, flees=0.9, breeds=0.0015, max_count=16, group="animal", mass=40, hardness=2,
             eats=("green plant", "yellow-green plant", "red berry"), hunger=0.05, carcass="venison"),
    ItemKind("venison", (150, 40, 50), energy=60, spawns=False, regrows=False, wilt_chance=0.005,
             group="meat", mass=3, cooks_into="roasted venison", rots_into="rotten meat"),
    ItemKind("roasted venison", (125, 60, 40), energy=80, spawns=False, regrows=False,
             wilt_chance=0.003, group="cooked"),
    ItemKind("rotten meat", (110, 120, 70), energy=10, toxin=7.0, toxin_delay=4, toxin_hours=8,
             spawns=False, regrows=False, wilt_chance=0.01, group="meat"),
    # Wolves hunt deer and cugs, and bite anyone who comes too close.
    ItemKind("wolf", (95, 95, 105), edible=False, spawn_weight=0.05, habitat="dry", regrows=False,
             wilt_chance=0.0001, wanders=0.45, breeds=0.0006, max_count=6, group="animal", mass=30,
             hardness=3, eats=("cug", "deer", "snared cug", "cug meat", "venison"), hunger=0.15,
             bites=10.0, bite_chance=0.12, carcass="wolf pelt"),
    ItemKind("wolf pelt", (130, 125, 120), edible=False, spawns=False, regrows=False,
             wilt_chance=0.0002, group="material", mass=2, warm=True, flexible=True, tensile=3,
             burn_hours=3, ignites_at=6),
    # Snakes lie still in dry grass and bite if disturbed.
    ItemKind("snake", (150, 160, 60), edible=False, spawn_weight=0.15, habitat="dry", regrows=False,
             wilt_chance=0.0002, wanders=0.08, flees=0.2, breeds=0.0008, max_count=15, group="animal",
             bites=10.0, bite_chance=0.04, eats=("cug", "bird egg"), hunger=0.03, carcass="snake meat"),
    ItemKind("snake meat", (210, 160, 150), energy=20, spawns=False, regrows=False, wilt_chance=0.006,
             group="meat", cooks_into="roasted cug", rots_into="rotten meat"),
    # Songbirds flit about and lay eggs beside them.
    ItemKind("songbird", (240, 110, 170), edible=False, spawn_weight=0.2, regrows=False,
             wilt_chance=0.0002, wanders=0.6, flees=0.95, breeds=0.002, max_count=40, group="animal",
             mass=0.3, drops=(("bird egg", 0.002),), seasonal=True, carcass="bird meat",
             eats=("grass seed", "red berry"), hunger=0.03),
    ItemKind("bird meat", (225, 130, 120), energy=20, spawns=False, regrows=False, wilt_chance=0.006,
             group="meat", cooks_into="roasted bird", rots_into="rotten meat"),
    ItemKind("roasted bird", (180, 110, 60), energy=30, spawns=False, regrows=False,
             wilt_chance=0.004, group="cooked"),
    # Fish live in the ponds; a spear or bow struck at the water can take one.
    ItemKind("fish", (150, 180, 200), energy=35, spawns=False, regrows=False, wilt_chance=0.006,
             group="meat", cooks_into="cooked fish", rots_into="rotten meat"),
    ItemKind("cooked fish", (220, 180, 140), energy=45, spawns=False, regrows=False,
             wilt_chance=0.004, group="cooked"),

    # --- Plants that follow the seasons and the rain ---------------------------
    ItemKind("berry bush", (140, 40, 70), edible=False, spawn_weight=0.4, habitat="near_water",
             regrows=False, wilt_chance=0.00005, group="plant", immovable=True, hardness=2,
             drops=(("red berry", 0.004),), seasonal=True, burn_hours=4, ignites_at=5),
    ItemKind("rotten apple", (120, 70, 40), energy=5, toxin=2.0, toxin_delay=3, toxin_hours=3,
             spawns=False, regrows=False, wilt_chance=0.002, group="fruit",
             grows_into="sapling", grow_days=20),   # the core takes root
    ItemKind("puffball", (245, 245, 235), energy=15, spawns=False, regrows=False, wilt_chance=0.01,
             group="mushroom", after_rain=0.0004, cooks_into="roasted mushroom"),

    # --- Natural shelter --------------------------------------------------------
    # A rock overhang keeps off rain and cold like a shelter; so does a thick pine.
    ItemKind("rock overhang", (150, 140, 130), edible=False, spawn_weight=0.25, regrows=False,
             wilt_chance=0.0, group="stone", immovable=True, hardness=9, mass=500, cover=True),
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
    ("sharp flake", "sapling"): "springy pole",
    ("flint blade", "sapling"): "springy pole",
    ("stick", "beehive"): "honeycomb",
    ("fallen branch", "beehive"): "honeycomb",
    ("sharpened stick", "beehive"): "honeycomb",
    ("stone hammer", "nut"): "cracked nut",
}

# Tapping: a sharp cut into something living makes it give something up, beside it,
# without destroying it. (held, target) -> what appears on open ground next to it.
TAP_RECIPES = {
    ("sharp flake", "pine tree"): "resin",
    ("flint blade", "pine tree"): "resin",
    ("spear", "pine tree"): "resin",
}

# Pressing one thing onto another: {a, b} -> what they join into (either order).
# Whether it holds is physics: see `binding_strength` in physics.py.
JOIN_RECIPES = {
    frozenset({"fibre"}): "cord",                          # two lengths of fibre twist into cord
    frozenset({"cord", "stick"}): "corded stick",
    frozenset({"vine", "stick"}): "corded stick",
    frozenset({"resin", "stick"}): "resin stick",
    frozenset({"corded stick", "flint blade"}): "spear",
    frozenset({"corded stick", "sharp flake"}): "spear",
    frozenset({"resin stick", "flint blade"}): "spear",
    frozenset({"resin stick", "sharp flake"}): "spear",
    frozenset({"corded stick", "grey rock"}): "stone hammer",
    frozenset({"resin stick", "grey rock"}): "stone hammer",
    frozenset({"cord", "springy pole"}): "bow",
    frozenset({"vine", "springy pole"}): "bow",
    frozenset({"cord", "sharpened stick"}): "snare",
    frozenset({"vine", "sharpened stick"}): "snare",
}
