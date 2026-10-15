"""Policies decide what every living agent does this tick, all at once."""

import numpy as np

from emergent_world.agents import genes
from emergent_world.agents.agent import Action
from emergent_world.agents.brain import OUTPUT_SIZE, imitate, learn, think
from emergent_world.agents.senses import AGENT_COLOR, RAY_DIRECTIONS, RAY_SIZE, sense_all


MOVE_ACTIONS = (Action.NORTH, Action.SOUTH, Action.EAST, Action.WEST, Action.REST)
SKILL_ACTIONS = (Action.STRIKE, Action.RUB, Action.PICK_UP, Action.DROP, Action.GIVE,
                 Action.COMFORT, Action.CALL, Action.CALL_B, Action.CALL_C)
PEOPLE_ACTIONS = (Action.TAKE, Action.HIT, Action.COMFORT)


class RandomPolicy:
    """Baseline: uniformly random actions."""

    def __init__(self, rng: np.random.Generator):
        self.rng = rng

    def choose_actions(self, agents: list, world, config, reach: int | None = None, lookup=None) -> list:
        return [Action(int(a)) for a in self.rng.integers(0, len(Action), len(agents))]


class BrainPolicy:
    """Each agent's own brain reads its senses and picks an action."""

    def __init__(self, rng: np.random.Generator):
        self.rng = rng

    def choose_actions(self, agents: list, world, config, reach: int | None = None, lookup=None) -> list:
        """`lookup` maps ids to agents, so children can find their parents."""
        if not agents:
            return []
        inputs = sense_all(agents, world, config, reach)
        penalties = np.zeros((len(agents), OUTPUT_SIZE), dtype=np.float32)
        penalties[:, Action.EAT] = self.eat_penalty(agents, world, config)
        penalties[:, :4] = self.steer_penalty(agents, inputs, config)
        penalties *= self.desperation(agents, config)[:, None]
        # Grief: a pull toward sitting still (a negative penalty is a nudge toward).
        grieving = np.array([a.grief > 0 for a in agents])
        penalties[grieving, Action.REST] -= config.grief_rest
        # Company: adults ready for children are drawn toward people they can see.
        penalties[:, :4] -= self.company_pull(agents, inputs, config)
        # What they know, which hunger doesn't change: sticks aren't food, trusted
        # foods are, children stay near their parent, and remembered places pull.
        useless_eat, useless_steer = self.useless_penalty(agents, world, inputs, config)
        penalties[:, Action.EAT] += useless_eat
        penalties[:, :4] += useless_steer
        trust_eat, trust_steer = self.trust_pull(agents, world, inputs, config)
        penalties[:, Action.EAT] -= trust_eat
        penalties[:, :4] -= trust_steer
        penalties[:, :4] -= self.place_pull(agents, inputs, config, lookup or {})
        penalties += self.social_penalty(agents, lookup or {}, config)
        details = {}
        actions = think([a.brain for a in agents], inputs, self.rng,
                        config.action_selection,
                        np.array([genes.value(a, config, "exploration") for a in agents]), penalties, details)
        if config.imitation and lookup:
            self._imitate(agents, lookup, config)
        if config.learning:
            self._learn(agents, details, actions, config)
        for i, agent in enumerate(agents):
            agent.last_seen = inputs[i]
        return [Action(int(a)) for a in actions]

    @staticmethod
    def _learn(agents: list, details: dict, actions, config):
        """Each agent learns from how its last choice turned out: the reward felt
        since then, plus how good things look now, against what it expected."""
        hidden, values = details["hidden"], details["values"]
        for i, agent in enumerate(agents):
            last = agent.last_choice
            if last is not None:
                prev_hidden, prev_action, prev_value = last
                error = agent.reward + config.discount * float(values[i].max()) - prev_value
                learn(agent.brain, prev_hidden, prev_action, error, genes.value(agent, config, "learn_rate"))
            agent.reward = 0.0
            a = int(actions[i])
            agent.last_choice = (hidden[i].copy(), a, float(values[i, a]))

    @staticmethod
    def _imitate(agents: list, lookup: dict, config):
        """People watch each other. Seeing someone nearby do something (not just walk
        about), an onlooker puts themselves in that person's place and leans toward
        doing the same in the same situation: more if it seemed to pay off, away from
        it if it plainly hurt. Skills with no immediate payoff (striking, rubbing,
        carrying, giving) still get copied a little: people copy what others bother
        doing. Relatives and friends are watched most, and children copy most of all."""
        demos = []
        for model in lookup.values():
            last = model.last_choice
            if (not model.alive or model.asleep or last is None or model.last_seen is None
                    or last[1] in MOVE_ACTIONS or model.age < config.maturity_age):
                continue
            payoff = float(np.clip(model.reward * config.imitation_payoff, -1.0, 1.0))
            if last[1] in SKILL_ACTIONS:
                payoff += config.imitation_skill
            if abs(payoff) > 0.05:
                demos.append((model, last[1], payoff))
        if not demos:
            return
        reach = config.vision_range
        for agent in agents:
            best = None
            for model, action, payoff in demos:
                if model is agent or max(abs(model.x - agent.x), abs(model.y - agent.y)) > reach:
                    continue
                regard = 0.3 + agent.known.get(model.id, 0.0) + (1.0 if model.id in agent.kin else 0.0)
                if best is None or regard > best[0]:
                    best = (regard, model, action, payoff)
            if best is None:
                continue
            regard, model, action, payoff = best
            child = 2.0 if agent.age < config.maturity_age else 1.0
            imitate(agent.brain, model.last_seen, action,
                    genes.value(agent, config, "imitation_rate") * regard * child * payoff)
            if payoff > 0:
                agent.copied[action] = (model.id, agent.age)

    @staticmethod
    def _toward(dx: int, dy: int) -> list:
        """Move indices (NORTH 0, SOUTH 1, EAST 2, WEST 3) that close a gap of (dx, dy)."""
        moves = []
        if dx:
            moves.append(2 if dx > 0 else 3)
        if dy:
            moves.append(1 if dy > 0 else 0)
        return moves

    @staticmethod
    def _ray_moves(r: int) -> list:
        dx, dy = RAY_DIRECTIONS[r]
        return BrainPolicy._toward(dx, dy)

    @staticmethod
    def _seen_color(inputs_row, r: int) -> tuple:
        return tuple(int(round(v * 255)) for v in inputs_row[r * RAY_SIZE + 4:r * RAY_SIZE + 7])

    @classmethod
    def useless_penalty(cls, agents: list, world, inputs: np.ndarray, config) -> tuple:
        """Refuse to bite what's known not to be food, and don't walk over to it."""
        eat = np.zeros(len(agents), dtype=np.float32)
        steer = np.zeros((len(agents), 4), dtype=np.float32)
        for i, agent in enumerate(agents):
            useless = agent.memory.useless
            if not useless:
                continue
            kind = config.item(int(world.plants[agent.x, agent.y]))
            if kind is not None and kind.color in useless:
                eat[i] = config.useless_penalty
            for r in range(len(RAY_DIRECTIONS)):
                closeness = inputs[i, r * RAY_SIZE + 7]
                if closeness > 0 and cls._seen_color(inputs[i], r) in useless:
                    for m in cls._ray_moves(r):
                        steer[i, m] += 1.5 * closeness
        return eat, steer

    @classmethod
    def trust_pull(cls, agents: list, world, inputs: np.ndarray, config) -> tuple:
        """Hungry agents want to eat foods they trust, and head for them when seen."""
        eat = np.zeros(len(agents), dtype=np.float32)
        steer = np.zeros((len(agents), 4), dtype=np.float32)
        for i, agent in enumerate(agents):
            hunger = 1.0 - agent.energy / config.max_energy
            if hunger < 0.1 or not agent.memory.trust:
                continue
            kind = config.item(int(world.plants[agent.x, agent.y]))
            if kind is not None:
                eat[i] = config.trust_pull * agent.memory.trusted(kind.color) * (0.5 + hunger)
            best_r, best = None, 0.0
            for r in range(len(RAY_DIRECTIONS)):
                closeness = inputs[i, r * RAY_SIZE + 7]
                if closeness > 0:
                    value = agent.memory.trusted(cls._seen_color(inputs[i], r)) * closeness
                    if value > best:
                        best_r, best = r, value
            if best_r is not None:
                for m in cls._ray_moves(best_r):
                    steer[i, m] += config.trust_pull * best * hunger * 2
        return eat, steer

    @classmethod
    def place_pull(cls, agents: list, inputs: np.ndarray, config, lookup: dict) -> np.ndarray:
        """Children keep close to a parent; thirsty or hungry agents with nothing in
        sight head back to where they last found water or food."""
        pull = np.zeros((len(agents), 4), dtype=np.float32)
        rays = range(len(RAY_DIRECTIONS))
        for i, agent in enumerate(agents):
            if agent.age < config.maturity_age:
                parent = next((p for p in (lookup.get(agent.parent_id), lookup.get(agent.other_parent_id))
                               if p is not None and p.alive), None)
                if parent is None and config.orphans_follow_kin:
                    parent = cls._guardian(agent, lookup, config)
                if parent is not None and parent.alive:
                    dx, dy = parent.x - agent.x, parent.y - agent.y
                    if max(abs(dx), abs(dy)) > 2:
                        for m in cls._toward(dx, dy):
                            pull[i, m] += config.follow_pull
            water_need = 1.0 - agent.water / config.max_water
            water_seen = any(inputs[i, r * RAY_SIZE + 3] > 0 for r in rays)
            if water_need > 0.4 and not water_seen and agent.memory.water_at is not None:
                tx, ty = agent.memory.water_at
                for m in cls._toward(tx - agent.x, ty - agent.y):
                    pull[i, m] += config.homing_pull * water_need * 2
            food_need = 1.0 - agent.energy / config.max_energy
            if food_need > 0.5 and agent.memory.food_at is not None:
                food_seen = any(inputs[i, r * RAY_SIZE + 7] > 0
                                and agent.memory.trusted(cls._seen_color(inputs[i], r)) > 0.2 for r in rays)
                if not food_seen:
                    tx, ty = agent.memory.food_at
                    if (tx, ty) != (agent.x, agent.y):
                        for m in cls._toward(tx - agent.x, ty - agent.y):
                            pull[i, m] += config.homing_pull * food_need
        return pull

    @staticmethod
    def _guardian(child, lookup: dict, config):
        """For an orphan: the nearest living grown relative, or else the grown-up
        they're closest to."""
        best, best_score = None, None
        for other_id in set(child.kin) | set(child.known):
            other = lookup.get(other_id)
            if other is None or not other.alive or other.age < config.maturity_age:
                continue
            score = (2.0 if other_id in child.kin else 0.0) + child.known.get(other_id, 0.0) \
                - 0.02 * max(abs(other.x - child.x), abs(other.y - child.y))
            if best_score is None or score > best_score:
                best, best_score = other, score
        return best

    @staticmethod
    def company_pull(agents: list, inputs: np.ndarray, config) -> np.ndarray:
        """How strongly each agent is drawn toward other people in sight, per move
        (NORTH, SOUTH, EAST, WEST). Adults ready for children feel it strongly."""
        others = np.array(AGENT_COLOR) / 255.0
        pull = np.zeros((len(agents), 4), dtype=np.float32)
        move_of = {(0, -1): 0, (0, 1): 1, (1, 0): 2, (-1, 0): 3}
        for i, agent in enumerate(agents):
            ready = (agent.age >= config.maturity_age and agent.reproduce_cooldown == 0
                     and agent.energy >= config.reproduce_energy and agent.grief == 0)
            strength = (config.mating_pull if ready else 0.0) + config.lonely_pull * agent.loneliness
            if strength < 0.05:
                continue
            for r, (dx, dy) in enumerate(RAY_DIRECTIONS):
                closeness = inputs[i, r * RAY_SIZE + 7]
                if closeness > 0 and np.allclose(inputs[i, r * RAY_SIZE + 4:r * RAY_SIZE + 7], others, atol=0.01):
                    moves = [move_of[(dx, 0)], move_of[(0, dy)]] if dx and dy else [move_of[(dx, dy)]]
                    for m in moves:
                        pull[i, m] += strength * (0.5 + closeness) / len(moves)
        return pull

    @staticmethod
    def social_penalty(agents: list, lookup: dict, config) -> np.ndarray:
        """Innate reluctance to hurt or rob someone, strongest toward family and
        friends and in kind people. Anger at someone who wronged you overrides it,
        and so does hunger when they hold food. Reaching for someone who isn't
        there is pointless, so those actions are held back when nobody's beside you."""
        from emergent_world.agents.emotions import trait
        penalties = np.zeros((len(agents), OUTPUT_SIZE), dtype=np.float32)
        people = [p for p in lookup.values() if p.alive]
        for i, agent in enumerate(agents):
            beside = [p for p in people if p is not agent and max(abs(p.x - agent.x), abs(p.y - agent.y)) <= 1]
            if not beside:
                penalties[i, list(PEOPLE_ACTIONS)] = 3.0
                continue
            other = beside[0]
            bond = agent.known.get(other.id, 0.0) + (1.0 if other.id in agent.kin else 0.0)
            care = config.harm_aversion * (0.5 + trait(agent, "kindness")) * (1.0 + 2.0 * bond)
            release = 3.0 * agent.anger * agent.grudges.get(other.id, 0.0) + 2.0 * agent.anger
            held = config.item(other.hands)
            if held is not None and held.edible:
                release += 2.0 * (1.0 - agent.energy / config.max_energy)
            penalties[i, Action.HIT] = max(0.0, care - release)
            penalties[i, Action.TAKE] = 3.0 if agent.hands or not other.hands else max(0.0, 0.6 * care - release)
        return penalties

    @staticmethod
    def desperation(agents: list, config) -> np.ndarray:
        """Hunger overrides disgust: below half energy, wariness fades, down to a
        tenth of its strength when starving. Without this, an agent that wrongly
        blames its main food can starve rather than ever learn it was safe."""
        energy = np.array([a.energy / config.max_energy for a in agents], dtype=np.float32)
        return np.clip(energy / config.desperation_below, 0.1, 1.0)

    @staticmethod
    def steer_penalty(agents: list, inputs: np.ndarray, config) -> np.ndarray:
        """How much memories hold each agent back from walking toward foods it's
        wary of, judged from what it actually sees along each vision ray.

        Returns (agents, 4) for NORTH, SOUTH, EAST, WEST. Closer foods weigh more;
        a diagonal ray counts half toward each of its two directions.
        """
        move_of = {(0, -1): Action.NORTH, (0, 1): Action.SOUTH,
                   (1, 0): Action.EAST, (-1, 0): Action.WEST}
        penalty = np.zeros((len(agents), 4), dtype=np.float32)
        for i, agent in enumerate(agents):
            if not agent.memory.aversion:
                continue
            for r, (dx, dy) in enumerate(RAY_DIRECTIONS):
                closeness = inputs[i, r * RAY_SIZE + 7]
                if closeness <= 0:
                    continue
                seen = tuple(int(round(v * 255)) for v in inputs[i, r * RAY_SIZE + 4:r * RAY_SIZE + 7])
                wary = agent.memory.level(seen)
                if not wary:
                    continue
                push = config.steer_strength * agent.aversion_gain * wary * closeness
                moves = [move_of[(dx, 0)], move_of[(0, dy)]] if dx and dy else [move_of[(dx, dy)]]
                for move in moves:
                    penalty[i, move] += push / len(moves)
        return penalty

    @staticmethod
    def eat_penalty(agents: list, world, config) -> np.ndarray:
        """How much each agent's memories hold it back from eating what's underfoot."""
        penalty = np.zeros(len(agents), dtype=np.float32)
        for i, agent in enumerate(agents):
            kind = config.item(int(world.plants[agent.x, agent.y]))
            if kind is not None:
                penalty[i] = agent.aversion_gain * agent.memory.level(kind.color)
        return penalty
