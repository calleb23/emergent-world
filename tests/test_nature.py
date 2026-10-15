import numpy as np

from emergent_world.agents.agent import Action
from emergent_world.config import Config
from emergent_world.sim import Simulation
from emergent_world.world import physics
from emergent_world.world.grid import NO_PLANT


def _sim(climate=False):
    sim = Simulation(Config(initial_agents=1, min_population=0, climate=climate), seed=0)
    sim.world.terrain[:] = 0
    sim.world.plants[:] = NO_PLANT
    a = sim.agents[0]
    a.x, a.y = 30, 30
    return sim, a, sim.config.item_id


def test_everything_named_in_nature_exists():
    c = Config()
    looks = {k.look for k in c.items}
    for k in c.items:
        assert set(k.eats) <= looks and (not k.rots_into or k.rots_into in looks)


def test_wolves_hunt_cugs_beside_them():
    sim, a, item = _sim()
    sim.world.plants[10, 10] = item("wolf")
    eaten = False
    for _ in range(300):
        for dx, dy in physics.NEIGHBOURS:
            if sim.world.plants[10 + dx, 10 + dy] == NO_PLANT:
                sim.world.plants[10 + dx, 10 + dy] = item("cug")
        before = int((sim.world.plants == item("cug")).sum())
        sim.world.move_critters(np.zeros(sim.world.plants.shape, dtype=bool))
        if (sim.world.plants == item("cug")).sum() < before:
            eaten = True
            break
        sim.world.plants[sim.world.plants == item("wolf")] = NO_PLANT
        sim.world.plants[10, 10] = item("wolf")
    assert eaten


def test_wolves_bite_people_next_to_them():
    sim, a, item = _sim()
    sim.world.plants[a.x + 1, a.y] = item("wolf")
    before = a.health
    for _ in range(40):
        physics.nature(sim)
    assert a.health < before
    assert a.memory.level(sim.config.items[item("wolf") - 1].color) > 0


def test_a_pelt_keeps_off_a_cold_night_but_not_the_rain():
    sim, a, item = _sim(climate=True)
    from emergent_world import behaviour
    c = sim.climate
    c.weather = "clear"
    c.tick_count = 3 * c.days_per_season * c.ticks_per_day   # a winter midnight
    assert behaviour.exposed(sim, a)
    a.hands = item("wolf pelt")
    assert not behaviour.exposed(sim, a)
    sim.climate.weather = "rain"
    assert behaviour.exposed(sim, a)


def test_a_spear_at_the_water_takes_fish():
    sim, a, item = _sim()
    sim.world.terrain[a.x - 1, a.y] = 1
    caught = False
    for _ in range(60):
        a.hands = item("spear")
        sim.world.plants[a.x, a.y] = NO_PLANT
        sim._act(a, Action.STRIKE)
        if sim.world.plants[a.x, a.y] == item("fish"):
            caught = True
            break
    assert caught and sim.world.fish < physics.FISH_STOCK


def test_meat_rots_and_apple_cores_take_root():
    sim, a, item = _sim()
    sim.world._wilt[item("cug meat")] = 1.0
    sim.world.plants[5, 5] = item("cug meat")
    sim.world.tick(growth=0.0)
    assert sim.world.plants[5, 5] == item("rotten meat")
    sim.world.plants[7, 7] = item("rotten apple")
    for _ in range(20 * 24):
        physics.grow(sim)
    assert sim.world.plants[7, 7] == item("sapling")


def test_rain_brings_mushrooms_and_fills_pots():
    sim, a, item = _sim(climate=True)
    sim.climate.weather = "rain"
    sim.world.wet[:] = 1.0
    sim.world.plants[3, 3] = item("clay pot")
    a.hands = item("clay pot")
    for _ in range(60):
        physics.nature(sim)
    assert (sim.world.plants == item("puffball")).any()
    assert sim.world.plants[3, 3] == item("pot of water") and a.hands == item("pot of water")


def test_berry_bushes_fruit_in_season_only():
    sim, a, item = _sim(climate=True)
    sim.world.plants[20, 20] = item("berry bush")
    c = sim.climate
    c.weather = "clear"
    c.tick_count = 3 * c.days_per_season * c.ticks_per_day   # winter
    assert c.season == "winter"
    for _ in range(2000):
        physics.shed(sim)
    assert not (sim.world.plants == item("red berry")).any()
