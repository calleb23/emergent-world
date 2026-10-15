from emergent_world.agents.agent import Action
from emergent_world.config import Config, days
from emergent_world.sim import Simulation


def _sim():
    sim = Simulation(Config(initial_agents=1, min_population=0), seed=0)
    agent = sim.agents[0]
    agent.lifespan = days(1000)
    return sim, agent


def test_spare_energy_becomes_fat_and_fat_feeds_lean_times():
    sim, agent = _sim()
    agent.energy = sim.config.max_energy
    for _ in range(20):
        sim._update_fat(agent)
    assert agent.fat > 0
    stored = agent.fat
    agent.energy = 10
    sim._update_fat(agent)
    assert agent.fat < stored and agent.energy > 10


def test_old_agents_heal_slower_and_stumble():
    sim, agent = _sim()
    agent.age = int(agent.lifespan * 0.95)
    start = (agent.x, agent.y)
    stuck = 0
    for _ in range(200):
        agent.x, agent.y = start
        sim._act(agent, Action.EAST if sim.world.is_walkable(start[0] + 1, start[1]) else Action.WEST)
        stuck += (agent.x, agent.y) == start
    assert stuck > 40   # a frail agent's steps often don't happen


def test_distant_relatives_hear_a_death_and_grieve():
    sim, parent = _sim()
    child = sim.spawn_agent(parent.x, parent.y, parent=parent)
    child.x = parent.x + 12 if parent.x + 12 < sim.world.width else parent.x - 12   # out of sight, within earshot
    sim._kill(parent, "starvation")
    assert any("cry out" in text for _, text in child.events)
    assert child.grief > 0
    assert child.grief <= sim.config.grief_hours * 2


def test_history_records_firsts_once():
    sim, agent = _sim()
    sim.chronicle("first", once="x")
    sim.chronicle("again", once="x")
    assert [t for _, t in sim.history].count("first") == 1
    assert "again" not in [t for _, t in sim.history]
