"""Logging: every death with its cause, plus a per-tick population summary.

Graphs of these numbers show emergence long before you can see it on screen.
"""

import csv
from collections import Counter
from pathlib import Path


class Stats:
    def __init__(self):
        self.deaths: list[dict] = []
        self.ticks: list[dict] = []
        self.meals = Counter()

    def record_meal(self, agent, kind: str):
        self.meals[kind] += 1

    def record_death(self, agent, tick: int):
        self.deaths.append({
            "tick": tick,
            "agent": agent.id,
            "age": agent.age,
            "cause": agent.cause_of_death,
            "x": agent.x,
            "y": agent.y,
        })

    def record_tick(self, sim):
        living = sim.living
        plants = sim.world.plant_counts()
        self.ticks.append({
            "tick": sim.tick_count,
            "population": len(living),
            "food_plants": plants["food"],
            "poison_plants": plants["poison"],
            "avg_energy": round(sum(a.energy for a in living) / len(living), 2) if living else 0,
            "avg_water": round(sum(a.water for a in living) / len(living), 2) if living else 0,
        })

    def deaths_by_cause(self) -> Counter:
        return Counter(d["cause"] for d in self.deaths)

    def summary(self) -> str:
        lines = [f"Deaths: {len(self.deaths)}"]
        for cause, count in self.deaths_by_cause().most_common():
            lines.append(f"  {cause}: {count}")
        lines.append(f"Meals: food {self.meals['food']}, poison {self.meals['poison']}")
        if self.deaths:
            avg_age = sum(d["age"] for d in self.deaths) / len(self.deaths)
            lines.append(f"Average age at death: {avg_age:.0f} ticks")
        return "\n".join(lines)

    def save(self, folder: Path):
        folder.mkdir(parents=True, exist_ok=True)
        for name, rows in (("deaths.csv", self.deaths), ("ticks.csv", self.ticks)):
            if not rows:
                continue
            with open(folder / name, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
                writer.writeheader()
                writer.writerows(rows)
