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


def test_starving_overrides_wariness_but_not_known_non_food():
    sim, a = _sim()
    c = sim.config
    plant = c.item_id("green plant")
    sim.world.plants[a.x, a.y] = plant
    a.memory.aversion[c.item(plant).color] = 0.5
    a.energy = 0.1 * c.max_energy
    eat, _ = BrainPolicy.trust_pull([a], sim.world, __import__("numpy").zeros((1, 200)), c)
    assert eat[0] > 0
    rock = c.item_id("grey rock")
    sim.world.plants[a.x, a.y] = rock
    a.memory.useless.add(c.item(rock).color)
    eat, _ = BrainPolicy.trust_pull([a], sim.world, __import__("numpy").zeros((1, 200)), c)
    assert eat[0] == 0


def test_watching_family_eat_a_food_eases_wariness_of_it():
    sim, a = _sim()
    b = sim.agents[1]
    b.x, b.y = a.x + 1, a.y
    a.kin.add(b.id)
    b.kin.add(a.id)
    kind = sim.config.item(sim.config.item_id("green plant"))
    a.memory.aversion[kind.color] = 0.5
    sim._consume(b, kind)
    assert a.memory.aversion[kind.color] < 0.5


def test_thirst_urges_a_drink_beside_water_and_draws_toward_water_in_sight():
    import numpy as np
    from emergent_world.agents.agent import Action
    from emergent_world.agents.senses import TOUCH_LIQUID, RAY_SIZE, sense_all
    sim, a = _sim()
    c = sim.config
    a.water = 0.05 * c.max_water
    inputs = np.zeros((1, 200), dtype=np.float32)
    inputs[0, TOUCH_LIQUID] = 1.0
    pol = sim.policy
    # The urge alone: beside water and parched, drinking is pulled up hard.
    beside = inputs[:, TOUCH_LIQUID] > 0
    urge = c.thirst_urge * beside * np.clip((1 - a.water / c.max_water - 0.3) / 0.7, 0, 1)
    assert urge[0] > 4
    # Water seen along the east ray (index 2) pulls a parched person east.
    rays = np.zeros((1, 200), dtype=np.float32)
    rays[0, 2 * RAY_SIZE + 3] = 0.8
    pull = BrainPolicy.place_pull([a], rays, c, sim.by_id)
    assert pull[0, Action.EAST] > 0 and pull[0, Action.WEST] == 0
