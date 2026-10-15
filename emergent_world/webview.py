"""What the browser view needs to know, shared by the live server and replays.

The page (viewer.html) draws whatever state it's handed: the map, the people on
it, the weather, and one followed person's record. Live mode fetches that state
from a running simulation; replay mode rebuilds it from a recording.
"""

from pathlib import Path

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
    }


def plant_string(world) -> str:
    return "".join(chr(48 + int(v)) for v in world.plants.T.flatten())


AGENT_FIELDS = 8  # id, x, y, energy %, water %, health %, rest %, asleep


def agent_rows(sim) -> list:
    c, rows = sim.config, []
    for a in sim.agents:
        if a.alive:
            rows += [a.id, a.x, a.y, round(100 * a.energy / c.max_energy),
                     round(100 * a.water / c.max_water), round(100 * a.health / c.max_health),
                     round(100 * (1 - a.fatigue)), int(a.asleep)]
    return rows


def climate_info(sim) -> dict:
    climate = sim.climate
    if climate is None:
        return {"weather": "clear", "temp": 18, "season": ""}
    return {"weather": climate.weather, "temp": round(climate.temperature), "season": climate.season}


def person(agent, now: int, sim=None) -> dict:
    """One agent's record: family, life events, and (live only) what they're wary of."""
    end = now if agent.alive else agent.events[-1][0]
    record = {
        "parent": agent.parent_id,
        "children": list(agent.offspring),
        "generation": agent.generation,
        "lifespan": agent.lifespan,
        "born": end - agent.age,
        "died": None if agent.alive else end,
        "cause": agent.cause_of_death,
        "events": [[t, text] for t, text in agent.events],
    }
    if sim is not None:
        record["wary"] = [[sim.config.look_of(color), round(level, 2)]
                          for color, level in sorted(agent.memory.aversion.items(), key=lambda kv: -kv[1])]
    return record
