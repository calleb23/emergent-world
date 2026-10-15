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
    for _ in range(sim.config.items[1].toxin_delay + 1):
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


def test_life_story_records_birth_sickness_and_witnessed_death():
    sim, parent, child, _ = _family_sim()
    assert child.events[-1][1] == f"Born to {parent.name} (#{parent.id}), of the {parent.line} line"
    assert child.line == parent.line
    assert any("Had a child" in text for _, text in parent.events)
    sim.world.plants[parent.x, parent.y] = POISON
    sim._act(parent, Action.EAT)
    assert parent.events[-1][1] == "Ate a yellow-green plant for the first time"
    parent.health = 1
    while parent.alive:
        sim._update_body(parent)
    assert parent.events[-1][1].startswith("Died of poison")
    texts = [text for _, text in child.events]
    assert (f"Saw their parent {parent.name} (#{parent.id}) die (poison); "
            "now wary of yellow-green plant") in texts
    assert texts[-1] == f"Grieving for {parent.name}"
    assert child.grief > 0


def test_following_passes_to_a_child_on_death():
    sim, parent, child, sibling = _family_sim()
    told = []
    sim.on_event = lambda agent, tick, text: told.append((agent.id, text))
    sim.follow(parent)
    child.age, sibling.age = 50, 10
    sim._kill(parent, "old_age")
    assert sim.followed_id == child.id   # the oldest living child
    assert told[0] == (parent.id, f"Died of old age, aged {parent.age // 24} days")
    assert told[-1][0] == child.id and "child of" in told[-1][1]


def test_wariness_steers_away_from_foods_in_sight():
    from emergent_world.agents.senses import sense_all
    sim, parent, child, sibling = _family_sim()
    for other in (parent, sibling):
        other.x, other.y = 5, 5          # out of the way
    sim.world.plants[child.x + 3, child.y] = POISON   # east, in sight
    sim.world.plants[child.x, child.y - 2] = FOOD     # north, in sight
    child.memory.aversion[POISON_COLOR] = 1.0
    inputs = sense_all([child], sim.world, sim.config)
    north, south, east, west = BrainPolicy.steer_penalty([child], inputs, sim.config)[0]
    assert east > 0                        # held back from the poison
    assert north == south == west == 0     # nothing to be wary of elsewhere


def test_hunger_overrides_wariness():
    sim, parent, child, _ = _family_sim()
    child.energy = sim.config.max_energy
    fed = BrainPolicy.desperation([child], sim.config)[0]
    child.energy = 0
    starving = BrainPolicy.desperation([child], sim.config)[0]
    assert fed == 1.0 and abs(starving - 0.1) < 1e-6
