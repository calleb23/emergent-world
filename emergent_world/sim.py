"""The simulation: owns the world, the agents and the tick loop."""

from collections import deque

import numpy as np

from emergent_world.agents.agent import MOVES, Action, Agent, Sickness
from emergent_world.agents.brain import Brain
from emergent_world import behaviour
from emergent_world.agents.names import label, make_name
from emergent_world.agents.policy import BrainPolicy, RandomPolicy
from emergent_world.config import Config
from emergent_world.stats import Stats
from emergent_world.world import physics
from emergent_world.world.climate import Climate
from emergent_world.world.grid import World


class Simulation:
    def __init__(self, config: Config | None = None, seed: int = 0):
        self.config = config or Config()
        self.seed = seed
        # One generator for everything, so a seed replays a run exactly.
        self.rng = np.random.default_rng(seed)
        self.world = World(self.config, self.rng)
        self.climate = Climate(self.rng) if self.config.climate else None
        self.world.climate = self.climate   # senses read light and weather through the world
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
        # The world's history: notable firsts and records, as (tick, text).
        self.history: list[tuple[int, str]] = []
        self._world_firsts: set = set()
        self._oldest_death = 0
        self._deepest_generation = 0
        self._most_alive = 0
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
                agent.fatigue = self.config.sleep_threshold  # the world starts at midnight
        else:
            for _ in range(self.config.initial_agents):
                agent = self.spawn_agent()
                agent.fatigue = self.config.sleep_threshold


    @property
    def uses_brains(self) -> bool:
        return isinstance(self.policy, BrainPolicy)

    def spawn_agent(self, x=None, y=None, brain=None, parent: Agent | None = None,
                    energy=None, water=None, father: Agent | None = None) -> Agent:
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
            brain=brain.copy() if brain is not None else None,
            genome=brain,
            generation=parent.generation + 1 if parent else 0,
            parent_id=parent.id if parent else -1,
            lineage=parent.lineage if parent else "",
            name=make_name(self.rng),
            sex="f" if self.rng.random() < 0.5 else "m",
            other_parent_id=father.id if father is not None else -1,
            aversion_gain=self._inherit_gain(parent, father),
        )
        agent.line = parent.line if parent is not None else agent.name
        self._next_id += 1
        self.agents.append(agent)
        self.by_id[agent.id] = agent
        if parent is not None:
            # Family ties: the child knows its parents and siblings, and they know it.
            for p in [parent] + ([father] if father is not None else []):
                for sibling_id in p.offspring:
                    sibling = self.by_id.get(sibling_id)
                    if sibling is not None and sibling_id != agent.id:
                        sibling.kin.add(agent.id)
                        agent.kin.add(sibling_id)
                p.offspring.append(agent.id)
                p.kin.add(agent.id)
                agent.kin.add(p.id)
            parents = label(parent) + (f" and {label(father)}" if father is not None else "")
            self.log(agent, f"Born to {parents}, of the {agent.line} line")
            if agent.generation > self._deepest_generation and agent.generation % 5 == 0:
                self._deepest_generation = agent.generation
                self.chronicle(f"The {agent.line} line reached its {agent.generation}th generation "
                               f"with the birth of {label(agent)}")
            if father is not None:
                self.log(parent, f"Had a child with {father.name}: {label(agent)}")
                self.log(father, f"Had a child with {parent.name}: {label(agent)}")
            else:
                self.log(parent, f"Had a child, {label(agent)}")
        else:
            self.log(agent, f"Arrived in the world, founding the {agent.line} line")
        return agent

    # --- Life stories -------------------------------------------------------

    def chronicle(self, text: str, once: object = None):
        """Record a moment in the world's history (once per key, if one is given)."""
        if once is not None:
            if once in self._world_firsts:
                return
            self._world_firsts.add(once)
        self.history.append((self.tick_count, text))

    def log(self, agent: Agent, text: str):
        agent.events.append((self.tick_count, text))
        del agent.events[:-200]  # keep the most recent 200
        if self.on_event is not None and agent.id == self.followed_id:
            self.on_event(agent, self.tick_count, text)

    def look_name(self, color) -> str:
        return self.config.look_of(color)

    def relation(self, agent: Agent, other: Agent) -> str:
        """What `other` is to `agent`: parent, child or sibling."""
        if other.id in (agent.parent_id, agent.other_parent_id):
            return "parent"
        if agent.id in (other.parent_id, other.other_parent_id):
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
                          f"Now following {label(nxt)} ("
                          + (f"{self.relation(dead, nxt)} of {dead.name}" if nxt.id in dead.kin
                             else f"no relation to {dead.name}")
                          + f"), aged {nxt.age // 24} days")

    def _inherit_gain(self, parent: Agent | None, father: Agent | None = None) -> float:
        c = self.config
        if parent is None:
            return c.aversion_gain
        base = parent.aversion_gain if father is None else (parent.aversion_gain + father.aversion_gain) / 2
        return max(0.0, base + float(self.rng.normal(0, c.aversion_gain_mutation)))

    def plant_color(self, plant: int):
        """What an item looks like. Memory is keyed by appearance, never by type."""
        kind = self.config.item(plant)
        return kind.color if kind else None

    def kin_hearing(self, agent: Agent) -> list:
        """Living relatives close enough to hear this agent cry out, but too far to see."""
        sight, hearing = self.config.vision_range, self.config.hearing_range
        out = []
        for kin_id in agent.kin:
            kin = self.by_id.get(kin_id)
            if kin is not None and kin.alive:
                d = max(abs(kin.x - agent.x), abs(kin.y - agent.y))
                if sight < d <= hearing:
                    out.append(kin)
        return out

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

    @property
    def vision_reach(self) -> int:
        """How far agents can see right now: less at night and in bad weather."""
        if self.climate is None:
            return self.config.vision_range
        return max(2, round(self.config.vision_range * self.climate.visibility))

    def tick(self):
        if self.climate is not None:
            self.climate.tick()
        self.world.tick(self.climate.growth if self.climate is not None else 1.0)
        physics.tick(self)
        physics.grow(self)
        physics.shed(self)
        living = self.living
        occupied = np.zeros((self.world.width, self.world.height), dtype=bool)
        for a in living:
            occupied[a.x, a.y] = True
        self.world.move_critters(occupied, self.climate.growth if self.climate is not None else 1.0)
        awake = [a for a in living if not a.asleep]
        actions = self.policy.choose_actions(awake, self.world, self.config, self.vision_reach, self.by_id)
        for agent, action in zip(awake, actions):
            self._act(agent, action)
            behaviour.after_action(self, agent)
            agent.activity = behaviour.describe(self, agent, action)
        for agent in living:
            self._update_body(agent)
            if agent.asleep:
                agent.activity = behaviour.describe(self, agent, None)
            if agent.alive and not agent.asleep:
                self._maybe_reproduce(agent)
        # Dead agents live on only in the stats log.
        self.agents = [a for a in self.agents if a.alive]
        self.by_id = {a.id: a for a in self.agents}
        self._update_memories()
        self._newcomers()
        self._chronicle_tick()
        if self.uses_brains:
            self._bootstrap()
        self.tick_count += 1
        self.stats.record_tick(self)

    def _act(self, agent: Agent, action: Action):
        c = self.config
        if action in MOVES:
            frail = agent.age / agent.lifespan - c.old_age_from
            if frail > 0 and self.rng.random() < min(0.5, frail * 2):
                return   # old legs: this step doesn't happen
            dx, dy = MOVES[action]
            if self.world.is_walkable(agent.x + dx, agent.y + dy):
                agent.x += dx
                agent.y += dy
        elif action == Action.EAT:
            held = c.item(agent.hands)
            if held is not None and held.edible:
                agent.hands = 0
                self._first(agent, ("ate carried",), f"Ate the {held.look} they were carrying")
                self._consume(agent, held, carried=True)
            else:
                self._eat(agent)
        elif action in (Action.PICK_UP, Action.DROP, Action.GIVE, Action.STRIKE, Action.RUB):
            x, y = agent.x, agent.y
            before = (agent.hands, int(self.world.plants[x, y]), int(self.world.fire[x, y] > 0))
            {Action.PICK_UP: self._pick_up, Action.DROP: self._drop, Action.GIVE: self._give,
             Action.STRIKE: lambda a: physics.strike(self, a), Action.RUB: lambda a: physics.rub(self, a)}[action](agent)
            after = (agent.hands, int(self.world.plants[x, y]), int(self.world.fire[x, y] > 0))
            if before != after:
                self._copied_success(agent, action)
        elif action == Action.DRINK:
            held = c.item(agent.hands)
            if held is not None and held.water and not self.world.next_to_liquid(agent.x, agent.y):
                agent.water = min(c.max_water, agent.water + held.water)
                agent.hands = c.item_id(held.empties_into) if held.empties_into else 0
                self._first(agent, ("drank carried",), f"Drank from the {held.look} they were carrying")
                self.chronicle(f"{label(agent)} carried water away from the pond and drank it",
                               once="carried water")
            elif self.world.next_to_liquid(agent.x, agent.y):
                if held is not None and held.holds_water:
                    agent.hands = c.item_id(held.holds_water)
                    self._first(agent, ("filled", held.look), f"Dipped a {held.look} in the water; it filled")
                if "first drink" not in agent.firsts:
                    agent.firsts.add("first drink")
                    self.log(agent, "Drank water for the first time")
                if "water" in agent.out_of:
                    self.log(agent, "Found water just in time")
                agent.water = min(c.max_water, agent.water + c.drink_amount)
                agent.memory.water_at = (agent.x, agent.y)

    def _copied_success(self, agent: Agent, action):
        """They did something that worked, having lately watched someone else do it."""
        seen = agent.copied.get(action)
        if seen is None or agent.age - seen[1] > 72:
            return
        model = self.by_id.get(seen[0])
        if model is None or ("copied", action) in agent.firsts:
            return
        agent.firsts.add(("copied", action))
        verb = {Action.PICK_UP: "pick things up", Action.DROP: "put things down", Action.GIVE: "give things",
                Action.STRIKE: "strike things", Action.RUB: "rub things together"}[action]
        self.log(agent, f"Did what they'd watched {model.name} do: learned to {verb}")
        self.chronicle(f"{label(agent)} learned to {verb} by watching {label(model)}", once=("copied", action))

    def _first(self, agent: Agent, key, text: str):
        """Log a life event only the first time it happens."""
        if key not in agent.firsts:
            agent.firsts.add(key)
            self.log(agent, text)

    def _pick_up(self, agent: Agent):
        if agent.hands:
            return
        kind = self.config.item(int(self.world.plants[agent.x, agent.y]))
        if kind is None:
            return
        if kind.immovable or kind.mass > self.config.max_carry:
            self._first(agent, ("heavy", kind.look), f"Tried to pick up a {kind.look}; it wouldn't budge")
            return
        if kind.prickly:
            agent.take_damage(kind.prickly, "thorns")
        self.world.take_plant(agent.x, agent.y)
        agent.hands = self.config.items.index(kind) + 1
        self._first(agent, ("picked", kind.color), f"Picked up a {kind.look} for the first time")
        self.chronicle(f"{label(agent)} was the first to pick something up: a {kind.look}", once="picked up")

    def _drop(self, agent: Agent):
        """Put down what's held. A stick dropped where sticks already lie adds to the
        pile; enough sticks in one spot make a shelter."""
        held = self.config.item(agent.hands)
        if held is None:
            return
        x, y = agent.x, agent.y
        if held.sticky and self.rng.random() < held.sticky / 20:
            self._first(agent, ("sticky", held.look), f"Tried to put down a {held.look}; it stuck to their fingers")
            return
        if physics.reinforce(self, agent):
            return
        if self.world.plants[x, y] and physics.join(self, agent):
            return
        if self.world.fire[x, y] and held.burn_hours:
            agent.hands = 0
            self.world.fire[x, y] += held.burn_hours
            self._first(agent, ("stoked",), f"Fed a {held.look} to a fire; it flared up")
            self.chronicle(f"{label(agent)} fed a fire to keep it going", once="stoked")
            return
        if held.look == "stick" and self.world.terrain[x, y] == 0:
            agent.hands = 0
            if self.world.add_to_shelter(x, y, self.config.sticks_per_shelter):
                self.log(agent, "Dropped a stick on the pile, and it became a shelter")
                self.chronicle(f"{label(agent)} made the first shelter, from a pile of sticks", once="shelter")
            else:
                self._first(agent, ("dropped stick",), "Put a stick down")
            return
        if self.world.plants[x, y] == 0:
            agent.hands = 0
            if held.brittle and held.breaks_into and self.rng.random() < held.brittle:
                self.world.plants[x, y] = self.config.item_id(held.breaks_into)
                if held.water:
                    self.world.wet[x, y] = 1.0   # spilled
                self._first(agent, ("smashed", held.look), f"Put down a {held.look} too hard; it broke")
                return
            self.world.plants[x, y] = self.config.item_id(held.look)
            self._first(agent, ("dropped", held.color), f"Put down a {held.look}")

    def _give(self, agent: Agent):
        """Hand what's held to the nearest person right next to you."""
        held = self.config.item(agent.hands)
        if held is None:
            return
        near = [o for o in self.agents if o is not agent and o.alive and not o.hands
                and max(abs(o.x - agent.x), abs(o.y - agent.y)) <= 1]
        if not near:
            return
        other = near[0]
        other.hands, agent.hands = agent.hands, 0
        self.log(agent, f"Gave a {held.look} to {other.name}")
        self.log(other, f"{agent.name} gave them a {held.look}")
        self.chronicle(f"{label(agent)} gave something to someone for the first time: "
                       f"a {held.look}, to {other.name}", once="gave")
        for a, b in ((agent, other), (other, agent)):
            a.known[b.id] = min(1.0, a.known.get(b.id, 0) + 0.05)

    def _eat(self, agent: Agent):
        """Try to eat whatever loose item is underfoot. Instinct tries anything solid."""
        c = self.config
        kind = c.item(int(self.world.plants[agent.x, agent.y]))
        if kind is None:
            return
        color, look = kind.color, kind.look
        if not kind.edible:
            # A rock or stick: nothing happens, and it stays where it is. Now they
            # know it isn't food, and so does any relative who saw.
            if ("bit", color) not in agent.firsts:
                agent.firsts.add(("bit", color))
                self.log(agent, f"Tried to eat a {look}; nothing happened. Not food.")
            agent.memory.bit_inedible(color)
            for kin in self.kin_watching(agent):
                if color not in kin.memory.useless:
                    kin.memory.saw_kin_bite_inedible(color)
                    self.log(kin, f"Watched {agent.name} bite a {look} for nothing; learned it isn't food")
            return
        self.world.take_plant(agent.x, agent.y)
        self._consume(agent, kind)

    def _consume(self, agent: Agent, kind, carried: bool = False):
        """Eat an edible item, from the ground or from the hands."""
        c = self.config
        color, look = kind.color, kind.look
        if color not in agent.firsts:
            agent.firsts.add(color)
            caught = "Caught and ate" if kind.wanders else "Ate"
            self.log(agent, f"{caught} a {look} for the first time")
            self.chronicle(f"{label(agent)} was the first to {'catch and eat' if kind.wanders else 'eat'} a {look}",
                           once=("ate", color))
        elif agent.memory.level(color) > 0.5:
            self.log(agent, f"Ate a {look} despite a bad feeling about it")
        self.stats.record_meal_by_learning(agent, kind.harmful)
        agent.memory.record_meal(self.tick_count, color)
        for kin in self.kin_watching(agent):
            kin.memory.saw_kin_eat(self.tick_count, agent.id, color)
            if agent.id in (kin.parent_id, kin.other_parent_id):
                if kin.memory.trusted(color) < 0.2 and ("learned", color) not in kin.firsts:
                    kin.firsts.add(("learned", color))
                    self.log(kin, f"Watched {agent.name} eat a {look}; learning it's food")
                kin.memory.saw_parent_eat(color, c.parent_trust)
        if not carried and agent.memory.level(color) < 0.3:
            agent.memory.food_at = (agent.x, agent.y)
        agent.energy = min(c.max_energy, agent.energy + kind.energy)
        if kind.cures and agent.sicknesses:
            agent.sicknesses = []
            self.log(agent, f"Ate a {look} while sick, and the sickness passed")
            self.chronicle(f"{label(agent)} ate a {look} while sick and recovered", once=("cured", look))
        if kind.harmful:
            agent.sicknesses.append(Sickness(kind.toxin_delay, kind.toxin_hours, kind.toxin))
        self.stats.record_meal(agent, "poison" if kind.harmful else "food")

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
        hunger = thirst = self.difficulty
        if self.climate is not None:
            hunger *= self.climate.hunger
            thirst *= self.climate.thirst
            self._update_sleep(agent)
            if agent.asleep:
                hunger *= c.sleep_drain
                thirst *= c.sleep_drain
        if self.world.fire[agent.x, agent.y]:
            agent.take_damage(physics.BURN_DAMAGE, "fire")
            agent.memory.burned(physics.FIRE_COLOR)
            self._first(agent, ("burned",), "Stepped into fire and was burned")
        carried = c.item(agent.hands)
        if carried is not None and not agent.asleep:
            agent.fatigue = min(1.0, agent.fatigue + c.carry_fatigue * carried.mass)   # heavy loads tire
        underfoot = c.item(int(self.world.plants[agent.x, agent.y]))
        if underfoot is not None and underfoot.prickly:
            agent.take_damage(underfoot.prickly, "thorns")
            agent.memory.burned(underfoot.color, 0.3)
            self._first(agent, ("pricked", underfoot.look), f"Walked into a {underfoot.look}; it scratched")
        out_in_it = behaviour.exposed(self, agent)
        if out_in_it:
            hunger *= c.exposure_hunger
            agent.take_damage(c.exposure_damage, "exposure")
            if ("exposed",) not in agent.firsts:
                agent.firsts.add(("exposed",))
                self.log(agent, "Caught out in the cold and wet with nowhere to shelter")
        agent.energy = max(0.0, agent.energy - c.energy_drain * hunger)
        agent.water = max(0.0, agent.water - c.water_drain * thirst)
        self._update_fat(agent)
        agent.grief = max(0, agent.grief - 1)
        old = agent.age >= c.old_age_from * agent.lifespan
        if old and ("old",) not in agent.firsts:
            agent.firsts.add(("old",))
            self.log(agent, "Growing old: slower to heal, and steps come harder")

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
            rest = c.sleep_healing if agent.asleep else 1.0
            frailty = 0.5 if old else 1.0
            agent.health = min(c.max_health, agent.health + c.healing * rest * frailty)
        if agent.fatigue >= 1.0 and not agent.asleep:
            agent.take_damage(c.exhaustion_damage, "exhaustion")

        self._feel(agent)
        if agent.health <= 0:
            self._kill(agent, agent.last_damage)
        elif agent.age >= agent.lifespan:
            self._kill(agent, "old_age")

    def _feel(self, agent: Agent):
        """How much better or worse this hour felt. Needs easing feels good, pain,
        cold and wet, and boredom feel bad, new ground feels good. Brains learn
        from this; the viewer shows its running average as mood."""
        c = self.config
        levels = (agent.energy / c.max_energy, agent.water / c.max_water,
                  agent.health / c.max_health, 1.0 - agent.fatigue)
        comfort = -sum((1.0 - v) ** 2 for v in levels)
        feeling = 0.0 if agent.comfort is None else 2.0 * (comfort - agent.comfort)
        agent.comfort = comfort
        if behaviour.exposed(self, agent):
            feeling -= c.exposure_weight
        feeling -= c.boredom_weight * agent.boredom
        if len(agent.recent) >= 2 and agent.recent[-1] not in agent.recent[:-1]:
            feeling += c.novelty_reward
        if agent.last_damage and agent.health < agent.last_health:
            feeling -= c.pain_weight * (agent.last_health - agent.health)
        agent.last_health = agent.health
        agent.reward += feeling
        agent.mood = 0.99 * agent.mood + 0.01 * feeling * 10

    def _update_fat(self, agent: Agent):
        """Spare energy is stored as fat; in lean times fat is burned back."""
        c = self.config
        if agent.energy > c.store_fat_above * c.max_energy and agent.fat < c.max_fat:
            moved = min(c.fat_store_rate, c.max_fat - agent.fat)
            agent.energy -= moved
            agent.fat += moved * 0.8
        elif agent.energy < c.burn_fat_below * c.max_energy and agent.fat > 0:
            burned = min(c.fat_burn_rate, agent.fat)
            agent.fat -= burned
            agent.energy += burned

    def _update_sleep(self, agent: Agent):
        """Tiredness builds while awake. Tired agents sleep at night and wake
        rested, or early if thirst, hunger or sickness gets bad; pushed too far,
        they collapse wherever they are."""
        c, climate = self.config, self.climate
        if agent.asleep:
            agent.fatigue = max(0.0, agent.fatigue - c.rest_rate)
            urgent = (agent.water < 0.15 * c.max_water or agent.energy < 0.10 * c.max_energy
                      or any(s.felt for s in agent.sicknesses))
            # Sleep lasts until dawn once rested; nobody gets up in the dark for no reason.
            rested = not climate.is_night and agent.fatigue < c.wake_threshold
            if urgent or rested:
                agent.asleep = False
                if urgent and agent.fatigue > 0.5 and ("woke", "urgent") not in agent.firsts:
                    agent.firsts.add(("woke", "urgent"))
                    self.log(agent, "Woke in the night, too thirsty or hungry to sleep")
        else:
            agent.fatigue = min(1.0, agent.fatigue + c.fatigue_rate)
            if agent.fatigue >= 1.0:
                agent.asleep = True
                self.log(agent, "Collapsed from exhaustion")
            elif climate.is_night and agent.fatigue >= c.sleep_threshold:
                agent.asleep = True
        weather = climate.weather
        if weather in ("storm", "snow") and ("weather", weather) not in agent.firsts:
            agent.firsts.add(("weather", weather))
            self.log(agent, "Caught in a storm for the first time" if weather == "storm"
                     else "Saw snow for the first time")

    def _maybe_reproduce(self, agent: Agent):
        c = self.config
        if (agent.age < c.maturity_age
                or agent.energy < c.reproduce_energy
                or agent.water < c.reproduce_water
                or agent.reproduce_cooldown > 0
                or len(self.agents) >= c.max_population):
            return
        father = None
        if c.two_parents:
            if agent.sex != "f":
                return
            father = self._find_partner(agent)
            if father is None:
                return
            father.energy = max(0.0, father.energy - c.father_cost_energy)
            father.children += 1
        x, y = self._free_neighbor(agent)
        agent.energy -= c.reproduce_cost_energy
        agent.water = max(0.0, agent.water - c.reproduce_cost_water)
        agent.reproduce_cooldown = c.reproduce_cooldown
        agent.children += 1
        source = agent if father is None or self.rng.random() < 0.5 else father
        brain = source.genome.mutated(self.rng, c.mutation_scale, c.mutation_rate) if source.genome else None
        child = self.spawn_agent(x, y, brain=brain, parent=agent, father=father,
                                 energy=c.child_energy, water=c.child_water)
        self.stats.record_birth(child)

    def _find_partner(self, mother: Agent) -> Agent | None:
        """A willing adult male nearby: awake, reasonably fed, and not close family."""
        c = self.config
        best, best_score = None, None
        for other in self.agents:
            if (other.sex != "m" or not other.alive or other.asleep or other.id in mother.kin
                    or other.age < c.maturity_age or other.energy < 0.3 * c.max_energy):
                continue
            d = max(abs(other.x - mother.x), abs(other.y - mother.y))
            if d > c.mate_range:
                continue
            # Someone she's close to beats someone merely nearby.
            score = mother.known.get(other.id, 0.0) * 10 - d
            if best_score is None or score > best_score:
                best, best_score = other, score
        return best

    def _free_neighbor(self, agent: Agent) -> tuple:
        options = [(agent.x + dx, agent.y + dy) for dx, dy in MOVES.values()
                   if self.world.is_walkable(agent.x + dx, agent.y + dy)]
        if not options:
            return agent.x, agent.y
        return options[int(self.rng.integers(0, len(options)))]

    def _newcomers(self):
        """Now and then a stranger arrives at the edge of the world."""
        c = self.config
        if (not c.newcomer_every_days or not self.uses_brains or len(self.agents) >= c.max_population
                or self.rng.random() >= 1.0 / (c.newcomer_every_days * 24)):
            return
        edge = int(self.rng.integers(0, 4))
        for _ in range(50):
            along = int(self.rng.integers(0, self.world.width))
            x, y = [(along, 0), (along, self.world.height - 1), (0, along), (self.world.width - 1, along)][edge]
            if self.world.is_walkable(x, y):
                break
        else:
            return
        # Strangers come from people much like those already here: their brain is a
        # varied copy of a living adult's, as that adult is now, with all it has learned.
        adults = [a for a in self.agents if a.alive and a.brain is not None and a.age >= c.maturity_age]
        brain = None
        if adults:
            kin_of = adults[int(self.rng.integers(0, len(adults)))]
            brain = kin_of.brain.mutated(self.rng, c.mutation_scale, c.mutation_rate)
        agent = self.spawn_agent(x, y, brain=brain)
        agent.age = int(c.maturity_age + self.rng.integers(0, max(1, agent.lifespan // 3)))
        agent.events[-1] = (self.tick_count, f"Wandered in from beyond the edge of the world, "
                                             f"founding the {agent.line} line")
        self.chronicle(f"{label(agent)}, a stranger, wandered in from beyond the edge of the world")

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

    def _update_bonds(self):
        """People near each other while awake get to know each other."""
        c = self.config
        awake = [a for a in self.agents if a.alive and not a.asleep]
        for i, a in enumerate(awake):
            for b in awake[i + 1:]:
                if max(abs(a.x - b.x), abs(a.y - b.y)) > c.company_range:
                    continue
                for me, other in ((a, b), (b, a)):
                    before = me.known.get(other.id)
                    now = min(1.0, (before or 0.0) + c.bond_per_hour)
                    me.known[other.id] = now
                    if before is None and other.id not in me.kin:
                        self.log(me, f"Met {label(other)} for the first time")
                    if (before or 0) < c.close_bond <= now:
                        self.log(me, f"Became close to {other.name}")
        if self.tick_count % 24 == 0:
            for a in self.agents:
                for other_id in list(a.known):
                    a.known[other_id] *= c.bond_fade
                    if a.known[other_id] < 0.005:
                        del a.known[other_id]

    def _update_memories(self):
        c = self.config
        self._update_bonds()
        for agent in self.agents:
            agent.memory.settle_meals(self.tick_count, c.aversion_window, c.learned_safety, c.trust_gain)
            if self.tick_count % 24 == 0:
                agent.memory.forget(self.tick_count, c.aversion_window, c.aversion_fade)

    def _kill(self, agent: Agent, cause: str):
        agent.alive = False
        agent.cause_of_death = cause
        self.log(agent, f"Died of {cause.replace('_', ' ')}, aged {agent.age // 24} days")
        for kin in self.kin_watching(agent):
            text = f"Saw their {self.relation(kin, agent)} {label(agent)} die ({cause.replace('_', ' ')})"
            if cause == "poison":
                blamed = kin.memory.saw_kin_die_of_poison(self.tick_count, agent.id,
                                                          self.config.aversion_window,
                                                          self.config.witness_aversion)
                self.stats.witnessed_deaths += 1
                if blamed:
                    text += "; now wary of " + " and ".join(sorted(self.look_name(b) for b in blamed))
            self.log(kin, text)
            self._grieve(kin, agent)
        for kin in self.kin_hearing(agent):
            self.log(kin, f"Heard their {self.relation(kin, agent)} {label(agent)} cry out, far off, and fall silent")
            self._grieve(kin, agent)
        for friend in self.agents:
            if (friend.alive and friend.id not in agent.kin
                    and friend.known.get(agent.id, 0) >= self.config.close_bond):
                self.log(friend, f"Lost {agent.name}, who they were close to")
                self._grieve(friend, agent)
        if agent.id == self.followed_id:
            self._pick_next_followed(agent)
        self._chronicle_death(agent, cause)
        self.stats.record_death(agent, self.tick_count)
        if agent.genome is not None:
            fitness = agent.age + self.config.child_fitness * agent.children
            self.recent_deaths.append((fitness, agent.genome))

    def _grieve(self, mourner: Agent, lost: Agent):
        """Losing close family weighs on someone for days: they want to sit still."""
        close = (lost.id in (mourner.parent_id, mourner.other_parent_id)
                 or mourner.id in (lost.parent_id, lost.other_parent_id)
                 or mourner.known.get(lost.id, 0) >= self.config.close_bond)
        mourner.grief = max(mourner.grief, self.config.grief_hours * (2 if close else 1))
        if close:
            self.log(mourner, f"Grieving for {lost.name}")

    def _chronicle_death(self, agent: Agent, cause: str):
        words = cause.replace("_", " ")
        self.chronicle(f"{label(agent)} became the first to die of {words}", once=("death", cause))
        days = agent.age // 24
        if days > self._oldest_death and days > 60:
            self._oldest_death = days
            self.chronicle(f"{label(agent)} died aged {days} days, the oldest anyone has lived")
        if not any(a.alive and a.line == agent.line for a in self.agents):
            self.chronicle(f"The {agent.line} line died out with {label(agent)}")

    def _chronicle_tick(self):
        alive = len(self.agents)
        if alive > self._most_alive and alive >= 20 and alive % 10 == 0:
            self._most_alive = alive
            self.chronicle(f"The world's population reached {alive}")
        if self.climate is not None:
            if self.climate.weather == "snow":
                self.chronicle("The first snow fell", once="snow")
            if self.climate.weather == "storm":
                self.chronicle("The first storm swept over the world", once="storm")

    def run(self, ticks: int, progress_every: int = 0):
        for _ in range(ticks):
            if not self.living:
                break
            self.tick()
            if progress_every and self.tick_count % progress_every == 0:
                print(self.stats.progress_line(self))
