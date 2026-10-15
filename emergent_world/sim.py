"""The simulation: owns the world, the agents and the tick loop."""

import numpy as np

from emergent_world.agents.agent import MOVES, Action, Agent, Sickness
from emergent_world.agents.policy import RandomPolicy
from emergent_world.config import Config
from emergent_world.stats import Stats
from emergent_world.world.grid import FOOD, POISON, World


class Simulation:
    def __init__(self, config: Config | None = None, seed: int = 0):
        self.config = config or Config()
        self.seed = seed
        # One generator for everything, so a seed replays a run exactly.
        self.rng = np.random.default_rng(seed)
        self.world = World(self.config, self.rng)
        self.policy = RandomPolicy(self.rng)
        self.stats = Stats()
        self.tick_count = 0
        self.agents: list[Agent] = []
        self._next_id = 0
        for _ in range(self.config.initial_agents):
            self.spawn_agent()

    def spawn_agent(self) -> Agent:
        c = self.config
        x, y = self.world.random_walkable_tile()
        agent = Agent(
            id=self._next_id,
            x=x,
            y=y,
            energy=c.max_energy,
            water=c.max_water,
            health=c.max_health,
            lifespan=int(self.rng.integers(c.lifespan[0], c.lifespan[1] + 1)),
        )
        self._next_id += 1
        self.agents.append(agent)
        return agent

    @property
    def living(self) -> list[Agent]:
        return [a for a in self.agents if a.alive]

    def tick(self):
        self.world.tick()
        for agent in self.living:
            action = self.policy.choose_action(agent, self.world)
            self._act(agent, action)
            self._update_body(agent)
        self.tick_count += 1
        self.stats.record_tick(self)

    def _act(self, agent: Agent, action: Action):
        c = self.config
        if action in MOVES:
            dx, dy = MOVES[action]
            if self.world.is_walkable(agent.x + dx, agent.y + dy):
                agent.x += dx
                agent.y += dy
        elif action == Action.EAT:
            plant = self.world.take_plant(agent.x, agent.y)
            if plant == FOOD:
                agent.energy = min(c.max_energy, agent.energy + c.food_energy)
                self.stats.record_meal(agent, "food")
            elif plant == POISON:
                agent.energy = min(c.max_energy, agent.energy + c.poison_energy)
                agent.sicknesses.append(
                    Sickness(c.poison_delay, c.poison_duration, c.poison_damage)
                )
                self.stats.record_meal(agent, "poison")
        elif action == Action.DRINK:
            if self.world.next_to_water(agent.x, agent.y):
                agent.water = min(c.max_water, agent.water + c.drink_amount)

    def _update_body(self, agent: Agent):
        c = self.config
        agent.age += 1
        agent.energy = max(0.0, agent.energy - c.energy_drain)
        agent.water = max(0.0, agent.water - c.water_drain)

        if agent.energy == 0:
            agent.take_damage(c.starvation_damage, "starvation")
        if agent.water == 0:
            agent.take_damage(c.dehydration_damage, "dehydration")

        for sickness in agent.sicknesses:
            if sickness.delay > 0:
                sickness.delay -= 1
            else:
                agent.take_damage(sickness.damage, "poison")
                sickness.duration -= 1
        agent.sicknesses = [s for s in agent.sicknesses if s.duration > 0]

        if agent.energy > 0 and agent.water > 0 and not agent.sicknesses:
            agent.health = min(c.max_health, agent.health + c.healing)

        if agent.health <= 0:
            self._kill(agent, agent.last_damage)
        elif agent.age >= agent.lifespan:
            self._kill(agent, "old_age")

    def _kill(self, agent: Agent, cause: str):
        agent.alive = False
        agent.cause_of_death = cause
        self.stats.record_death(agent, self.tick_count)

    def run(self, ticks: int):
        for _ in range(ticks):
            if not self.living:
                break
            self.tick()
