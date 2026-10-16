"""What the browser view needs to know, shared by the live server and replays.

The page (viewer.html) draws whatever state it's handed: the map, the people on
it, the weather, and one followed person's record. Live mode fetches that state
from a running simulation; replay mode rebuilds it from a recording.
"""

from pathlib import Path

from emergent_world.behaviour import ACTIVITIES

PAGE = Path(__file__).with_name("viewer.html")


def page(data: dict) -> str:
    """The viewer page with `data` built in."""
    import json
    return PAGE.read_text().replace("/*VIEWER_DATA*/null", json.dumps(data, separators=(",", ":")))


def static_info(sim, mode: str) -> dict:
    """Things that never change during a run."""
    c, world = sim.config, sim.world
    return {
        "mode": mode,
        "seed": sim.seed,
        "width": world.width,
        "height": world.height,
        "ticksPerDay": 24,
        "visionRange": c.vision_range,
        "terrain": "".join(str(int(v)) for v in world.terrain.T.flatten()),  # row by row
        "items": [{"look": k.look, "color": k.color, "group": k.group,
                   "harmful": k.harmful, "edible": k.edible} for k in c.items],
        "lifespanYears": round(c.average_lifespan / (24 * 365), 1),
        "activities": list(ACTIVITIES),
        "agentFields": AGENT_FIELDS,
    }


def plant_string(world) -> str:
    return "".join(chr(48 + int(v)) for v in world.plants.T.flatten())


# id, x, y, energy %, water %, health %, rest %, asleep, what they're doing (index
# into ACTIVITIES), then fear, anger, loneliness and joy (0-10)
AGENT_FIELDS = 13


def agent_rows(sim) -> list:
    c, rows = sim.config, []
    index = {name: i for i, name in enumerate(ACTIVITIES)}
    for a in sim.agents:
        if a.alive:
            rows += [a.id, a.x, a.y, round(100 * a.energy / c.max_energy),
                     round(100 * a.water / c.max_water), round(100 * a.health / c.max_health),
                     round(100 * (1 - a.fatigue)), int(a.asleep), index.get(a.activity, 0),
                     round(10 * a.fear), round(10 * a.anger), round(10 * a.loneliness), round(10 * a.joy)]
    return rows


SOCIAL_KEYS = ("gift", "comfort", "hit", "theft", "taught", "transmission", "call_answered")


def counts_row(sim) -> list:
    """Running totals for a replay frame: births, deaths, then each of SOCIAL_KEYS."""
    return [sim.stats.births, len(sim.stats.deaths)] + [int(sim.counts[k]) for k in SOCIAL_KEYS]


def climate_info(sim) -> dict:
    climate = sim.climate
    if climate is None:
        return {"weather": "clear", "temp": 18, "season": ""}
    return {"weather": climate.weather, "temp": round(climate.temperature), "season": climate.season}


def person(agent, now: int, sim=None) -> dict:
    """One agent's record: family, life events, and (live only) what they're wary of."""
    end = now if agent.alive else agent.events[-1][0]
    record = {
        "name": agent.name,
        "line": agent.line,
        "sex": agent.sex,
        "parent": agent.parent_id,
        "otherParent": agent.other_parent_id,
        "children": list(agent.offspring),
        "generation": agent.generation,
        "lifespan": agent.lifespan,
        "born": end - agent.age,
        "died": None if agent.alive else end,
        "cause": agent.cause_of_death,
        "events": [[t, text] for t, text in agent.events],
        "personality": [[k, round(v, 2)] for k, v in agent.traits.items()],
    }
    if sim is not None:
        record["known"] = [[other_id, sim.by_id[other_id].name, round(bond, 2)]
                           for other_id, bond in sorted(agent.known.items(), key=lambda kv: -kv[1])[:8]
                           if other_id in sim.by_id]
        record["feelings"] = [["fear", round(agent.fear, 2)], ["anger", round(agent.anger, 2)],
                              ["loneliness", round(agent.loneliness, 2)], ["joy", round(agent.joy, 2)]]
        record["grudges"] = [[sim.by_id[i].name, round(v, 2)] for i, v in
                             sorted(agent.grudges.items(), key=lambda kv: -kv[1])[:5] if i in sim.by_id]
        record["wary"] = [[sim.config.look_of(color), round(level, 2)]
                          for color, level in sorted(agent.memory.aversion.items(), key=lambda kv: -kv[1])]
    return record


def world_stats(sim) -> dict:
    """The world so far, for the viewer's summary panel: births, deaths by cause,
    discoveries made, and how people have treated each other."""
    from emergent_world.metrics import DISCOVERIES
    causes = sim.stats.deaths_by_cause().most_common(5)
    found = []
    for prefix, name in DISCOVERIES.items():
        ticks = [t for k, t in sim.first_ticks.items() if k == prefix or (prefix.endswith("/") and k.startswith(prefix))]
        if ticks:
            found.append([name.replace("_", " "), min(ticks)])
    found.sort(key=lambda f: f[1])
    return {"births": sim.stats.births, "deaths": len(sim.stats.deaths),
            "causes": [[c.replace("_", " "), n] for c, n in causes], "discoveries": found,
            "social": {k: int(sim.counts[k]) for k in SOCIAL_KEYS}}


def history(sim, limit: int | None = None) -> list:
    rows = [[t, text] for t, text in sim.history]
    return rows[-limit:] if limit else rows


def world_marks(world) -> dict:
    """Fires, shelters and stick piles, as flat tile indices (row by row)."""
    def tiles(mask):
        xs, ys = mask.nonzero()
        return [int(y) * world.width + int(x) for x, y in zip(xs, ys)]
    return {"fires": tiles(world.fire > 0), "shelters": tiles(world.shelter),
            "piles": tiles((world.piles > 0) & ~world.shelter)}
