"""Run a world for a long time and summarise it, year by year.

    python -m emergent_world.century                # 100 years, seed 0
    python -m emergent_world.century --years 50 --seed 3

Prints a line per year, and writes century.json (yearly figures and the world's
history) plus century_replay.html, a replay of the final two years.
"""

import argparse
import json
import time
from collections import Counter
from pathlib import Path

from emergent_world.config import TICKS_PER_YEAR, Config
from emergent_world.replay import record, write_page
from emergent_world.sim import Simulation


def count_events(agents, phrase: str) -> int:
    return sum(1 for a in agents for _, text in a.events if phrase in text)


def run(years: int, seed: int, founders: str, replay_years: float, out_dir: Path) -> dict:
    config = Config.small_world()
    if Path(founders).exists():
        config.founders_path = founders
    sim = Simulation(config, seed=seed)
    sim.follow(max(sim.agents, key=lambda a: a.age, default=None))
    from emergent_world.metrics import Recorder
    recorder = Recorder(sim)

    yearly = []
    everyone = {a.id: a for a in sim.agents}
    deaths_before, births_before = Counter(), 0
    started = time.time()
    main_years = max(0, years - replay_years)
    for year in range(1, int(main_years) + 1):
        alive_samples, mood_samples = [], []
        for hour in range(TICKS_PER_YEAR):
            sim.tick()
            recorder.sample(sim)
            if hour % 24 == 0:
                alive_samples.append(len(sim.agents))
                mood_samples += [a.mood for a in sim.agents]
                for a in sim.agents:
                    everyone.setdefault(a.id, a)
            if not sim.living:
                break
        deaths = sim.stats.deaths_by_cause()
        new_deaths = deaths - deaths_before
        deaths_before = Counter(deaths)
        living = sim.agents
        row = {
            "year": year,
            "alive_avg": round(sum(alive_samples) / max(1, len(alive_samples)), 1),
            "alive_end": len(living),
            "births": sim.stats.births - births_before,
            "deaths": dict(new_deaths),
            "oldest_days": max((a.age // 24 for a in living), default=0),
            "max_generation": max((a.generation for a in living), default=0),
            "lines": len({a.line for a in living}),
            "shelters": int(sim.world.shelter.sum()),
            "stick_piles": int((sim.world.piles > 0).sum()),
            "mood": round(sum(mood_samples) / max(1, len(mood_samples)), 3),
            "aversion_gene": round(sum(a.aversion_gain for a in living) / max(1, len(living)), 2),
            "cugs": int((sim.world.plants == config.item_id("cug")).sum()),
            "fires": int((sim.world.fire > 0).sum()),
        }
        births_before = sim.stats.births
        yearly.append(row)
        took = time.time() - started
        print(f"year {year:>3} | alive {row['alive_end']:>3} (avg {row['alive_avg']:>5}) | born {row['births']:>3} | "
              f"oldest {row['oldest_days']:>4}d | gen {row['max_generation']:>3} | lines {row['lines']:>2} | "
              f"shelters {row['shelters']} piles {row['stick_piles']:>3} | mood {row['mood']:+.2f} | "
              f"deaths {row['deaths']} | {took / 60:.0f} min", flush=True)
        if not sim.living:
            print("Everyone has died.")
            break
        if year % 10 == 0:
            from emergent_world import checkpoint
            checkpoint.save(sim, out_dir / "century.ckpt", note=f"year {year}")

    totals = {
        "gifts": count_events(everyone.values(), "Gave a"),
        "pickups": count_events(everyone.values(), "Picked up"),
        "children_with_partner": count_events(everyone.values(), "Had a child with"),
        "people_ever": len(everyone),
    }
    summary = {"seed": seed, "years": years, "yearly": yearly, "totals": totals,
               "metrics": recorder.summary(sim),
               "history": [[t, text] for t, text in sim.history]}
    (out_dir / "century.json").write_text(json.dumps(summary))
    print("Totals:", totals)

    if sim.living and replay_years > 0:
        print(f"Recording the final {replay_years:g} years...", flush=True)
        data = record(config, seed, replay_years, founders, sim=sim)
        write_page(data, out_dir / "century_replay.html")
        summary["history"] = [[t, text] for t, text in sim.history]
        (out_dir / "century.json").write_text(json.dumps(summary))
        print("Wrote century_replay.html")
    return summary


def main():
    parser = argparse.ArgumentParser(description="Run a world for a long time and summarise it")
    parser.add_argument("--years", type=int, default=100)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--founders", default="founders.npz")
    parser.add_argument("--replay-years", type=float, default=2.0)
    parser.add_argument("--out", default=".")
    args = parser.parse_args()
    run(args.years, args.seed, args.founders, args.replay_years, Path(args.out))


if __name__ == "__main__":
    main()
