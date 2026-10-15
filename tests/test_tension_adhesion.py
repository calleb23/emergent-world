from emergent_world.agents.agent import Action
from emergent_world.config import Config
from emergent_world.sim import Simulation
from emergent_world.world import physics
from emergent_world.world.grid import NO_PLANT
from emergent_world.world.items import JOIN_RECIPES, TAP_RECIPES


def _sim():
    sim = Simulation(Config(initial_agents=1, min_population=0, climate=False), seed=0)
    sim.world.terrain[:] = 0
    sim.world.plants[:] = NO_PLANT
    a = sim.agents[0]
    a.x, a.y = 30, 30
    return sim, a, sim.config.item_id


def _press(sim, a, held, below):
    item = sim.config.item_id
    sim.world.plants[a.x, a.y] = item(below)
    a.hands = item(held)
    for _ in range(20):   # sticky things can cling to the fingers for a moment
        if not a.hands or a.hands != item(held):
            break
        sim._act(a, Action.DROP)
    return sim.world.plants[a.x, a.y]


def test_all_join_and_tap_recipes_name_real_items():
    looks = {k.look for k in Config().items}
    for parts, result in JOIN_RECIPES.items():
        assert parts <= looks and result in looks
    for (held, target), result in TAP_RECIPES.items():
        assert {held, target, result} <= looks


def test_fibre_twists_into_cord_and_cord_lashes_a_spear():
    sim, a, item = _sim()
    assert _press(sim, a, "fibre", "fibre") == item("cord")
    assert _press(sim, a, "cord", "stick") == item("corded stick")
    assert _press(sim, a, "flint blade", "corded stick") == item("spear")


def test_resin_glues_but_not_when_soaked():
    sim, a, item = _sim()
    assert _press(sim, a, "resin", "stick") == item("resin stick")
    sim.world.wet[a.x, a.y] = 1.0
    strength, load = physics.binding_strength(sim.world, sim.config.item(item("resin")),
                                              sim.config.item(item("stick")), a.x, a.y)
    assert strength < 2 * load   # wet glue won't hold a stick


def test_a_weak_binder_cannot_hold_a_heavy_stone():
    sim, a, item = _sim()
    c = sim.config
    fibre, rock = c.item(item("fibre")), c.item(item("grey rock"))
    strength, load = physics.binding_strength(sim.world, fibre, rock, a.x, a.y)
    assert strength < 2 * load


def test_a_spear_reaches_a_cug_two_tiles_away():
    sim, a, item = _sim()
    a.hands = item("spear")
    sim.world.plants[a.x + 2, a.y] = item("cug")
    for _ in range(60):
        if sim.world.plants[a.x + 2, a.y] != item("cug"):
            break
        a.hands = item("spear")
        sim._act(a, Action.STRIKE)
    assert sim.world.plants[a.x + 2, a.y] == item("cug meat")


def test_bonds_give_way_under_strain():
    sim, a, item = _sim()
    broke = False
    for _ in range(400):
        a.hands = item("stone hammer")
        sim.world.plants[a.x, a.y] = item("flint nodule")
        sim._act(a, Action.STRIKE)
        if a.hands == item("stick"):
            broke = True
            break
    assert broke


def test_a_snare_catches_a_wandering_cug():
    sim, a, item = _sim()
    import numpy as np
    sim.world.plants[10, 10] = item("cug")
    for dx, dy in physics.NEIGHBOURS:
        sim.world.plants[10 + dx, 10 + dy] = item("snare")
    for _ in range(200):
        sim.world.move_critters(np.zeros(sim.world.plants.shape, dtype=bool))
    assert (sim.world.plants == item("snared cug")).any()


def test_cutting_a_pine_gives_resin_and_keeps_the_tree():
    sim, a, item = _sim()
    a.hands = item("flint blade")
    sim.world.plants[a.x, a.y] = item("pine tree")
    for _ in range(40):
        sim._act(a, Action.STRIKE)
    assert sim.world.plants[a.x, a.y] == item("pine tree")
    assert (sim.world.plants == item("resin")).any()


def test_wet_tinder_is_hard_to_light_and_daubed_shelters_do_not_burn():
    sim, a, item = _sim()
    sim.world.plants[5, 5] = item("dry grass tuft")
    dry = physics.burnable(sim.world, sim.config, 5, 5)
    sim.world.wet[5, 5] = 1.0
    assert physics.burnable(sim.world, sim.config, 5, 5) > 3 * dry
    sim.world.shelter[a.x, a.y] = True
    a.hands = item("mud")
    for _ in range(20):
        if not a.hands:
            break
        sim._act(a, Action.DROP)
    assert sim.world.reinforced[a.x, a.y] & physics.DAUBED
    assert physics.burnable(sim.world, sim.config, a.x, a.y) == 0


def test_fallen_trees_leave_logs_and_eggs_can_smash():
    sim, a, item = _sim()
    sim.world._wilt[item("tree")] = 1.0
    sim.world.plants[3, 3] = item("tree")
    sim.world.tick(growth=0.0)
    assert sim.world.plants[3, 3] == item("log")
    smashed = 0
    for _ in range(40):
        sim.world.plants[a.x, a.y] = NO_PLANT
        a.hands = item("bird egg")
        sim._act(a, Action.DROP)
        smashed += sim.world.plants[a.x, a.y] == item("broken egg")
    assert 0 < smashed < 40


def test_carrying_something_heavy_tires_you():
    sim, a, item = _sim()
    a.fatigue = 0.0
    a.hands = item("pot of water")
    sim._update_body(a)
    loaded = a.fatigue
    a.fatigue, a.hands = 0.0, 0
    sim._update_body(a)
    assert loaded > a.fatigue
