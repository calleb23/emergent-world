from emergent_world.agents import emotions
from emergent_world.agents.agent import Action
from emergent_world.config import Config
from emergent_world.sim import Simulation
from emergent_world.world.grid import NO_PLANT


def _pair():
    sim = Simulation(Config(initial_agents=2, min_population=0, climate=False), seed=0)
    sim.world.terrain[:] = 0
    sim.world.plants[:] = NO_PLANT
    a, b = sim.agents
    a.x, a.y, b.x, b.y = 30, 30, 31, 30
    return sim, a, b


def test_children_inherit_temperament():
    sim, a, b = _pair()
    a.traits = {t: 1.0 for t in emotions.TRAITS}
    b.traits = {t: 1.0 for t in emotions.TRAITS}
    child = sim.spawn_agent(a.x, a.y, parent=a, father=b)
    assert all(v > 0.7 for v in child.traits.values())


def test_hitting_hurts_frightens_and_breeds_a_grudge():
    sim, a, b = _pair()
    before = b.health
    sim._act(a, Action.HIT)
    assert b.health < before and b.fear > 0 and b.anger > 0
    assert b.grudges[a.id] > 0


def test_taking_from_someone_angers_them():
    sim, a, b = _pair()
    b.hands = sim.config.item_id("apple")
    b.asleep = True   # can't hold on while asleep
    sim._act(a, Action.TAKE)
    assert a.hands == sim.config.item_id("apple") and not b.hands
    assert b.grudges[a.id] > 0


def test_comfort_soothes_and_softens_grudges():
    sim, a, b = _pair()
    b.fear, b.loneliness, b.grudges[a.id] = 0.8, 0.8, 0.5
    sim._act(a, Action.COMFORT)
    assert b.fear < 0.8 and b.loneliness < 0.8 and b.grudges[a.id] < 0.5
    assert b.reward > 0


def test_calls_are_heard_with_direction_and_alarm():
    sim, a, b = _pair()
    b.x = a.x + 6
    a.fear = 0.9
    sim._act(a, Action.CALL)
    dx, dy, loud, alarm = b.heard_next
    assert dx < 0 and loud > 0 and alarm == 0.9


def test_being_alone_gets_lonely_and_company_eases_it():
    sim, a, b = _pair()
    b.x = a.x + 20
    for _ in range(50):
        emotions.update(sim, a)
    lonely = a.loneliness
    assert lonely > 0
    b.x = a.x + 1
    a.known[b.id] = 0.5
    emotions.update(sim, a)
    assert a.loneliness < lonely


def test_people_are_reluctant_to_hit_family():
    sim, a, b = _pair()
    from emergent_world.agents.policy import BrainPolicy
    stranger = BrainPolicy.social_penalty([a], sim.by_id, sim.config)[0, Action.HIT]
    a.kin.add(b.id)
    family = BrainPolicy.social_penalty([a], sim.by_id, sim.config)[0, Action.HIT]
    assert family > stranger > 0
