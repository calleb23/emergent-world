"""The simulation: owns the world, the agents and the tick loop."""

from collections import deque

import numpy as np

from emergent_world.agents.agent import MOVES, Action, Agent, Sickness
from emergent_world.agents.brain import Brain
from emergent_world.agents.policy import BrainPolicy, RandomPolicy
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
        if self.config.policy == "random":
            self.policy = RandomPolicy(self.rng)
        else:
            self.policy = BrainPolicy(self.rng)
        self.stats = Stats()
        self.tick_count = 0
        self.agents: list[Agent] = []
        # (fitness, brain) of recent deaths. Only recent ones, so champions from
        # the easy garden phase don't keep seeding a harder world.
        self.recent_deaths: deque = deque(maxlen=self.config.hall_of_fame_window)
        self._next_id = 0
        for _ in range(self.config.initial_agents):
            self.spawn_agent()

    @property
    def uses_brains(self) -> bool:
        return isinstance(self.policy, BrainPolicy)

    def spawn_agent(self, x=None, y=None, brain=None, parent: Agent | None = None,
                    energy=None, water=None) -> Agent:
        c = self.config
        if x is None:
            x, y = self.world.random_walkable_tile()
        if brain is None and self.uses_brains:
            brain = Brain.random(self.rng)
        agent = Agent(
            id=self._next_id,
            x=x,
            y=y,
            energy=c.max_energy if energy is None else energy,
            water=c.max_water if water is None else water,
            health=c.max_health,
            lifespan=int(self.rng.integers(c.lifespan[0], c.lifespan[1] + 1)),
            brain=brain,
            generation=parent.generation + 1 if parent else 0,
            parent_id=parent.id if parent else -1,
        )
        self._next_id += 1
        self.agents.append(agent)
        return agent

    @property
    def living(self) -> list[Agent]:
        return [a for a in self.agents if a.alive]

    def tick(self):
        self.world.tick()
        living = self.living
        actions = self.policy.choose_actions(living, self.world, self.config)
        for agent, action in zip(living, actions):
            self._act(agent, action)
            self._update_body(agent)
            if agent.alive:
                self._maybe_reproduce(agent)
        # Dead agents live on only in the stats log.
        self.agents = [a for a in self.agents if a.alive]
        if self.uses_brains:
            self._bootstrap()
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

    @property
    def difficulty(self) -> float:
        """Drain multiplier: starts gentle, reaches 1.0 after the garden phase."""
        c = self.config
        if c.garden_ticks <= 0:
            return 1.0
        progress = min(1.0, self.tick_count / c.garden_ticks)
        return c.garden_start + (1.0 - c.garden_start) * progress

    def _update_body(self, agent: Agent):
        c = self.config
        agent.age += 1
        agent.reproduce_cooldown = max(0, agent.reproduce_cooldown - 1)
        agent.energy = max(0.0, agent.energy - c.energy_drain * self.difficulty)
        agent.water = max(0.0, agent.water - c.water_drain * self.difficulty)

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

    def _maybe_reproduce(self, agent: Agent):
        c = self.config
        if (agent.age < c.maturity_age
                or agent.energy < c.reproduce_energy
                or agent.water < c.reproduce_water
                or agent.reproduce_cooldown > 0
                or len(self.agents) >= c.max_population):
            return
        x, y = self._free_neighbor(agent)
        agent.energy -= c.reproduce_cost_energy
        agent.water = max(0.0, agent.water - c.reproduce_cost_water)
        agent.reproduce_cooldown = c.reproduce_cooldown
        agent.children += 1
        brain = agent.brain.mutated(self.rng, c.mutation_scale) if agent.brain else None
        child = self.spawn_agent(x, y, brain=brain, parent=agent,
                                 energy=c.child_energy, water=c.child_water)
        self.stats.record_birth(child)

    def _free_neighbor(self, agent: Agent) -> tuple:
        options = [(agent.x + dx, agent.y + dy) for dx, dy in MOVES.values()
                   if self.world.is_walkable(agent.x + dx, agent.y + dy)]
        if not options:
            return agent.x, agent.y
        return options[int(self.rng.integers(0, len(options)))]

    def _bootstrap(self):
        """Top up the population while evolution gets going."""
        c = self.config
        missing = c.min_population - len(self.agents)
        if missing <= 0:
            return
        ranked = sorted(self.recent_deaths, key=lambda entry: entry[0], reverse=True)
        best = [brain for _, brain in ranked[:c.hall_of_fame_size]]
        for _ in range(missing):
            brain = None
            if best and self.rng.random() < c.reseed_from_best:
                parent = best[int(self.rng.integers(0, len(best)))]
                brain = parent.mutated(self.rng, c.mutation_scale)
            self.spawn_agent(brain=brain)
            self.stats.reseeded += 1

    def _kill(self, agent: Agent, cause: str):
        agent.alive = False
        agent.cause_of_death = cause
        self.stats.record_death(agent, self.tick_count)
        if agent.brain is not None:
            fitness = agent.age + self.config.child_fitness * agent.children
            self.recent_deaths.append((fitness, agent.brain))

    def run(self, ticks: int, progress_every: int = 0):
        for _ in range(ticks):
            if not self.living:
                break
            self.tick()
            if progress_every and self.tick_count % progress_every == 0:
                print(self.stats.progress_line(self))
