"""A hippocampus: memories of particular moments, recalled by need, and replayed in sleep.

Each person keeps a small store of **episodes**: what happened, where, when, and
how much it mattered. Drinking when parched, a good meal, sheltering from a storm,
being hurt, seeing someone else sheltered while you were out in the cold, watching
someone pile wood. Episodes are merged when they happen in the same spot, and
fade with time at a rate that suits what they're about (where water is stays
useful longer than where a meal was). When the store is full, the weakest go.

**Recall** is cued by need: thirst calls up remembered water, hunger food, cold
shelter. The best place weighs how much it mattered, how recently, and how far
away it is. What's recalled is something the brain can sense (direction and
strength), and it also steers the built-in pulls toward water, food and shelter.

**Replay**: experiences (what was sensed, what was done, how it felt) are kept
for a while, and replayed to the brain during sleep, so learning keeps going at
night, the way the hippocampus is thought to train the rest of the brain.
"""

from collections import deque
from dataclasses import dataclass, field

import numpy as np

KINDS = ("water", "food", "shelter", "danger", "build")
NEEDS = ("water", "food", "shelter")          # the kinds recall serves (and the brain senses)
HALF_LIFE_DAYS = {"water": 120, "food": 40, "shelter": 365, "danger": 30, "build": 20}
CAPACITY = 128
REPLAY_CAPACITY = 256
MEMORY_SIZE = 3 * len(NEEDS)                  # brain inputs: dx, dy, strength per need
SENSE_RANGE = 20                              # tiles at which a recalled direction reads as full


@dataclass
class Episode:
    tick: int
    x: int
    y: int
    kind: str
    value: float
    who: int = -1           # someone involved (the person seen sheltering, the builder)


@dataclass
class Hippocampus:
    episodes: list = field(default_factory=list)
    replay: deque = field(default_factory=lambda: deque(maxlen=REPLAY_CAPACITY))
    recalled: dict = field(default_factory=dict)   # need -> (x, y, strength), refreshed now and then

    def strength(self, e: Episode, now: int) -> float:
        age_days = (now - e.tick) / 24.0
        return e.value * 0.5 ** (age_days / HALF_LIFE_DAYS[e.kind])

    def encode(self, now: int, x: int, y: int, kind: str, value: float, who: int = -1) -> Episode:
        """Remember a moment. A new moment of the same kind in the same spot refreshes
        the old memory rather than adding another."""
        for e in self.episodes:
            if e.kind == kind and abs(e.x - x) <= 1 and abs(e.y - y) <= 1:
                e.value = max(self.strength(e, now), value)
                e.tick, e.who = now, (who if who >= 0 else e.who)
                return e
        e = Episode(now, int(x), int(y), kind, float(value), who)
        self.episodes.append(e)
        if len(self.episodes) > CAPACITY:
            weakest = min(range(len(self.episodes)), key=lambda i: self.strength(self.episodes[i], now))
            self.episodes.pop(weakest)
        return e

    def recall(self, kind: str, x: int, y: int, now: int):
        """The best remembered place of this kind from here: (x, y, strength), or None."""
        best, best_score = None, 0.0
        for e in self.episodes:
            if e.kind != kind:
                continue
            score = self.strength(e, now) / (1.0 + max(abs(e.x - x), abs(e.y - y)) / 15.0)
            if score > best_score:
                best, best_score = e, score
        return None if best is None else (best.x, best.y, best_score)

    def refresh(self, x: int, y: int, now: int):
        """Recall the best place for each need, for the senses and the pulls."""
        self.recalled = {}
        for need in NEEDS:
            found = self.recall(need, x, y, now)
            if found is not None and found[2] > 0.02:
                self.recalled[need] = found

    def forget(self, now: int):
        self.episodes = [e for e in self.episodes if self.strength(e, now) > 0.02]

    def best(self, kind: str, now: int, n: int = 3) -> list:
        """The strongest few memories of a kind (what a parent shows a child)."""
        mine = [e for e in self.episodes if e.kind == kind]
        return sorted(mine, key=lambda e: -self.strength(e, now))[:n]


def memory_inputs(agent) -> list:
    """What the brain senses of its memories: for water, food and shelter, the
    direction to the best remembered place and how strongly it's remembered."""
    row = []
    hippo = getattr(agent, "hippo", None)
    for need in NEEDS:
        found = hippo.recalled.get(need) if hippo is not None else None
        if found is None:
            row += [0.0, 0.0, 0.0]
        else:
            tx, ty, s = found
            row += [max(-1.0, min(1.0, (tx - agent.x) / SENSE_RANGE)),
                    max(-1.0, min(1.0, (ty - agent.y) / SENSE_RANGE)), min(1.0, s)]
    return row


def replay_step(brain, transition, discount: float, rate: float) -> None:
    """Relearn one remembered experience (temporal-difference, on the last layer)."""
    from emergent_world.agents.brain import learn
    hidden, action, reward, next_hidden = transition
    values = hidden @ brain.w2 + brain.b2
    next_values = next_hidden @ brain.w2 + brain.b2
    error = reward + discount * float(next_values.max()) - float(values[action])
    learn(brain, hidden, action, error, rate)


def sleep_replay(agent, rng, discount: float, rate: float, count: int) -> None:
    hippo = agent.hippo
    if not hippo.replay or agent.brain is None:
        return
    n = len(hippo.replay)
    for k in rng.integers(0, n, size=min(count, n)):
        replay_step(agent.brain, hippo.replay[int(k)], discount, rate)


def as_array(x):
    return np.asarray(x, dtype=np.float32)
