"""Feelings the body produces, and what an observer would call each person's activity.

Nothing here makes anyone do anything. People act only through their brains
(move, eat, drink, rest, pick up, drop, give); this module works out what they
feel as a result, which their brains sense and learn from:

- Exposure: caught out in rain, a storm, snow or a cold night, away from any
  shelter, wears down health and burns energy. Being at a shelter stops it.
- Boredom: lingering in a small patch builds boredom; going somewhere new
  relieves it.
- Activity: a short label for the viewer, describing what someone is doing.
"""

ACTIVITIES = ("", "sleeping", "sheltering", "drinking", "eating", "picking something up",
              "striking something", "rubbing something",
              "putting something down", "giving something", "carrying something", "grieving",
              "following a parent", "looking for water", "looking for food", "resting",
              "wandering", "out in the weather")


def exposed(sim, agent) -> bool:
    """Caught out in the weather: rain, storm or snow, or a cold night, away from shelter."""
    climate = sim.climate
    if climate is None:
        return False
    if sim.world.shelter_near(agent.x, agent.y, 1) is not None:
        return False
    if climate.weather in ("rain", "storm", "snow"):
        return True
    cold_night = climate.is_night and climate.temperature < 6
    from emergent_world.world.physics import fire_near
    return cold_night and not fire_near(sim.world, agent.x, agent.y)   # a fire keeps you warm


def update_boredom(sim, agent) -> None:
    """Lingering in a small patch builds boredom; covering new ground eases it."""
    c = sim.config
    agent.recent.append((agent.x, agent.y))
    if len(agent.recent) > c.boredom_window:
        agent.recent.pop(0)
    if len(agent.recent) < c.boredom_window:
        return
    spread = len(set(agent.recent))
    if spread < c.boredom_window // 6:
        agent.boredom = min(1.0, agent.boredom + c.boredom_rise)
    else:
        agent.boredom = max(0.0, agent.boredom - c.boredom_ease)


def after_action(sim, agent) -> None:
    """Notice shelters close by, and update boredom."""
    spot = sim.world.shelter_near(agent.x, agent.y, 1)
    if spot is not None:
        agent.memory.shelter_at = spot
    update_boredom(sim, agent)


def describe(sim, agent, action) -> str:
    """A short label for what the person is doing right now."""
    c = sim.config
    if agent.asleep:
        return "sheltering" if sim.world.shelter_near(agent.x, agent.y, 1) else "sleeping"
    name = getattr(action, "name", "")
    labels = {"DRINK": "drinking", "EAT": "eating", "PICK_UP": "picking something up",
              "DROP": "putting something down", "GIVE": "giving something",
              "STRIKE": "striking something", "RUB": "rubbing something"}
    if name in labels:
        return labels[name]
    if agent.grief:
        return "grieving"
    if exposed(sim, agent):
        return "out in the weather"
    if agent.hands:
        return "carrying something"
    if agent.age < c.maturity_age:
        return "following a parent"
    if agent.water < 0.4 * c.max_water:
        return "looking for water"
    if agent.energy < 0.5 * c.max_energy:
        return "looking for food"
    if name == "REST":
        return "resting"
    return "wandering"
