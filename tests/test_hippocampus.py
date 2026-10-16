import numpy as np

from emergent_world import behaviour
from emergent_world.agents.agent import Action
from emergent_world.agents.hippocampus import CAPACITY, Hippocampus, memory_inputs
from emergent_world.agents.senses import INPUT_SIZE, sense_all
from emergent_world.config import Config
from emergent_world.sim import Simulation
from emergent_world.world.grid import NO_PLANT


def _sim():
    sim = Simulation(Config(initial_agents=2, min_population=0), seed=0)
    sim.world.terrain[:] = 0
    sim.world.plants[:] = NO_PLANT
    a, b = sim.agents
    a.x, a.y = 30, 30
    return sim, a, b


def test_episodes_merge_fade_and_the_weakest_are_forgotten():
    h = Hippocampus()
    h.encode(0, 5, 5, "water", 0.5)
    h.encode(10, 5, 6, "water", 0.9)            # same spot: refreshed, not added
    assert len(h.episodes) == 1 and h.episodes[0].value == 0.9
    assert h.strength(h.episodes[0], 10 + 24 * 120) < 0.5   # half-life of water is 120 days
    for k in range(CAPACITY + 10):
        h.encode(0, k * 3, 0, "food", 0.01 * (k % 7 + 1))
    assert len(h.episodes) <= CAPACITY


def test_recall_prefers_strong_recent_near_memories():
    h = Hippocampus()
    h.encode(0, 50, 50, "water", 1.0)
    h.encode(0, 32, 30, "water", 0.6)
    x, y, s = h.recall("water", 30, 30, 0)
    assert (x, y) == (32, 30)                    # nearer wins over a slightly stronger far one


def test_the_brain_senses_what_is_recalled():
    sim, a, b = _sim()
    a.hippo.encode(sim.tick_count, a.x + 10, a.y, "water", 1.0)
    a.hippo.refresh(a.x, a.y, sim.tick_count)
    row = memory_inputs(a)
    assert row[0] > 0 and row[1] == 0 and row[2] > 0
    assert sense_all([a, b], sim.world, sim.config).shape[1] == INPUT_SIZE


def test_drinking_when_parched_is_remembered_and_recalled_as_the_place_for_water():
    sim, a, b = _sim()
    sim.world.terrain[a.x - 1, a.y] = 1
    a.water = 10
    sim._act(a, Action.DRINK)
    assert any(e.kind == "water" for e in a.hippo.episodes)


def test_seeing_someone_sheltered_while_exposed_makes_people_want_shelter():
    sim, a, b = _sim()
    sim.climate.weather = "storm"
    sim.climate.tick_count = 12
    a.asleep = False
    b.x, b.y = a.x + 3, a.y
    sim.world.plants[b.x + 1, b.y] = sim.config.item_id("rock overhang")
    behaviour.remember_weather(sim, a, out_in_it=True)
    assert a.shelter_want > 0
    assert any(e.kind == "shelter" and e.who == b.id for e in a.hippo.episodes)


def test_watching_someone_pile_wood_is_remembered_as_a_place_to_build():
    sim, a, b = _sim()
    b.x, b.y = a.x + 3, a.y
    a.hands = sim.config.item_id("stick")
    sim._act(a, Action.DROP)
    assert any(e.kind == "build" and e.who == a.id for e in b.hippo.episodes)


def test_sleep_replays_experience_to_the_brain():
    sim, a, b = _sim()
    rng = np.random.default_rng(0)
    h = np.ones(16, dtype=np.float32)
    a.hippo.replay.append((h, int(Action.EAT), 1.0, np.zeros(16, dtype=np.float32)))
    before = a.brain.w2[:, Action.EAT].copy()
    from emergent_world.agents.hippocampus import sleep_replay
    sleep_replay(a, rng, 0.95, 0.05, 4)
    assert not np.allclose(before, a.brain.w2[:, Action.EAT])
