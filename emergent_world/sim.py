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
        self.instinct_brain = None
        if self.config.instincts_path:
            from emergent_world.instincts import load
            self.instinct_brain = load(self.config.instincts_path)
        self.founders = []
        if self.config.founders_path:
            from emergent_world.prehistory import load_founders
            self.founders = load_founders(self.config.founders_path)
        self.stats = Stats()
        self.tick_count = 0
        self.agents: list[Agent] = []
        self.by_id: dict[int, Agent] = {}
        # (fitness, brain) of recent deaths. Only recent ones, so champions from
        # the easy garden phase don't keep seeding a harder world.
        self.recent_deaths: deque = deque(maxlen=self.config.hall_of_fame_window)
        self._next_id = 0
        # Life stories are written for every agent; on_event, if set, is called
        # for the followed agent's events (the viewer and --story use it).
        self.followed_id: int | None = None
        self.on_event = None
        if self.founders:
            # Founders enter at mixed ages so they don't all grow old and die in
            # the same week. founder_count picks a few at random instead of all.
            chosen = self.founders
            count = self.config.founder_count
            if 0 < count < len(self.founders):
                picks = self.rng.choice(len(self.founders), size=count, replace=False)
                chosen = [self.founders[int(i)] for i in picks]
            for brain in chosen:
                agent = self.spawn_agent(brain=brain)
                agent.age = int(self.rng.integers(0, agent.lifespan // 2))
        else:
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
            brain = self.new_brain()
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
            lineage=parent.lineage if parent else "",
            aversion_gain=self._inherit_gain(parent),
        )
        self._next_id += 1
        self.agents.append(agent)
        self.by_id[agent.id] = agent
        if parent is not None:
            # Family ties: the child knows its parent and siblings, and they know it.
            for sibling_id in parent.offspring:
                sibling = self.by_id.get(sibling_id)
                if sibling is not None:
                    sibling.kin.add(agent.id)
                    agent.kin.add(sibling_id)
            parent.offspring.append(agent.id)
            parent.kin.add(agent.id)
            agent.kin.add(parent.id)
            self.log(agent, f"Born to #{parent.id}")
            self.log(parent, f"Had a child, #{agent.id}")
        else:
            self.log(agent, "Arrived in the world")
        return agent

    # --- Life stories -------------------------------------------------------

    def log(self, agent: Agent, text: str):
        agent.events.append((self.tick_count, text))
        del agent.events[:-200]  # keep the most recent 200
        if self.on_event is not None and agent.id == self.followed_id:
            self.on_event(agent, self.tick_count, text)

    def look_name(self, color) -> str:
        c = self.config
        return {c.food_color: c.food_look, c.poison_color: c.poison_look}.get(color, "something")

    def relation(self, agent: Agent, other: Agent) -> str:
        """What `other` is to `agent`: parent, child or sibling."""
        if other.id == agent.parent_id:
            return "parent"
        if other.parent_id == agent.id:
            return "child"
        return "sibling"

    def follow(self, agent: Agent | None):
        self.followed_id = agent.id if agent is not None else None

    def _pick_next_followed(self, dead: Agent):
        """When the followed agent dies, carry on with family if possible."""
        family = [self.by_id[i] for i in dead.offspring if i in self.by_id and self.by_id[i].alive]
        family = family or [self.by_id[i] for i in dead.kin if i in self.by_id and self.by_id[i].alive]
        candidates = family or [a for a in self.agents if a.alive]
        self.follow(max(candidates, key=lambda a: a.age) if candidates else None)
        nxt = self.by_id.get(self.followed_id) if self.followed_id is not None else None
        if nxt is not None and self.on_event is not None:
            self.on_event(nxt, self.tick_count,
                          f"Now following #{nxt.id} ("
                          + (f"{self.relation(dead, nxt)} of #{dead.id}" if nxt.id in dead.kin
                             else f"no relation to #{dead.id}")
                          + f"), aged {nxt.age // 24} days")

    def _inherit_gain(self, parent: Agent | None) -> float:
        c = self.config
        if parent is None:
            return c.aversion_gain
        return max(0.0, parent.aversion_gain + float(self.rng.normal(0, c.aversion_gain_mutation)))

    def plant_color(self, plant: int):
        """What a plant looks like. Memory is keyed by appearance, never by type."""
        return {FOOD: self.config.food_color, POISON: self.config.poison_color}.get(plant)

    def kin_watching(self, agent: Agent) -> list:
        """Living relatives close enough to see this agent."""
        reach = self.config.vision_range
        watching = []
        for kin_id in agent.kin:
            kin = self.by_id.get(kin_id)
            if kin is not None and kin.alive and max(abs(kin.x - agent.x), abs(kin.y - agent.y)) <= reach:
                watching.append(kin)
        return watching

    def new_brain(self) -> Brain:
        """A brain for an agent with no parent: a founder, instincts, or random."""
        if self.founders:
            founder = self.founders[int(self.rng.integers(0, len(self.founders)))]
            return founder.mutated(self.rng, self.config.mutation_scale, self.config.mutation_rate)
        if self.instinct_brain is not None:
            return self.instinct_brain.mutated(self.rng, self.config.mutation_scale, self.config.mutation_rate)
        return Brain.random(self.rng)

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
        self.by_id = {a.id: a for a in self.agents}
        self._update_memories()
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
            color = self.plant_color(plant)
            if color is not None:
                look = self.look_name(color)
                if color not in agent.firsts:
                    agent.firsts.add(color)
                    self.log(agent, f"Ate a {look} for the first time")
                elif agent.memory.level(color) > 0.5:
                    self.log(agent, f"Ate a {look} despite a bad feeling about it")
                self.stats.record_meal_by_learning(agent, plant == POISON)
                agent.memory.record_meal(self.tick_count, color)
                for kin in self.kin_watching(agent):
                    kin.memory.saw_kin_eat(self.tick_count, agent.id, color)
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
            if self.world.next_to_liquid(agent.x, agent.y):
                if "first drink" not in agent.firsts:
                    agent.firsts.add("first drink")
                    self.log(agent, "Drank water for the first time")
                if "water" in agent.out_of:
                    self.log(agent, "Found water just in time")
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

        for need, level, text in (("food", agent.energy, "Starving: ran out of energy"),
                                  ("water", agent.water, "Parched: ran out of water")):
            if level == 0 and need not in agent.out_of:
                agent.out_of.add(need)
                self.log(agent, text)
            elif level > 0:
                agent.out_of.discard(need)
        if agent.energy == 0:
            agent.take_damage(c.starvation_damage, "starvation")
        if agent.water == 0:
            agent.take_damage(c.dehydration_damage, "dehydration")

        for sickness in agent.sicknesses:
            if sickness.delay > 0:
                sickness.delay -= 1
            else:
                if not sickness.felt:
                    sickness.felt = True
                    blamed = agent.memory.got_sick(self.tick_count, c.aversion_window, c.sickness_aversion)
                    if blamed:
                        looks = " and ".join(sorted(self.look_name(b) for b in blamed))
                        self.log(agent, f"Fell sick; now wary of {looks}")
                    else:
                        self.log(agent, "Fell sick again")
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
        brain = agent.brain.mutated(self.rng, c.mutation_scale, c.mutation_rate) if agent.brain else None
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
                brain = parent.mutated(self.rng, c.mutation_scale, c.mutation_rate)
            self.spawn_agent(brain=brain)
            self.stats.reseeded += 1

    def _update_memories(self):
        c = self.config
        for agent in self.agents:
            agent.memory.settle_meals(self.tick_count, c.aversion_window, c.learned_safety)
            if self.tick_count % 24 == 0:
                agent.memory.forget(self.tick_count, c.aversion_window, c.aversion_fade)

    def _kill(self, agent: Agent, cause: str):
        agent.alive = False
        agent.cause_of_death = cause
        self.log(agent, f"Died of {cause.replace('_', ' ')}, aged {agent.age // 24} days")
        for kin in self.kin_watching(agent):
            text = f"Saw their {self.relation(kin, agent)} #{agent.id} die ({cause.replace('_', ' ')})"
            if cause == "poison":
                blamed = kin.memory.saw_kin_die_of_poison(self.tick_count, agent.id,
                                                          self.config.aversion_window,
                                                          self.config.witness_aversion)
                self.stats.witnessed_deaths += 1
                if blamed:
                    text += "; now wary of " + " and ".join(sorted(self.look_name(b) for b in blamed))
            self.log(kin, text)
        if agent.id == self.followed_id:
            self._pick_next_followed(agent)
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
