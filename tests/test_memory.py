import numpy as np

from emergent_world.agents.agent import Action
from emergent_world.agents.memory import GOT_SICK, NAIVE, WITNESSED, FoodMemory
from emergent_world.agents.policy import BrainPolicy
from emergent_world.config import Config
from emergent_world.sim import Simulation
from emergent_world.world.grid import FOOD, NO_PLANT, POISON

FOOD_COLOR, POISON_COLOR = Config().food_color, Config().poison_color


def test_sickness_blames_recent_meals_only():
    memory = FoodMemory()
    memory.record_meal(0, FOOD_COLOR)        # long ago
    memory.record_meal(100, POISON_COLOR)    # recent
    memory.settle_meals(100, window=48, safety=0.3)  # the old meal settles as safe
    memory.got_sick(120, window=48, strength=0.8)
    assert memory.level(POISON_COLOR) == 0.8
    assert memory.level(FOOD_COLOR) == 0.0
    assert memory.how_learned == GOT_SICK


def test_safe_meals_wear_down_wrongful_blame():
    memory = FoodMemory()
    memory.aversion[FOOD_COLOR] = 0.8
    for day in range(5):
        memory.record_meal(day * 100, FOOD_COLOR)
        memory.settle_meals(day * 100 + 49, window=48, safety=0.3)
    assert memory.level(FOOD_COLOR) < 0.2


def test_witnessing_a_relatives_poison_death():
    memory = FoodMemory()
    memory.saw_kin_eat(10, eater_id=7, color=POISON_COLOR)
    memory.saw_kin_eat(12, eater_id=8, color=FOOD_COLOR)   # someone else's meal
    memory.saw_kin_die_of_poison(40, eater_id=7, window=48, strength=0.6)
    assert memory.level(POISON_COLOR) == 0.6
    assert memory.level(FOOD_COLOR) == 0.0
    assert memory.how_learned == WITNESSED


def test_aversion_fades():
    memory = FoodMemory()
    memory.aversion[POISON_COLOR] = 1.0
    for day in range(200):
        memory.forget(day * 24, window=48, fade=0.995)
    assert 0.3 < memory.level(POISON_COLOR) < 0.4


def _family_sim():
    sim = Simulation(Config(initial_agents=1, instincts_path="instincts.npz", min_population=0), seed=0)
    sim.world.terrain[:] = 0
    sim.world.plants[:] = NO_PLANT
    parent = sim.agents[0]
    parent.x, parent.y = 20, 20
    child = sim.spawn_agent(21, 20, parent=parent)
    sibling = sim.spawn_agent(22, 20, parent=parent)
    return sim, parent, child, sibling


def test_family_ties_and_inherited_gene():
    sim, parent, child, sibling = _family_sim()
    assert child.kin == {parent.id, sibling.id}
    assert parent.kin == {child.id, sibling.id}
    assert child.memory.how_learned == NAIVE
    assert child.aversion_gain != parent.aversion_gain  # mutated, not copied


def test_child_who_watches_parent_die_of_poison_learns_to_avoid_it():
    sim, parent, child, _ = _family_sim()
    sim.world.plants[parent.x, parent.y] = POISON
    sim._act(parent, Action.EAT)          # child sees the meal
    parent.health = 1
    for _ in range(sim.config.poison_delay + 1):
        if parent.alive:
            sim._update_body(parent)
    assert not parent.alive and parent.cause_of_death == "poison"
    assert child.memory.level(POISON_COLOR) > 0
    assert child.memory.how_learned == WITNESSED


def test_aversion_holds_back_eating():
    sim, parent, child, _ = _family_sim()
    sim.world.plants[child.x, child.y] = POISON
    child.memory.aversion[POISON_COLOR] = 1.0
    penalty = BrainPolicy.eat_penalty([child], sim.world, sim.config)
    assert penalty[0] == child.aversion_gain
    sim.world.plants[child.x, child.y] = FOOD
    assert BrainPolicy.eat_penalty([child], sim.world, sim.config)[0] == 0
