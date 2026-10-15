from emergent_world.agents.agent import Action, Sickness
from emergent_world.config import Config
from emergent_world.sim import Simulation
from emergent_world.world import physics
from emergent_world.world.grid import NO_PLANT
from emergent_world.world.items import STRIKE_RECIPES


def _sim():
    sim = Simulation(Config(initial_agents=1, min_population=0, climate=False), seed=0)
    sim.world.terrain[:] = 0
    sim.world.plants[:] = NO_PLANT
    a = sim.agents[0]
    a.x, a.y = 30, 30
    return sim, a, sim.config.item_id


def _strike_until_changed(sim, a, tries=40):
    start = sim.world.plants[a.x, a.y]
    for _ in range(tries):
        if sim.world.plants[a.x, a.y] != start:
            return
        sim._act(a, Action.STRIKE)


def test_every_item_named_anywhere_exists():
    c = Config()
    looks = {k.look for k in c.items}
    for k in c.items:
        for name in (k.breaks_into, k.cooks_into, k.holds_water, k.empties_into, k.grows_into):
            assert not name or name in looks, name
        for name, _ in k.drops:
            assert name in looks
    for (held, target), result in STRIKE_RECIPES.items():
        assert {held, target, result} <= looks
    assert len({k.color for k in c.items}) == len(c.items)


def test_trees_and_hives_cannot_be_carried():
    sim, a, item = _sim()
    for look in ("tree", "beehive", "log"):
        sim.world.plants[a.x, a.y] = item(look)
        sim._act(a, Action.PICK_UP)
        assert a.hands == 0 and sim.world.plants[a.x, a.y] == item(look)


def test_a_flake_whittles_a_stick_and_strips_a_reed():
    sim, a, item = _sim()
    a.hands = item("sharp flake")
    for target, result in (("stick", "sharpened stick"), ("reed", "fibre"), ("cug", "cug meat")):
        sim.world.plants[a.x, a.y] = item(target)
        _strike_until_changed(sim, a)
        assert sim.world.plants[a.x, a.y] == item(result)
        assert a.hands == item("sharp flake")   # tools aren't used up


def test_a_hard_tool_fells_a_tree_into_a_log():
    sim, a, item = _sim()
    a.hands = item("flint blade")
    sim.world.plants[a.x, a.y] = item("tree")
    _strike_until_changed(sim, a)
    assert sim.world.plants[a.x, a.y] == item("log")


def test_hives_sting_whoever_knocks_honey_out():
    sim, a, item = _sim()
    a.hands = item("stick")
    sim.world.plants[a.x, a.y] = item("beehive")
    before = a.health
    _strike_until_changed(sim, a)
    assert sim.world.plants[a.x, a.y] == item("honeycomb")
    assert a.health < before
    assert a.memory.level(sim.config.items[item("beehive") - 1].color) > 0


def test_thorns_hurt_underfoot():
    sim, a, item = _sim()
    sim.world.plants[a.x, a.y] = item("thorn bush")
    before = a.health
    sim._update_body(a)
    assert a.health < before


def test_flint_sparks_light_dry_grass():
    sim, a, item = _sim()
    a.hands = item("flint nodule")
    sim.world.plants[a.x, a.y] = item("grey rock")
    sim.world.plants[a.x + 1, a.y] = item("dry grass tuft")
    sim._act(a, Action.STRIKE)
    assert sim.world.fire[a.x + 1, a.y] > 0


def test_a_pot_carries_water_away_from_the_pond():
    sim, a, item = _sim()
    sim.world.terrain[a.x - 1, a.y] = 1   # a pond beside them
    a.hands = item("clay pot")
    sim._act(a, Action.DRINK)
    assert a.hands == item("pot of water")
    a.x += 5
    a.water = 10
    sim._act(a, Action.DRINK)
    assert a.water > 10 and a.hands == item("clay pot")


def test_clay_dropped_in_a_fire_becomes_a_pot():
    sim, a, item = _sim()
    sim.world.plants[a.x, a.y] = item("stick")
    physics.ignite(sim, a.x, a.y)
    a.hands = item("clay lump")
    sim._act(a, Action.DROP)
    for _ in range(physics.COOK_HOURS):
        physics.tick(sim)
    assert sim.world.plants[a.x, a.y] == item("clay pot")


def test_feeding_a_fire_keeps_it_going():
    sim, a, item = _sim()
    sim.world.plants[a.x, a.y] = item("stick")
    physics.ignite(sim, a.x, a.y)
    fuel = sim.world.fire[a.x, a.y]
    a.hands = item("fallen branch")
    sim._act(a, Action.DROP)
    assert a.hands == 0 and sim.world.fire[a.x, a.y] > fuel


def test_blue_flowers_cure_sickness():
    sim, a, item = _sim()
    a.sicknesses.append(Sickness(0, 10, 5.0))
    sim.world.plants[a.x, a.y] = item("blue flower")
    sim._act(a, Action.EAT)
    assert not a.sicknesses


def test_seeds_grow_and_trees_shed():
    sim, a, item = _sim()
    sim.world.plants[10, 10] = item("grass seed")
    for _ in range(7 * 24):
        physics.grow(sim)
    assert sim.world.plants[10, 10] == item("green plant")
    sim.world.plants[20, 20] = item("tree")
    for _ in range(3000):
        physics.shed(sim)
    around = {int(sim.world.plants[20 + dx, 20 + dy]) for dx, dy in physics.NEIGHBOURS}
    assert around & {item("apple"), item("fallen branch")}


def test_branches_pile_up_into_shelters_like_sticks():
    sim, a, item = _sim()
    for _ in range(sim.config.sticks_per_shelter):
        a.hands = item("fallen branch")
        sim._act(a, Action.DROP)
    assert sim.world.shelter[a.x, a.y]
