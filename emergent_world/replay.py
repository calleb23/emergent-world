"""Record a run into one self-contained web page you can open in any browser.

    python -m emergent_world.replay                 # 3 years, writes replay.html
    python -m emergent_world.replay --run-years 5 --seed 2

No pygame needed: open replay.html in a browser to play the run back, scrub
through time, and click any agent to read their life story.
"""

import argparse
import json
from pathlib import Path

from emergent_world.config import TICKS_PER_DAY, TICKS_PER_YEAR, Config
from emergent_world.sim import Simulation

FRAME_EVERY = 6        # ticks (hours) between recorded frames
KEYFRAME_DAYS = 10     # a full plant map every this many days; changes in between
TEMPLATE = Path(__file__).with_name("replay_template.html")


def _plant_string(world) -> str:
    return "".join(str(int(v)) for v in world.plants.T.flatten())  # row by row


def record(config: Config, seed: int, run_years: float, founders: str) -> dict:
    if Path(founders).exists():
        config.founders_path = founders
    sim = Simulation(config, seed=seed)
    sim.follow(max(sim.agents, key=lambda a: a.age, default=None))
    world = sim.world

    known = {}            # every agent that ever lived, by id
    frames = []           # [followed id, [id, x, y, energy, water, health, ...]]
    keyframes = {}        # day -> full plant string
    plant_changes = []    # per day: [index, value, index, value, ...]
    previous = world.plants.T.flatten().copy()

    def snapshot():
        agents = []
        for a in sim.agents:
            if a.alive:
                agents += [a.id, a.x, a.y, round(100 * a.energy / config.max_energy),
                           round(100 * a.water / config.max_water),
                           round(100 * a.health / config.max_health)]
        frames.append([sim.followed_id if sim.followed_id is not None else -1, agents])

    for a in sim.agents:
        known[a.id] = a
    keyframes[0] = _plant_string(world)
    snapshot()
    total = int(run_years * TICKS_PER_YEAR)
    while sim.tick_count < total and sim.living:
        sim.tick()
        for a in sim.agents:
            known.setdefault(a.id, a)
        if sim.tick_count % FRAME_EVERY == 0:
            snapshot()
        if sim.tick_count % TICKS_PER_DAY == 0:
            day = sim.tick_count // TICKS_PER_DAY
            now = world.plants.T.flatten()
            if day % KEYFRAME_DAYS == 0:
                keyframes[day] = _plant_string(world)
                plant_changes.append([])
            else:
                changed = (now != previous).nonzero()[0]
                plant_changes.append([int(v) for i in changed for v in (i, now[i])])
            previous = now.copy()

    people = {}
    for a in known.values():
        # Tick the agent was born. Founders arrive part-way through life, so
        # their birth is before the run started (a negative tick).
        end = sim.tick_count if a.alive else a.events[-1][0]
        people[a.id] = {
            "parent": a.parent_id,
            "children": a.offspring,
            "generation": a.generation,
            "lifespan": a.lifespan,
            "born": end - a.age,
            "died": None if a.alive else end,
            "cause": a.cause_of_death,
            "events": [[t, text] for t, text in a.events],
        }

    return {
        "seed": seed,
        "width": world.width,
        "height": world.height,
        "frameEvery": FRAME_EVERY,
        "ticksPerDay": TICKS_PER_DAY,
        "keyframeDays": KEYFRAME_DAYS,
        "terrain": "".join(str(int(v)) for v in world.terrain.T.flatten()),
        "keyframes": keyframes,
        "plantChanges": plant_changes,
        "frames": frames,
        "people": people,
        "colors": {"food": config.food_color, "poison": config.poison_color},
        "looks": {"food": config.food_look, "poison": config.poison_look},
        "lifespanYears": round(config.average_lifespan / TICKS_PER_YEAR, 1),
    }


def write_page(data: dict, out: Path):
    page = TEMPLATE.read_text().replace("/*REPLAY_DATA*/null", json.dumps(data, separators=(",", ":")))
    out.write_text(page)


def main():
    parser = argparse.ArgumentParser(description="Record a run into replay.html")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--run-years", type=float, default=3.0)
    parser.add_argument("--years", type=float, default=2.0, help="average lifespan in years")
    parser.add_argument("--people", type=int, default=12)
    parser.add_argument("--max-people", type=int, default=40)
    parser.add_argument("--children", type=float, default=3.0)
    parser.add_argument("--founders", default="founders.npz")
    parser.add_argument("--out", default="replay.html")
    args = parser.parse_args()

    config = Config.small_world(args.people, args.max_people, args.children, args.years)
    data = record(config, args.seed, args.run_years, args.founders)
    write_page(data, Path(args.out))
    size = Path(args.out).stat().st_size / 1e6
    print(f"Recorded {len(data['frames'])} frames and {len(data['people'])} lives; "
          f"wrote {args.out} ({size:.1f} MB)")


if __name__ == "__main__":
    main()
