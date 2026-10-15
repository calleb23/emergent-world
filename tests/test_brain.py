import numpy as np

from emergent_world.agents.agent import Action
from emergent_world.agents.brain import Brain, think
from emergent_world.agents.senses import (INPUT_SIZE, RAY_SIZE, TOUCH_LIQUID, UNDERFOOT,
                                         build_occupancy, sense)
from emergent_world.config import Config
from emergent_world.sim import Simulation
from emergent_world.world.grid import FOOD, NO_PLANT, WATER


def _empty_world_sim(**overrides):
    sim = Simulation(Config(initial_agents=1, **overrides), seed=0)
    sim.world.terrain[:] = 0
    sim.world.plants[:] = NO_PLANT
    agent = sim.agents[0]
    agent.x, agent.y = 20, 20
    return sim, agent


def test_senses_have_expected_size():
    sim, agent = _empty_world_sim()
    inputs = sense(agent, sim.world, build_occupancy(sim.world, sim.living), sim.config)
    assert inputs.shape == (INPUT_SIZE,)


def test_east_ray_sees_water_with_closeness():
    sim, agent = _empty_world_sim()
    sim.world.terrain[23, 20] = WATER  # 3 tiles east
    inputs = sense(agent, sim.world, build_occupancy(sim.world, sim.living), sim.config)
    east = 2 * RAY_SIZE  # third ray in RAY_DIRECTIONS
    assert inputs[east + 3] == 1.0 - 2 / sim.config.vision_range
    assert inputs[east + 2] > inputs[east]  # blue is stronger than red


def test_plants_do_not_hide_water():
    sim, agent = _empty_world_sim()
    sim.world.plants[21, 20] = FOOD    # a plant right next to the agent, east
    sim.world.terrain[24, 20] = WATER  # a pond behind it
    inputs = sense(agent, sim.world, build_occupancy(sim.world, sim.living), sim.config)
    east = 2 * RAY_SIZE
    assert inputs[east + 3] > 0      # ground layer still sees the water
    assert inputs[east + 7] == 1.0   # object layer sees the adjacent plant


def test_underfoot_and_touch_senses():
    sim, agent = _empty_world_sim()
    sim.world.plants[20, 20] = FOOD
    sim.world.terrain[20, 21] = WATER
    inputs = sense(agent, sim.world, build_occupancy(sim.world, sim.living), sim.config)
    underfoot = inputs[UNDERFOOT:UNDERFOOT + 3]
    assert np.allclose(underfoot, np.array(sim.config.food_color) / 255)
    assert inputs[TOUCH_LIQUID] == 1.0


def test_think_returns_one_valid_action_per_brain():
    rng = np.random.default_rng(0)
    brains = [Brain.random(rng) for _ in range(5)]
    actions = think(brains, rng.random((5, INPUT_SIZE)).astype(np.float32), rng)
    assert actions.shape == (5,)
    assert all(0 <= a < len(Action) for a in actions)


def test_mutation_changes_weights_but_not_shape():
    rng = np.random.default_rng(0)
    parent = Brain.random(rng)
    child = parent.mutated(rng, 0.05)
    assert child.w1.shape == parent.w1.shape
    assert not np.array_equal(child.w1, parent.w1)


def test_healthy_adult_reproduces_with_mutated_brain():
    sim, agent = _empty_world_sim()
    agent.age = sim.config.maturity_age
    agent.energy = sim.config.max_energy
    agent.water = sim.config.max_water
    sim._maybe_reproduce(agent)
    child = sim.agents[-1]
    assert child.parent_id == agent.id
    assert child.generation == 1
    assert not np.array_equal(child.brain.w1, agent.brain.w1)
    assert agent.reproduce_cooldown == sim.config.reproduce_cooldown


def test_thirsty_adult_does_not_reproduce():
    sim, agent = _empty_world_sim()
    agent.age = sim.config.maturity_age
    agent.energy = sim.config.max_energy
    agent.water = sim.config.reproduce_water - 1
    sim._maybe_reproduce(agent)
    assert len(sim.agents) == 1


def test_garden_difficulty_ramps_to_full():
    sim = Simulation(Config(garden_start=0.4, garden_ticks=100), seed=0)
    assert sim.difficulty == 0.4
    sim.tick_count = 50
    assert abs(sim.difficulty - 0.7) < 1e-9
    sim.tick_count = 500
    assert sim.difficulty == 1.0


def test_bootstrap_keeps_minimum_population():
    sim = Simulation(Config(initial_agents=0, min_population=10), seed=0)
    sim.tick()
    assert len(sim.living) == 10


def test_batched_senses_match_reference():
    from emergent_world.agents.senses import sense_all
    sim = Simulation(Config(initial_agents=60), seed=5)
    for _ in range(50):
        sim.tick()
    agents = sim.living
    agents[0].sicknesses.append(type("S", (), {"delay": 0})())  # one agent feeling pain
    occupied = build_occupancy(sim.world, agents)
    reference = np.stack([sense(a, sim.world, occupied, sim.config) for a in agents])
    assert np.allclose(sense_all(agents, sim.world, sim.config), reference)
