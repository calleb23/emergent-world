import numpy as np

from emergent_world.agents.agent import Action
from emergent_world.agents.brain import Brain, imitate
from emergent_world.agents.senses import INPUT_SIZE
from emergent_world.config import Config
from emergent_world.sim import Simulation


def _probs(brain, x):
    h = np.tanh(x @ brain.w1 + brain.b1)
    z = h @ brain.w2 + brain.b2
    p = np.exp(z - z.max())
    return p / p.sum()


def test_imitating_makes_the_seen_action_likelier_and_hurt_makes_it_rarer():
    rng = np.random.default_rng(0)
    brain = Brain.random(rng)
    x = rng.random(INPUT_SIZE).astype(np.float32)
    before = _probs(brain, x)[Action.STRIKE]
    imitate(brain, x, Action.STRIKE, 0.5)
    assert _probs(brain, x)[Action.STRIKE] > before
    mid = _probs(brain, x)[Action.STRIKE]
    imitate(brain, x, Action.STRIKE, -0.5)
    assert _probs(brain, x)[Action.STRIKE] < mid


def test_an_onlooker_leans_toward_what_a_relative_does():
    sim = Simulation(Config(initial_agents=2, min_population=0, climate=False), seed=0)
    model, child = sim.agents
    model.age = sim.config.maturity_age + 10
    child.x, child.y = model.x + 1, model.y
    child.kin.add(model.id)
    seen = np.random.default_rng(1).random(INPUT_SIZE).astype(np.float32)
    model.last_seen, model.last_choice, model.reward = seen, (None, int(Action.STRIKE), 0.0), 0.0
    before = _probs(child.brain, seen)[Action.STRIKE]
    sim.policy._imitate([child], sim.by_id, sim.config)
    assert _probs(child.brain, seen)[Action.STRIKE] > before
    assert Action.STRIKE in child.copied


def test_newcomers_carry_a_living_brain():
    c = Config(initial_agents=3, min_population=0, climate=False, newcomer_every_days=1 / 24)
    sim = Simulation(c, seed=0)
    for a in sim.agents:
        a.age = c.maturity_age + 1
    old = {a.id: a.brain for a in sim.agents}
    sim._newcomers()
    newcomer = sim.agents[-1]
    assert newcomer.id not in old
    closest = min(float(np.abs(newcomer.brain.w2 - b.w2).sum()) for b in old.values())
    assert closest < 1.0


def test_imitation_still_works_with_lifetime_learning_off():
    c = Config(initial_agents=2, min_population=0, climate=False, learning=False)
    sim = Simulation(c, seed=0)
    for _ in range(3):
        sim.tick()
    assert all(a.last_choice is not None for a in sim.agents)
