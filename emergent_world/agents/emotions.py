"""Feelings, personality, and what people sense of each other.

Emotions are states the body and the social world produce. Nothing here makes
anyone act: people feel these, sense them (their own, and the faces of whoever
is nearest), and their brains learn what to do about them, because fear,
anger and loneliness feel bad, and comfort, gifts and company feel good.

- Fear rises with pain, with dangerous animals or fire close by, and with
  alarm calls; it fades fast. Bold people feel less of it.
- Anger rises when someone hits you or takes what you hold; it fades over a
  day or so, but leaves a grudge against that person that fades much slower.
  Hot-tempered people feel more of it.
- Loneliness builds away from anyone you know, and eases in company.
  Sociable people feel it sooner; children far sooner.
- Joy follows good moments: meals, warmth, gifts, being comforted.

Personality is four inherited traits (0-1, around 0.5): boldness, sociability,
temper and kindness. A child's are the mean of its parents', plus a little
variation, so temperaments run in families and can evolve.
"""

import numpy as np

TRAITS = ("boldness", "sociability", "temper", "kindness")

# Brain inputs, appended after the body's feelings:
#   own feelings: fear, anger, loneliness, joy, grief
#   nearest person in sight: their fear, anger, joy; my bond with them, kin,
#     my grudge against them, whether they hold something, whether they're beside me
#   loudest call heard: direction (dx, dy), loudness, alarm in it, and which of
#     the three sounds it was (one-hot)
CALL_SOUNDS = 3
SOCIAL_SIZE = 5 + 8 + 4 + CALL_SOUNDS


def random_traits(rng) -> dict:
    return {t: float(np.clip(rng.normal(0.5, 0.15), 0.0, 1.0)) for t in TRAITS}


def inherit_traits(rng, parent, father=None) -> dict:
    if parent is None or not parent.traits:
        return random_traits(rng)
    sources = [parent] + ([father] if father is not None and father.traits else [])
    return {t: float(np.clip(sum(p.traits[t] for p in sources) / len(sources) + rng.normal(0, 0.08), 0.0, 1.0))
            for t in TRAITS}


def trait(agent, name: str) -> float:
    return agent.traits.get(name, 0.5) if agent.traits else 0.5


def update(sim, agent) -> None:
    """One hour of feelings. Call before the hour's reward is worked out."""
    c = sim.config
    timid = 1.5 - trait(agent, "boldness")
    hurt = max(0.0, agent.last_health - agent.health) / c.max_health
    threat = 0.0
    world = sim.world
    x0, y0 = max(0, agent.x - 2), max(0, agent.y - 2)
    near = world.plants[x0:agent.x + 3, y0:agent.y + 3]
    if sim.biter_ids and np.isin(near, sim.biter_ids).any():
        threat += 0.15
    if world.fire[x0:agent.x + 2, y0:agent.y + 2].any():
        threat += 0.1
    alarm = 0.0
    if agent.heard is not None:
        alarm = agent.heard[2] * agent.heard[3]
    agent.fear = min(1.0, agent.fear * 0.85 + timid * (4.0 * hurt + threat + 0.3 * alarm))
    agent.anger = agent.anger * 0.93
    agent.joy = agent.joy * 0.9

    company = False
    for other in sim.agents:
        if other is agent or not other.alive:
            continue
        if max(abs(other.x - agent.x), abs(other.y - agent.y)) <= c.company_range and (
                other.id in agent.kin or agent.known.get(other.id, 0.0) >= 0.1):
            company = True
            break
    if company:
        agent.loneliness = max(0.0, agent.loneliness - 0.08)
    else:
        rate = c.loneliness_rate * (0.5 + trait(agent, "sociability"))
        if agent.age < c.maturity_age:
            rate *= 3.0
        agent.loneliness = min(1.0, agent.loneliness + rate)

    if sim.tick_count % 24 == 0:
        for other_id in list(agent.grudges):
            agent.grudges[other_id] *= 0.97
            if agent.grudges[other_id] < 0.02:
                del agent.grudges[other_id]


def feeling_cost(agent, config) -> float:
    """How much the hour's emotions weigh, as a cost against the hour's reward."""
    return (config.fear_weight * agent.fear + config.anger_weight * agent.anger
            + config.lonely_weight * agent.loneliness)


def provoke(victim, culprit, amount: float) -> None:
    """Someone wronged them: anger now, and a grudge against that person.
    It stings less when it's your own child."""
    if culprit.id in victim.offspring:
        amount *= 0.3
    victim.anger = min(1.0, victim.anger + amount * (0.5 + trait(victim, "temper")))
    victim.grudges[culprit.id] = min(1.0, victim.grudges.get(culprit.id, 0.0) + amount)
    victim.known[culprit.id] = max(0.0, victim.known.get(culprit.id, 0.0) - 0.5 * amount)


def nearest_person(agent, people, reach: int):
    best, best_d = None, reach + 1
    for other in people:
        if other is agent or not other.alive:
            continue
        d = max(abs(other.x - agent.x), abs(other.y - agent.y))
        if d < best_d:
            best, best_d = other, d
    return best, best_d


def social_inputs(agent, people, config) -> list:
    grief = min(1.0, agent.grief / max(1, config.grief_hours * 2))
    row = [agent.fear, agent.anger, agent.loneliness, agent.joy, grief]
    other, d = nearest_person(agent, people, config.vision_range)
    if other is None:
        row += [0.0] * 8
    else:
        row += [other.fear, other.anger, other.joy, agent.known.get(other.id, 0.0),
                1.0 if other.id in agent.kin else 0.0, agent.grudges.get(other.id, 0.0),
                1.0 if other.hands else 0.0, 1.0 if d <= 1 else 0.0]
    if agent.heard is None:
        row += [0.0] * (4 + CALL_SOUNDS)
    else:
        dx, dy, loud, alarm, sound = agent.heard
        row += [dx, dy, loud, alarm] + [1.0 if k == sound else 0.0 for k in range(CALL_SOUNDS)]
    return row
