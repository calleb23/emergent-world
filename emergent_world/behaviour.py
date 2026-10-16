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
              "striking something", "rubbing something", "taking something", "fighting",
              "comforting someone", "calling out", "afraid", "lonely", "angry",
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
    held = sim.config.item(agent.hands)
    if held is not None and held.warm:
        return False   # wrapped in a pelt
    return cold_night and not fire_near(sim.world, agent.x, agent.y)   # a fire keeps you warm


def bad_weather(sim, agent) -> bool:
    """Rain, storm, snow or a cold night: weather worth sheltering from."""
    climate = sim.climate
    if climate is None:
        return False
    return climate.weather in ("rain", "storm", "snow") or (climate.is_night and climate.temperature < 6)


def remember_weather(sim, agent, out_in_it: bool) -> None:
    """Being snug in shelter in bad weather is worth remembering. So is seeing
    someone else snug while you're out in it: you want what they have."""
    if not bad_weather(sim, agent):
        return
    world, now = sim.world, sim.tick_count
    if not out_in_it:
        spot = world.shelter_near(agent.x, agent.y, 1)
        if spot is not None:
            agent.hippo.encode(now, spot[0], spot[1], "shelter", 0.7)
        return
    if not sim.config.emulation or agent.asleep:
        return
    reach = sim.vision_reach
    for other in sim.agents:
        if other is agent or not other.alive or max(abs(other.x - agent.x), abs(other.y - agent.y)) > reach:
            continue
        spot = world.shelter_near(other.x, other.y, 1)
        if spot is not None:
            agent.hippo.encode(now, spot[0], spot[1], "shelter", 1.0, who=other.id)
            agent.shelter_want = min(1.0, agent.shelter_want + 0.2)
            sim._first(agent, ("envied shelter",), f"Out in the weather, saw {other.name} snug under cover, and wanted that")
            sim.chronicle(f"{label_of(agent)}, out in the weather, saw {other.name} sheltering and wanted that",
                          once="envied shelter")
            break


def label_of(agent) -> str:
    from emergent_world.agents.names import label
    return label(agent)


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
    # Shelters they can see are remembered (nearest first), and so are the ones beside them.
    spot = sim.world.shelter_near(agent.x, agent.y, 1) or sim.world.shelter_near(agent.x, agent.y, sim.vision_reach)
    if spot is not None:
        if agent.memory.shelter_at is None:
            sim._first(agent, ("saw shelter",), "Saw a shelter, and remembered where it was")
        agent.memory.shelter_at = spot
    world = sim.world
    if spot is not None and sim.config.hippocampus:
        agent.hippo.encode(sim.tick_count, spot[0], spot[1], "shelter", 0.4)
    if sim.config.hippocampus and (sim.tick_count + agent.id) % 4 == 0:
        # Recall, cued by need: the best remembered water, food and shelter from here.
        agent.hippo_now = sim.tick_count
        agent.hippo.refresh(agent.x, agent.y, sim.tick_count)
        for need, slot in (("water", "water_at"), ("food", "food_at"), ("shelter", "shelter_at")):
            found = agent.hippo.recalled.get(need)
            if found is not None:
                setattr(agent.memory, slot, (found[0], found[1]))
    if sim.config.teaching and agent.age < sim.config.maturity_age:
        # A child kept close is shown the places its parent knows.
        for pid in (agent.parent_id, agent.other_parent_id):
            parent = sim.by_id.get(pid)
            if parent is None or not parent.alive or max(abs(parent.x - agent.x), abs(parent.y - agent.y)) > 2:
                continue
            for place in ("water_at", "food_at", "shelter_at"):
                if getattr(agent.memory, place) is None and getattr(parent.memory, place) is not None:
                    setattr(agent.memory, place, getattr(parent.memory, place))
                    sim._first(agent, ("shown", place), f"{parent.name} showed them where to find "
                               + {"water_at": "water", "food_at": "food", "shelter_at": "shelter"}[place])
            if sim.config.hippocampus and (sim.tick_count + agent.id) % 24 == 0:
                now = sim.tick_count
                for kind in ("water", "food", "shelter"):
                    if not any(e.kind == kind for e in agent.hippo.episodes):
                        for e in parent.hippo.best(kind, now, 2):
                            agent.hippo.encode(now, e.x, e.y, kind, 0.8 * parent.hippo.strength(e, now),
                                               who=parent.id)
    if sim.config.remember_seen_water and world.shore_distance[agent.x, agent.y] <= sim.vision_reach:
        agent.memory.water_at = tuple(int(v) for v in world.nearest_shore[agent.x, agent.y])
        if sim.config.hippocampus:
            sx, sy = agent.memory.water_at
            agent.hippo.encode(sim.tick_count, sx, sy, "water", 0.5)
    update_boredom(sim, agent)


def describe(sim, agent, action) -> str:
    """A short label for what the person is doing right now."""
    c = sim.config
    if agent.asleep:
        return "sheltering" if sim.world.shelter_near(agent.x, agent.y, 1) else "sleeping"
    name = getattr(action, "name", "")
    labels = {"DRINK": "drinking", "EAT": "eating", "PICK_UP": "picking something up",
              "DROP": "putting something down", "GIVE": "giving something",
              "STRIKE": "striking something", "RUB": "rubbing something",
              "TAKE": "taking something", "HIT": "fighting", "COMFORT": "comforting someone",
              "CALL": "calling out", "CALL_B": "calling out", "CALL_C": "calling out"}
    if name in labels:
        return labels[name]
    if agent.grief:
        return "grieving"
    if exposed(sim, agent):
        return "out in the weather"
    if agent.fear > 0.5:
        return "afraid"
    if agent.anger > 0.5:
        return "angry"
    if agent.hands:
        return "carrying something"
    if agent.age < c.maturity_age:
        return "following a parent"
    if agent.water < 0.4 * c.max_water:
        return "looking for water"
    if agent.energy < 0.5 * c.max_energy:
        return "looking for food"
    if agent.loneliness > 0.6:
        return "lonely"
    if name == "REST":
        return "resting"
    return "wandering"
