"""Record a run into one self-contained web page you can open in any browser.

    python -m emergent_world.replay                 # 3 years, writes replay.html
    python -m emergent_world.replay --run-years 5 --seed 2

No pygame needed: open replay.html in a browser to play the run back, scrub
through time, and click any agent to read their life story. To watch a run as
it happens instead, use `python -m emergent_world.live`.
"""

import argparse
from pathlib import Path

from emergent_world.config import TICKS_PER_DAY, TICKS_PER_YEAR, Config
from emergent_world.sim import Simulation
from emergent_world.webview import agent_rows, climate_info, page, person, plant_string, static_info

FRAME_EVERY = 6        # ticks (hours) between recorded frames
KEYFRAME_DAYS = 10     # a full plant map every this many days; changes in between
WEATHER = ("clear", "cloudy", "rain", "storm", "fog", "snow")


def record(config: Config, seed: int, run_years: float, founders: str) -> dict:
    if Path(founders).exists():
        config.founders_path = founders
    sim = Simulation(config, seed=seed)
    sim.follow(max(sim.agents, key=lambda a: a.age, default=None))
    world = sim.world

    known = {}            # every agent that ever lived, by id
    frames = []           # [followed id, weather index, temperature, agent rows]
    keyframes = {}        # day -> full plant string
    plant_changes = []    # per day: [index, value, index, value, ...]
    previous = world.plants.T.flatten().copy()

    def snapshot():
        weather = climate_info(sim)
        frames.append([sim.followed_id if sim.followed_id is not None else -1,
                       WEATHER.index(weather["weather"]), weather["temp"], agent_rows(sim)])

    for a in sim.agents:
        known[a.id] = a
    keyframes[0] = plant_string(world)
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
                keyframes[day] = plant_string(world)
                plant_changes.append([])
            else:
                changed = (now != previous).nonzero()[0]
                plant_changes.append([int(v) for i in changed for v in (i, now[i])])
            previous = now.copy()

    data = static_info(sim, "replay")
    data.update({
        "frameEvery": FRAME_EVERY,
        "keyframeDays": KEYFRAME_DAYS,
        "weatherNames": WEATHER,
        "keyframes": keyframes,
        "plantChanges": plant_changes,
        "frames": frames,
        "people": {a.id: person(a, sim.tick_count) for a in known.values()},
    })
    return data


def write_page(data: dict, out: Path):
    out.write_text(page(data))


def main():
    parser = argparse.ArgumentParser(description="Record a run into replay.html")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--run-years", type=float, default=3.0)
    parser.add_argument("--years", type=float, default=2.0, help="average lifespan in years")
    parser.add_argument("--people", type=int, default=30)
    parser.add_argument("--max-people", type=int, default=80)
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
