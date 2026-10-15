from emergent_world.agents.agent import Action
from emergent_world.config import Config
from emergent_world.sim import Simulation
from emergent_world.world import physics
from emergent_world.world.grid import NO_PLANT


def _sim():
    sim = Simulation(Config(initial_agents=1, min_population=0, climate=False), seed=0)
    sim.world.terrain[:] = 0
    sim.world.plants[:] = NO_PLANT
    return sim, sim.agents[0], sim.config.item_id


def test_rock_on_rock_chips_a_flake_and_a_rock_cracks_a_nut():
    sim, a, item = _sim()
    for target, result in (("grey rock", "sharp flake"), ("nut", "cracked nut")):
        sim.world.plants[a.x, a.y] = item(target)
        a.hands = item("grey rock")
        for _ in range(30):
            if sim.world.plants[a.x, a.y] != item(target):
                break
            sim._act(a, Action.STRIKE)
        assert sim.world.plants[a.x, a.y] == item(result)


def test_a_soft_thing_cannot_break_a_hard_one():
    sim, a, item = _sim()
    sim.world.plants[a.x, a.y] = item("grey rock")
    a.hands = item("stick")
    for _ in range(30):
        sim._act(a, Action.STRIKE)
    assert sim.world.plants[a.x, a.y] == item("grey rock")


def test_whole_nuts_cannot_be_eaten():
    assert not Config().items[Config().item_id("nut") - 1].edible


def test_rubbing_sticks_makes_fire_and_it_burns_out_to_ash():
    sim, a, item = _sim()
    sim.world.plants[a.x, a.y] = item("stick")
    a.hands = item("stick")
    for _ in range(10):
        sim._act(a, Action.RUB)
    assert sim.world.fire[a.x, a.y] > 0
    for _ in range(20):
        physics.tick(sim)
    assert sim.world.fire[a.x, a.y] == 0
    assert sim.world.plants[a.x, a.y] == item("ash")


def test_fire_spreads_to_burnable_neighbours_and_cooks_food():
    sim, a, item = _sim()
    x, y = 30, 30
    sim.world.plants[x, y] = item("stick")
    sim.world.plants[x + 1, y] = item("stick")
    sim.world.plants[x, y + 1] = item("pale mushroom")
    physics.ignite(sim, x, y)
    for _ in range(4):
        physics.tick(sim)
    assert sim.world.fire[x + 1, y] > 0 or sim.world.plants[x + 1, y] == item("ash")
    sim.world.fire[x, y + 1] = 5          # food sitting in a fire
    for _ in range(physics.COOK_HOURS):
        physics.tick(sim)
    assert sim.world.plants[x, y + 1] == item("roasted mushroom")
    assert not sim.config.items[item("roasted mushroom") - 1].harmful


def test_standing_in_fire_burns_and_teaches_wariness():
    sim, a, item = _sim()
    sim.world.fire[a.x, a.y] = 5
    health = a.health
    sim._update_body(a)
    assert a.health < health
    assert a.memory.level(physics.FIRE_COLOR) > 0
