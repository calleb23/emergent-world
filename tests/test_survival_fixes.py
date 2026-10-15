from emergent_world.config import Config
from emergent_world.sim import Simulation
from emergent_world.agents.policy import BrainPolicy
from emergent_world import behaviour


def _sim(**kw):
    sim = Simulation(Config(initial_agents=2, min_population=0, **kw), seed=0)
    return sim, sim.agents[0]


def test_too_parched_to_fall_asleep_unless_exhausted():
    sim, a = _sim()
    sim.climate.tick_count = 0   # midnight
    a.asleep, a.fatigue, a.water = False, 0.7, 5.0
    sim._update_sleep(a)
    assert not a.asleep
    a.fatigue = 1.0
    sim._update_sleep(a)
    assert a.asleep   # collapses anyway


def test_people_remember_water_they_have_only_seen():
    sim, a = _sim()
    w = sim.world
    near = [(x, y) for x in range(w.width) for y in range(w.height)
            if w.is_walkable(x, y) and 1 <= w.shore_distance[x, y] <= 2]
    a.x, a.y = near[0]
    a.memory.water_at = None
    sim.climate.tick_count = 12   # noon: full sight
    behaviour.after_action(sim, a)
    sx, sy = a.memory.water_at
    assert w.next_to_liquid(sx, sy)


def test_orphans_keep_close_to_kin():
    sim, a = _sim()
    child = sim.spawn_agent(a.x, a.y, parent=a)
    aunt = sim.agents[1]
    aunt.age = sim.config.maturity_age + 1
    child.kin.add(aunt.id)
    a.alive = False
    assert BrainPolicy._guardian(child, sim.by_id, sim.config) is aunt
