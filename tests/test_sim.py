from emergent_world.agents.agent import Action
from emergent_world.config import Config
from emergent_world.sim import Simulation
from emergent_world.world.grid import FOOD, NO_PLANT, POISON


def test_same_seed_same_run():
    a = Simulation(seed=42)
    b = Simulation(seed=42)
    a.run(500)
    b.run(500)
    assert a.stats.deaths == b.stats.deaths
    assert (a.world.plants == b.world.plants).all()


def test_different_seeds_differ():
    a = Simulation(seed=1)
    b = Simulation(seed=2)
    assert not (a.world.terrain == b.world.terrain).all()


def test_poison_damage_is_delayed():
    config = Config(initial_agents=1)
    sim = Simulation(config, seed=0)
    agent = sim.agents[0]
    sim.world.plants[agent.x, agent.y] = POISON
    sim._act(agent, Action.EAT)
    assert sim.world.plants[agent.x, agent.y] == NO_PLANT

    start = agent.health
    for _ in range(config.poison_delay):
        sim._update_body(agent)
    assert agent.health >= start  # no damage during the delay

    sim._update_body(agent)
    assert agent.health < start
    assert agent.last_damage == "poison"


def test_food_restores_energy():
    config = Config(initial_agents=1)
    sim = Simulation(config, seed=0)
    agent = sim.agents[0]
    agent.energy = 10
    sim.world.plants[agent.x, agent.y] = FOOD
    sim._act(agent, Action.EAT)
    assert agent.energy == 10 + config.food_energy


def test_starving_agent_dies_of_starvation():
    config = Config(initial_agents=1)
    sim = Simulation(config, seed=0)
    agent = sim.agents[0]
    agent.energy = 0
    agent.water = config.max_water * 10  # keep thirst out of it
    agent.lifespan = 10_000
    while agent.alive:
        sim._update_body(agent)
    assert agent.cause_of_death == "starvation"


def test_old_age():
    config = Config(initial_agents=1)
    sim = Simulation(config, seed=0)
    agent = sim.agents[0]
    agent.lifespan = 1
    sim._update_body(agent)
    assert not agent.alive
    assert agent.cause_of_death == "old_age"


def test_agents_never_walk_on_water():
    sim = Simulation(seed=3)
    for _ in range(300):
        sim.tick()
        for agent in sim.living:
            assert sim.world.is_walkable(agent.x, agent.y)
