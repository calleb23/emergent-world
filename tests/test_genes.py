import numpy as np

from emergent_world.agents import genes
from emergent_world.config import Config
from emergent_world.sim import Simulation


def test_children_inherit_learning_genes_near_their_parents():
    sim = Simulation(Config(initial_agents=2, min_population=0), seed=0)
    mother, father = sim.agents
    mother.genes = {g: 0.02 for g in genes.GENES}
    father.genes = {g: 0.02 for g in genes.GENES}
    kids = [sim.spawn_agent(mother.x, mother.y, parent=mother, father=father) for _ in range(30)]
    for g in genes.GENES:
        lo, hi = genes.LIMITS[g]
        vals = [k.genes[g] for k in kids]
        assert all(lo <= v <= hi for v in vals)
        assert abs(np.mean(np.log(vals)) - np.log(min(hi, max(lo, 0.02)))) < 0.1


def test_genes_steer_learning_only_when_switched_on():
    c = Config(initial_agents=1, min_population=0)
    sim = Simulation(c, seed=0)
    a = sim.agents[0]
    a.genes["learn_rate"] = 0.05
    assert genes.value(a, c, "learn_rate") == 0.05
    c.learning_genes = False
    assert genes.value(a, c, "learn_rate") == c.learn_rate


def test_founders_start_varied():
    sim = Simulation(Config(initial_agents=20, min_population=0), seed=0)
    vals = np.log([a.genes["exploration"] for a in sim.agents])
    assert vals.std() > 0.2
