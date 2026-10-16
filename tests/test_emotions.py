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
    dx, dy, loud, alarm, sound = sim._heard(b)
    assert sound == 0
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


def test_three_distinct_sounds_are_heard_as_such():
    sim, a, b = _pair()
    b.x = a.x + 4
    sim._act(a, Action.CALL_C)
    b.heard = sim._heard(b)
    assert b.heard[4] == 2
    row = emotions.social_inputs(b, [a, b], sim.config)
    assert row[-3:] == [0.0, 0.0, 1.0]


def test_signal_meaning_is_measured_against_chance():
    from collections import Counter
    import numpy as np
    from emergent_world.metrics import mutual_information, shuffled_mi
    meaningful = Counter({(0, "danger"): 50, (1, "food"): 50, (2, "water"): 50})
    noise = Counter({(s, c): 17 for s in range(3) for c in ("danger", "food", "water")})
    assert mutual_information(meaningful) > 1.5
    assert mutual_information(noise) < 0.01
    _, chance95 = shuffled_mi(meaningful, np.random.default_rng(0))
    assert mutual_information(meaningful) > chance95


def test_a_call_is_remembered_as_a_place_and_fades():
    sim, a, b = _pair()
    b.x = a.x + 6
    sim._act(a, Action.CALL_B)
    first = sim._heard(b)
    b.x = a.x - 3            # walk past where the call came from
    later = sim._heard(b)
    assert first[0] < 0 and later[0] > 0     # direction is from where they are now
    assert later[2] < first[2]               # and it fades
    for _ in range(sim.config.call_memory_hours):
        sim._heard(b)
    assert sim._heard(b) is None
