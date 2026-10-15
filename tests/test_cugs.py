import numpy as np

from emergent_world.agents.agent import Action
from emergent_world.config import Config
from emergent_world.sim import Simulation
from emergent_world.world.grid import NO_PLANT

CUG = len(Config().items)   # the cug is the last item in the table


def _empty_sim():
    sim = Simulation(Config(initial_agents=1, min_population=0), seed=0)
    sim.world.terrain[:] = 0
    sim.world.plants[:] = NO_PLANT
    return sim, sim.agents[0]


def test_cug_is_a_critter():
    cug = Config().items[CUG - 1]
    assert cug.look == "cug" and cug.edible and not cug.harmful
    assert cug.wanders > 0 and cug.flees > 0 and cug.breeds > 0


def test_cugs_bolt_when_someone_is_next_to_them():
    sim, agent = _empty_sim()
    occupied = np.zeros_like(sim.world.plants, dtype=bool)
    occupied[20, 20] = True
    moved = 0
    for _ in range(50):
        sim.world.plants[:] = NO_PLANT
        sim.world.plants[21, 20] = CUG
        sim.world.move_critters(occupied, growth=0)
        moved += sim.world.plants[21, 20] != CUG
    assert moved > 25          # flees about 70% of the time, plus wandering


def test_cugs_breed_up_to_their_limit():
    sim, agent = _empty_sim()
    sim.world.plants[10, 10] = CUG
    occupied = np.zeros_like(sim.world.plants, dtype=bool)
    for _ in range(5000):
        sim.world.move_critters(occupied)
    count = int((sim.world.plants == CUG).sum())
    assert 20 < count <= Config().items[CUG - 1].max_count


def test_catching_a_cug_feeds_and_is_remembered():
    sim, agent = _empty_sim()
    agent.energy = 20
    sim.world.plants[agent.x, agent.y] = CUG
    sim._act(agent, Action.EAT)
    assert agent.energy == 20 + Config().items[CUG - 1].energy
    assert agent.events[-1][1] == "Caught and ate a cug for the first time"
