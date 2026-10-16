"""Measuring a run: a daily sample of the world, and a summary at the end.

Metrics only read the simulation; they never change it. A run's daily samples
also give it a fingerprint (a hash), so two runs can be checked for being
exactly the same.
"""

import hashlib
import json
from collections import Counter

import numpy as np

from emergent_world.config import TICKS_PER_DAY
from emergent_world.agents.emotions import TRAITS

# World firsts worth timing: chronicle keys (or their prefix) -> a short name.
DISCOVERIES = {
    "made/sharp flake": "flake",
    "made fire": "fire_by_rubbing",
    "spark fire": "fire_by_sparks",
    "made/cracked nut": "cracked_nut",
    "shelter": "shelter",
    "made/corded stick": "corded_stick",
    "made/cord": "cord",
    "made/spear": "spear",
    "made/bow": "bow",
    "made/snare": "snare",
    "made/stone hammer": "stone_hammer",
    "fished": "fish",
    "carried water": "carried_water",
    "stoked": "stoked_fire",
    "copied/": "first_transmission",
    "gave": "first_gift",
    "theft": "first_theft",
    "violence": "first_violence",
    "killing": "first_killing",
}


ACTIVITY_THRESHOLD = 30   # person- or tile-days a made thing must accumulate to count as established


class Recorder:
    """Call `sample(sim)` every tick (it acts once a day) and `summary(sim)` at the end."""

    def __init__(self, sim):
        self.rows: list[dict] = []
        self.peak = 0
        self._groups = {}
        # Made things: kinds only physics or hands produce (tools, cooked food, cord...).
        # Their daily presence is the "evolutionary activity" of the world's technology.
        self._made = [i for i, k in enumerate(sim.config.items, start=1) if not k.spawns]
        self._species = {k.look: i for i, k in enumerate(sim.config.items, start=1) if k.wanders}
        self.made_activity = np.zeros(len(sim.config.items) + 1, dtype=np.int64)
        self.made_first_established: dict[int, int] = {}
        for i, k in enumerate(sim.config.items, start=1):
            group = ("predator" if k.bites and k.wanders else "critter" if k.wanders
                     else "poison" if k.harmful else "food" if k.edible else None)
            if group:
                self._groups.setdefault(group, []).append(i)

    def sample(self, sim) -> None:
        if sim.tick_count % TICKS_PER_DAY:
            return
        people = [a for a in sim.agents if a.alive]
        n = len(people)
        self.peak = max(self.peak, n)
        counts = np.bincount(sim.world.plants.ravel(), minlength=len(sim.config.items) + 1)

        def mean(attr):
            return round(float(np.mean([getattr(a, attr) for a in people])), 4) if n else 0.0
        row = {
            "day": sim.tick_count // TICKS_PER_DAY,
            "alive": n,
            "births": sim.stats.births,
            "deaths": len(sim.stats.deaths),
            "energy": mean("energy"), "water": mean("water"), "health": mean("health"),
            "mood": mean("mood"), "fear": mean("fear"), "anger": mean("anger"),
            "loneliness": mean("loneliness"),
            "lines": len({a.line for a in people}),
            "max_generation": max((a.generation for a in people), default=0),
            "shelters": int(sim.world.shelter.sum()),
            "fires": int((sim.world.fire > 0).sum()),
        }
        for group, ids in self._groups.items():
            row[group] = int(counts[ids].sum())
        held = np.bincount([a.hands for a in people], minlength=len(counts)) if people else np.zeros_like(counts)
        present = counts + held
        made_now = [i for i in self._made if present[i] > 0]
        self.made_activity[made_now] += present[made_now]
        for i in made_now:
            if i not in self.made_first_established and self.made_activity[i] >= ACTIVITY_THRESHOLD:
                self.made_first_established[i] = row["day"]
        row["made_kinds"] = len(made_now)
        row["established_made"] = len(self.made_first_established)
        for look, i in self._species.items():
            row["n_" + look.replace(" ", "_")] = int(counts[i])
        self.rows.append(row)

    def fingerprint(self) -> str:
        return hashlib.sha256(json.dumps(self.rows, sort_keys=True).encode()).hexdigest()[:16]

    def summary(self, sim) -> dict:
        deaths = sim.stats.deaths
        born_here = [d for d in deaths if d["tick"] - d["age"] >= 0]
        causes = Counter(d["cause"] for d in deaths)
        total = max(1, len(deaths))
        people = [a for a in sim.agents if a.alive]
        alive_series = [r["alive"] for r in self.rows] or [0]
        person_years = sum(alive_series) / 365.0
        extinct_day = next((r["day"] for r in self.rows if r["alive"] == 0), None)
        floor = max(sim.config.min_population, 0)
        last_year = alive_series[-365:]
        half = len(self.rows) // 2
        if half and len(self.rows) > half + 1:
            a, b = self.rows[half], self.rows[-1]
            years = max((b["day"] - a["day"]) / 365.0, 1e-9)
            net_late = round(((b["births"] - a["births"]) - (b["deaths"] - a["deaths"])) / years, 2)
        else:
            net_late = None
        out = {
            "days": sim.tick_count // TICKS_PER_DAY,
            # Viability: top-ups keep at least `min_population` alive, which can hide a collapse.
            "floor_share": round(float(np.mean([n <= floor for n in alive_series])), 4),
            "alive_last_year": round(float(np.mean(last_year)), 2),
            "net_growth_late": net_late,   # births minus deaths per year, second half of the run
            "alive_end": len(people),
            "alive_mean": round(float(np.mean(alive_series)), 2),
            "alive_min": int(min(alive_series)),
            "peak": self.peak,
            "extinct": extinct_day is not None,
            "extinct_day": extinct_day,
            "births": sim.stats.births,
            "births_per_person_year": round(sim.stats.births / max(person_years, 1e-9), 3),
            "life_expectancy_days": round(float(np.mean([d["age"] for d in born_here])) / TICKS_PER_DAY, 1)
            if born_here else None,
            "deaths": len(deaths),
            "max_generation": max([a.generation for a in people] + [d["generation"] for d in deaths] + [0]),
            "mood_mean": round(float(np.mean([r["mood"] for r in self.rows])), 4) if self.rows else 0.0,
            "fingerprint": self.fingerprint(),
        }
        for cause in ("dehydration", "starvation", "poison", "old_age", "exposure", "bites", "violence",
                      "thorns", "fire", "stings"):
            out[f"share_{cause}"] = round(causes[cause] / total, 4)
        for key in ("gift", "comfort", "hit", "theft", "call", "transmission", "taught", "call_answered", "call_helped"):
            out[f"count_{key}"] = int(sim.counts[key])
        for prefix, name in DISCOVERIES.items():
            ticks = [t for k, t in sim.first_ticks.items() if k == prefix or (prefix.endswith("/") and k.startswith(prefix))]
            out[f"day_{name}"] = round(min(ticks) / TICKS_PER_DAY, 1) if ticks else None
        out["discoveries"] = sum(1 for name in DISCOVERIES.values() if out[f"day_{name}"] is not None)
        out["genome_diversity"] = genome_diversity(people)
        out.update(behaviour_metrics(sim))
        out.update(signal_metrics(sim))
        from emergent_world.agents.genes import GENES
        for g in GENES:
            vals = [a.genes[g] for a in people if a.genes]
            # log-ratio of the living's geometric mean to the configured value: 0 = unchanged
            out[f"gene_{g}_logratio"] = round(float(np.mean(np.log(vals)) - np.log(getattr(sim.config, g))), 4) \
                if vals else None
            out[f"gene_{g}_sd"] = round(float(np.std(np.log(vals))), 4) if vals else None
        out.update(self.ecology_metrics())
        shelters = [r["shelters"] for r in self.rows] or [0]
        out["shelters_max"] = int(max(shelters))
        out["shelters_last_year"] = round(float(np.mean(shelters[-365:])), 2)
        out["made_kinds_ever"] = int((self.made_activity > 0).sum())
        out["established_made"] = len(self.made_first_established)
        out["made_activity_total"] = int(self.made_activity.sum())
        half = (self.rows[-1]["day"] // 2) if self.rows else 0
        out["new_established_late"] = sum(1 for d in self.made_first_established.values() if d > half)
        for t in TRAITS:
            values = [a.traits.get(t, 0.5) for a in people if a.traits]
            out[f"trait_{t}_mean"] = round(float(np.mean(values)), 4) if values else None
            out[f"trait_{t}_sd"] = round(float(np.std(values)), 4) if values else None
        return out


    def ecology_metrics(self) -> dict:
        """How steady the world's stocks are, and which species died out."""
        out = {}
        if len(self.rows) < 2:
            return out
        for key in ("food", "critter", "predator"):
            series = np.array([r.get(key, 0) for r in self.rows], dtype=float)
            out[f"cv_{key}"] = round(float(series.std() / series.mean()), 4) if series.mean() > 0 else None
        gone = [k[2:] for k in self.rows[0] if k.startswith("n_")
                and self.rows[0][k] > 0 and self.rows[-1][k] == 0]
        out["species_lost"] = len(gone)
        out["species_lost_names"] = gone
        return out


def behaviour_metrics(sim) -> dict:
    """How varied people's actions are, and how often skilled actions did something."""
    from emergent_world.agents.agent import Action
    counts = np.array([sim.action_counts[int(a)] for a in Action], dtype=float)
    total = counts.sum()
    out = {"actions_total": int(total)}
    if total:
        p = counts[counts > 0] / total
        out["action_entropy_bits"] = round(float(-(p * np.log2(p)).sum()), 4)
        moves = counts[[Action.NORTH, Action.SOUTH, Action.EAST, Action.WEST, Action.REST]].sum()
        out["share_doing"] = round(float(1 - moves / total), 4)   # anything but walking or resting
    effects = {k[7:]: v for k, v in sim.counts.items() if k.startswith("effect_")}
    out["skill_effects"] = int(sum(effects.values()))
    for name in ("strike", "rub", "drop", "pick_up", "give"):
        out[f"effect_{name}"] = int(effects.get(name, 0))
    return out


def mutual_information(pairs: Counter) -> float:
    """Bits of information a sound gives about the situation, from (sound, situation) counts."""
    total = sum(pairs.values())
    if not total:
        return 0.0
    sounds, contexts = Counter(), Counter()
    for (s, c), n in pairs.items():
        sounds[s] += n
        contexts[c] += n
    mi = 0.0
    for (s, c), n in pairs.items():
        p = n / total
        mi += p * np.log2(p / (sounds[s] / total * contexts[c] / total))
    return float(mi)


def shuffled_mi(pairs: Counter, rng, permutations: int = 200) -> tuple:
    """The same measure with sounds shuffled against situations: what chance alone
    gives for this many calls. Returns (mean, 95th percentile)."""
    sounds = np.array([s for (s, c), n in pairs.items() for _ in range(n)])
    contexts = [c for (s, c), n in pairs.items() for _ in range(n)]
    if len(sounds) < 2:
        return 0.0, 0.0
    values = []
    for _ in range(permutations):
        shuffled = rng.permutation(sounds)
        values.append(mutual_information(Counter(zip(shuffled.tolist(), contexts))))
    return float(np.mean(values)), float(np.percentile(values, 95))


def signal_metrics(sim, seed: int = 0) -> dict:
    """Do the three sounds carry meaning, and do listeners act on them?"""
    pairs = sim.call_log
    calls = sum(pairs.values())
    out = {"calls": int(calls)}
    if calls < 20:
        return out
    mi = mutual_information(pairs)
    chance, chance95 = shuffled_mi(pairs, np.random.default_rng(seed))
    out["signal_mi_bits"] = round(mi, 5)
    out["signal_mi_excess"] = round(mi - chance, 5)
    out["signal_meaningful"] = bool(mi > chance95)
    resp = sim.call_response
    heard_moves = sum(resp.values())
    if heard_moves:
        out["approach_after_call"] = round(sum(n for (s, toward), n in resp.items() if toward) / heard_moves, 4)
    return out


def genome_diversity(people, sample: int = 30) -> float | None:
    """Mean distance between the inherited brains of up to `sample` living people."""
    genomes = [a.genome for a in people if a.genome is not None][:sample]
    if len(genomes) < 2:
        return None
    flat = np.stack([np.concatenate([g.w1.ravel(), g.b1, g.w2.ravel(), g.b2]) for g in genomes])
    d = np.sqrt(((flat[:, None, :] - flat[None, :, :]) ** 2).sum(-1))
    return round(float(d[np.triu_indices(len(genomes), 1)].mean()), 4)
