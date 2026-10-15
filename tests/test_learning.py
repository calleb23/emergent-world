import numpy as np

from emergent_world.agents.agent import Action
from emergent_world.agents.brain import INPUT_SIZE, OUTPUT_SIZE, Brain, learn
from emergent_world.config import Config
from emergent_world.instincts import load
from emergent_world.sim import Simulation
from emergent_world.world.grid import NO_PLANT

STICK = [k.look for k in Config().items].index("stick") + 1
FOOD = 1


def _sim():
    sim = Simulation(Config(initial_agents=1, min_population=0), seed=0)
    sim.world.terrain[:] = 0
    sim.world.plants[:] = NO_PLANT
    return sim, sim.agents[0]


def test_old_brains_grow_to_new_senses_and_actions():
    brain = load("instincts.npz")
    assert brain.w1.shape[0] == INPUT_SIZE and brain.w2.shape[1] == OUTPUT_SIZE
    from emergent_world.agents.brain import NEW_ACTION_BIAS
    for new in (Action.PICK_UP, Action.DROP, Action.GIVE):
        assert brain.b2[new] == NEW_ACTION_BIAS and not brain.w2[:, new].any()   # start unlikely
    assert not brain.w1[72:].any()                                               # new senses start silent


def test_pick_up_drop_and_eat_what_you_carry():
    sim, a = _sim()
    sim.world.plants[a.x, a.y] = FOOD
    sim._act(a, Action.PICK_UP)
    assert a.hands == FOOD and sim.world.plants[a.x, a.y] == NO_PLANT
    a.energy = 20
    sim._act(a, Action.EAT)
    assert a.hands == 0 and a.energy > 20


def test_sticks_dropped_in_one_spot_become_a_shelter():
    sim, a = _sim()
    for _ in range(sim.config.sticks_per_shelter):
        a.hands = STICK
        sim._act(a, Action.DROP)
    assert sim.world.shelter[a.x, a.y]
    assert sim.history and "shelter" in sim.history[-1][1]


def test_give_hands_over_to_someone_next_to_you():
    sim, a = _sim()
    b = sim.spawn_agent(a.x + 1, a.y)
    a.hands = FOOD
    sim._act(a, Action.GIVE)
    assert a.hands == 0 and b.hands == FOOD


def test_learning_raises_the_value_of_rewarded_actions():
    rng = np.random.default_rng(0)
    brain = Brain.random(rng)
    hidden = np.tanh(rng.normal(size=brain.w1.shape[1])).astype(np.float32)
    before = float(hidden @ brain.w2[:, Action.DRINK] + brain.b2[Action.DRINK])
    for _ in range(20):
        learn(brain, hidden, Action.DRINK, error=1.0, rate=0.05)
    after = float(hidden @ brain.w2[:, Action.DRINK] + brain.b2[Action.DRINK])
    assert after > before


def test_children_inherit_birth_brains_not_learning():
    sim, mother = _sim()
    mother.brain.w2 += 5.0            # a lifetime of learning
    child = sim.spawn_agent(mother.x, mother.y,
                            brain=mother.genome.mutated(sim.rng, 0.0, 0.0), parent=mother)
    assert np.allclose(child.genome.w2, mother.genome.w2)
    assert not np.allclose(child.brain.w2, mother.brain.w2)


def test_drinking_when_thirsty_feels_good():
    sim, a = _sim()
    a.water = 10
    sim._feel(a)
    a.reward = 0.0
    a.water = 60
    sim._feel(a)
    assert a.reward > 0
