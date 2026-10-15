import numpy as np

from emergent_world.agents.agent import Action
from emergent_world.agents.senses import INPUT_SIZE, TOUCH_LIQUID, UNDERFOOT
from emergent_world.agents.teacher import teacher_action
from emergent_world.config import Config
from emergent_world.instincts import accuracy, collect, load, save, train
from emergent_world.sim import Simulation


def _senses(energy=0.5, water=0.5):
    x = np.zeros(INPUT_SIZE, dtype=np.float32)
    x[UNDERFOOT:UNDERFOOT + 3] = np.array((34, 52, 30)) / 255  # grass
    x[TOUCH_LIQUID + 1] = energy
    x[TOUCH_LIQUID + 2] = water
    return x


def test_teacher_drinks_when_touching_liquid_and_thirsty():
    x = _senses(water=0.3)
    x[TOUCH_LIQUID] = 1.0
    assert teacher_action(x, np.random.default_rng(0)) == Action.DRINK


def test_teacher_tries_to_eat_any_loose_solid_including_poison():
    """Instincts are about what things are (solid), not what they look like."""
    x = _senses(energy=0.3, water=1.0)
    x[UNDERFOOT:UNDERFOOT + 3] = np.array(Config().poison_color) / 255
    assert teacher_action(x, np.random.default_rng(0)) == Action.EAT


def test_cloned_brain_learns_and_round_trips(tmp_path):
    xs, ys = collect(3000, seed=0)
    brain = train(xs, ys, epochs=5)
    assert accuracy(brain, xs, ys) > 0.3
    path = tmp_path / "instincts.npz"
    save(brain, path)
    sim = Simulation(Config(initial_agents=3, instincts_path=str(path)), seed=0)
    assert sim.agents[0].brain.w1.shape == brain.w1.shape
    assert not np.array_equal(sim.agents[0].brain.w1, brain.w1)  # mutated copies
