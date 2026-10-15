"""Logging: every death and birth, plus a per-tick population summary.

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
        self.births = 0
        self.reseeded = 0
        # Snapshot for progress_line, so each line reports only its own window.
        self._window = {"deaths": 0, "meals": Counter(), "births": 0, "reseeded": 0}

    def record_meal(self, agent, kind: str):
        self.meals[kind] += 1

    def record_birth(self, agent):
        self.births += 1

    def record_death(self, agent, tick: int):
        self.deaths.append({
            "tick": tick,
            "agent": agent.id,
            "generation": agent.generation,
            "age": agent.age,
            "children": agent.children,
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
            "max_generation": max((a.generation for a in living), default=0),
            "food_plants": plants["food"],
            "poison_plants": plants["poison"],
            "avg_energy": round(sum(a.energy for a in living) / len(living), 2) if living else 0,
            "avg_water": round(sum(a.water for a in living) / len(living), 2) if living else 0,
            "births": self.births,
            "reseeded": self.reseeded,
            "food_meals": self.meals["food"],
            "poison_meals": self.meals["poison"],
        })

    def deaths_by_cause(self) -> Counter:
        return Counter(d["cause"] for d in self.deaths)

    def progress_line(self, sim) -> str:
        """One line summarising the window since the previous call."""
        w = self._window
        deaths = self.deaths[w["deaths"]:]
        meals = self.meals - w["meals"]
        births = self.births - w["births"]
        reseeded = self.reseeded - w["reseeded"]
        self._window = {"deaths": len(self.deaths), "meals": Counter(self.meals),
                        "births": self.births, "reseeded": self.reseeded}

        living = sim.living
        avg_age = sum(d["age"] for d in deaths) / len(deaths) if deaths else 0
        eaten = meals["food"] + meals["poison"]
        poison_meal_share = meals["poison"] / eaten if eaten else 0
        plants = sim.world.plant_counts()
        total_plants = plants["food"] + plants["poison"]
        poison_plant_share = plants["poison"] / total_plants if total_plants else 0
        causes = Counter(d["cause"] for d in deaths)
        cause_text = " ".join(f"{k}={v}" for k, v in causes.most_common())
        return (f"tick {sim.tick_count:>6} | difficulty {sim.difficulty:.2f} | pop {len(living):>3} | "
                f"gen {max((a.generation for a in living), default=0):>3} | "
                f"born {births:>4} reseeded {reseeded:>4} | "
                f"age at death {avg_age:>5.0f} | "
                f"poison meals {poison_meal_share:>5.1%} (plants {poison_plant_share:.1%}) | "
                f"{cause_text}")

    def summary(self) -> str:
        lines = [f"Deaths: {len(self.deaths)}  Births: {self.births}  Reseeded: {self.reseeded}"]
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
