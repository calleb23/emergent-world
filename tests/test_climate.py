import numpy as np

from emergent_world.agents.agent import Action
from emergent_world.agents.senses import RAY_SIZE, sense_all
from emergent_world.config import Config, days
from emergent_world.sim import Simulation
from emergent_world.world.climate import Climate
from emergent_world.world.grid import NO_PLANT, WATER


def test_light_follows_the_day():
    climate = Climate(np.random.default_rng(0))
    light = []
    for _ in range(24):
        light.append(climate.light)
        climate.tick()
    assert min(light) == 0.15 and max(light) == 1.0
    assert light[12] == 1.0          # noon
    assert light[2] == 0.15          # 2am


def test_seasons_turn_and_winter_snows():
    climate = Climate(np.random.default_rng(1))
    seasons, weather = set(), {}
    for _ in range(days(365)):
        climate.tick()
        seasons.add(climate.season)
        weather.setdefault(climate.season, set()).add(climate.weather)
    assert seasons == {"spring", "summer", "autumn", "winter"}
    assert "snow" in weather["winter"]
    assert "snow" not in weather["summer"]


def test_night_and_fog_shorten_sight():
    sim = Simulation(Config(initial_agents=1), seed=0)
    sim.world.terrain[:] = 0
    sim.world.plants[:] = NO_PLANT
    agent = sim.agents[0]
    agent.x, agent.y = 20, 20
    sim.world.terrain[26, 20] = WATER     # 6 tiles east
    east = 2 * RAY_SIZE
    assert sense_all([agent], sim.world, sim.config, reach=8)[0, east + 3] > 0
    assert sense_all([agent], sim.world, sim.config, reach=3)[0, east + 3] == 0


def test_tired_agents_sleep_at_night_and_wake_rested():
    sim = Simulation(Config(initial_agents=1, min_population=0), seed=0)
    agent = sim.agents[0]
    agent.lifespan = days(1000)
    asleep_hours = []
    for hour in range(days(3)):
        agent.energy = agent.water = 100  # keep needs out of it
        sim.tick()
        if agent.asleep:
            asleep_hours.append(hour % 24)
    assert asleep_hours, "never slept"
    assert all(h >= 16 or h <= 6 for h in asleep_hours)   # only around night
    assert 8 <= len(asleep_hours) / 3 <= 14               # hours asleep per night
    assert not any("Collapsed" in text for _, text in agent.events)


def test_sleeping_agents_do_not_act():
    sim = Simulation(Config(initial_agents=1, min_population=0), seed=0)
    agent = sim.agents[0]
    agent.asleep, agent.fatigue = True, 0.9
    seen = []
    class Spy:
        def choose_actions(self, agents, world, config, reach=None, lookup=None):
            seen.append(list(agents))
            return [Action.REST for _ in agents]
    sim.policy = Spy()
    sim.climate.tick_count = 1   # 1am: still night
    sim.tick()
    assert seen == [[]]


def test_urgent_thirst_wakes_a_sleeper():
    sim = Simulation(Config(initial_agents=1, min_population=0), seed=0)
    agent = sim.agents[0]
    agent.asleep, agent.fatigue, agent.water = True, 0.9, 5
    sim.climate.tick_count = 1
    sim._update_body(agent)
    assert not agent.asleep
