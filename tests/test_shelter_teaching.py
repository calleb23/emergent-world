import numpy as np

from emergent_world.agents.agent import Action
from emergent_world.agents.policy import BrainPolicy
from emergent_world.agents.senses import AT_SHELTER, EXPOSED, LIGHT
from emergent_world.config import Config
from emergent_world.sim import Simulation
from emergent_world.world.grid import NO_PLANT


def _sim():
    sim = Simulation(Config(initial_agents=2, min_population=0), seed=0)
    sim.world.terrain[:] = 0
    sim.world.plants[:] = NO_PLANT
    a, b = sim.agents
    a.x, a.y = 30, 30
    a.age = b.age = sim.config.maturity_age + 10
    return sim, a, b, sim.config.item_id


def test_out_in_the_weather_people_head_for_a_shelter_they_know():
    sim, a, b, item = _sim()
    a.memory.shelter_at = (36, 30)
    inputs = np.zeros((1, 200), dtype=np.float32)
    inputs[0, EXPOSED] = 1.0
    inputs[0, LIGHT] = 1.0
    pull = BrainPolicy.shelter_pull([a], inputs, sim.config)
    assert pull[0, Action.EAST] > 0 and pull[0, Action.WEST] == 0
    inputs[0, AT_SHELTER] = 1.0
    assert not BrainPolicy.shelter_pull([a], inputs, sim.config).any()


def test_knowing_shelter_and_the_cold_makes_people_gather_and_pile_wood():
    sim, a, b, item = _sim()
    sim.world.plants[a.x, a.y] = item("stick")
    pick, drop, _ = BrainPolicy.build_urge([a], sim.world, sim.config)
    assert pick[0] == 0                         # never seen a shelter, never cold: no urge
    a.memory.shelter_at = (40, 40)
    a.cold_memory = 0.8
    pick, drop, _ = BrainPolicy.build_urge([a], sim.world, sim.config)
    assert pick[0] > 0
    a.hands, sim.world.plants[a.x, a.y] = item("stick"), NO_PLANT
    sim.world.piles[a.x, a.y] = 2
    pick, drop, _ = BrainPolicy.build_urge([a], sim.world, sim.config)
    assert drop[0] > 0


def test_seeing_a_shelter_is_remembered():
    from emergent_world import behaviour
    sim, a, b, item = _sim()
    sim.climate.tick_count = 12
    sim.world.shelter[a.x + 3, a.y] = True
    behaviour.after_action(sim, a)
    assert a.memory.shelter_at == (a.x + 3, a.y)


def test_grown_ups_show_younger_family_what_works():
    sim, a, b, item = _sim()
    b.age = 10
    b.x, b.y = a.x + 2, a.y
    a.kin.add(b.id)
    sim.policy.choose_actions(sim.agents, sim.world, sim.config, None, sim.by_id)
    sim.world.plants[a.x, a.y] = item("stick")
    sim._act(a, Action.PICK_UP)
    assert Action.PICK_UP in b.copied and sim.counts["taught"] == 1


def test_children_near_a_parent_learn_the_places_it_knows():
    from emergent_world import behaviour
    sim, a, b, item = _sim()
    child = sim.spawn_agent(a.x + 1, a.y, parent=a)
    a.memory.water_at = (5, 5)
    behaviour.after_action(sim, child)
    assert child.memory.water_at == (5, 5)


def test_a_rock_overhang_keeps_off_the_weather():
    from emergent_world import behaviour
    sim, a, b, item = _sim()
    sim.climate.weather = "rain"
    assert behaviour.exposed(sim, a)
    sim.world.plants[a.x + 1, a.y] = item("rock overhang")
    assert not behaviour.exposed(sim, a)


def test_needy_listeners_go_to_see_what_a_call_was_about():
    sim, a, b, item = _sim()
    b.x, b.y = a.x + 6, a.y
    a.energy = 0.2 * sim.config.max_energy
    sim._act(b, Action.CALL_B)
    a.heard = sim._heard(a)
    pull = BrainPolicy.place_pull([a], np.zeros((1, 200), dtype=np.float32), sim.config, sim.by_id)
    assert pull[0, Action.EAST] > 0


def test_a_caller_is_glad_when_someone_who_came_finds_food():
    sim, a, b, item = _sim()
    b.x, b.y = a.x + 1, a.y
    sim._act(a, Action.CALL)
    b.heard = sim._heard(b)          # within a tile: they've arrived
    assert b.answered[0] == a.id
    before = a.reward
    sim._consume(b, sim.config.item(item("apple")))
    assert a.reward > before and sim.counts["call_helped"] == 1
