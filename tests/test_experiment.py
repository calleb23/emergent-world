import json
import os
import subprocess
import sys

import numpy as np
import pytest

from emergent_world import experiment
from emergent_world.config import TICKS_PER_DAY, Config
from emergent_world.metrics import Recorder
from emergent_world.sim import Simulation


def test_overrides_are_typed_and_unknown_keys_refused():
    o = experiment.parse_overrides(["imitation=False", "learn_rate=0.02", "initial_agents=12",
                                    "lifespan=[100, 200]"])
    assert o == {"imitation": False, "learn_rate": 0.02, "initial_agents": 12, "lifespan": (100, 200)}
    with pytest.raises(ValueError):
        experiment.parse_overrides(["no_such_thing=1"])
    with pytest.raises(ValueError):
        experiment.parse_overrides(["imitation=maybe"])


def test_seeds_are_reproducible_and_distinct():
    assert experiment.seeds_for(0, 4) == experiment.seeds_for(0, 4)
    assert len(set(experiment.seeds_for(0, 8))) == 8
    assert experiment.seeds_for(0, 4) != experiment.seeds_for(1, 4)


def _job(seed, days=8):
    return {"index": 0, "seed": seed, "ticks": days * TICKS_PER_DAY, "overrides": {}}


def test_same_seed_same_world_different_seed_different_world():
    a, b, c = experiment.run_one(_job(5)), experiment.run_one(_job(5)), experiment.run_one(_job(6))
    assert a["fingerprint"] == b["fingerprint"] != c["fingerprint"]


def test_worlds_match_across_processes_with_different_hash_seeds():
    code = ("import json,sys; from emergent_world import experiment as e; "
            "print(e.run_one({'index':0,'seed':3,'ticks':6*24,'overrides':{}})['fingerprint'])")
    prints = []
    for hash_seed in ("1", "2"):
        env = dict(os.environ, PYTHONHASHSEED=hash_seed)
        out = subprocess.run([sys.executable, "-c", code], cwd=experiment.ROOT, env=env,
                             capture_output=True, text=True, check=True)
        prints.append(out.stdout.strip().splitlines()[-1])
    assert prints[0] == prints[1]


def test_batch_writes_manifest_rows_and_summary_and_workers_do_not_matter(tmp_path):
    one = experiment.run_batch("t", 2, 4 / 365, {}, workers=1, out_root=tmp_path / "a")
    two = experiment.run_batch("t", 2, 4 / 365, {}, workers=2, out_root=tmp_path / "b")
    manifest = json.loads((one / "manifest.json").read_text())
    assert manifest["seeds"] and "commit" in manifest and "config" in manifest
    assert (one / "seed_0.jsonl").read_text().count("\n") >= 3
    fa = [r["fingerprint"] for r in experiment.load_summary(one)]
    fb = [r["fingerprint"] for r in experiment.load_summary(two)]
    assert fa == fb


def test_life_expectancy_extinction_and_discovery_timing():
    sim = Simulation(Config(initial_agents=2, min_population=0, climate=False, newcomer_every_days=0), seed=0)
    rec = Recorder(sim)
    sim.tick_count = 48
    sim.chronicle("x", once="made fire")
    a, b = sim.agents
    a.age, b.age = 24, 72   # a was born during the run, b before it
    sim._kill(a, "dehydration")
    sim._kill(b, "starvation")
    sim.agents = []
    rec.sample(sim)
    s = rec.summary(sim)
    assert s["life_expectancy_days"] == 1.0
    assert s["extinct"] and s["extinct_day"] == 2
    assert s["share_dehydration"] == 0.5 and s["day_fire_by_rubbing"] == 2.0


def test_comparison_flags_a_real_shift_and_not_noise():
    rng = np.random.default_rng(0)
    base = [{"alive_mean": float(v)} for v in rng.normal(10, 1, 8)]
    same = [{"alive_mean": float(v)} for v in rng.normal(10, 1, 8)]
    up = [{"alive_mean": float(v)} for v in rng.normal(15, 1, 8)]
    assert experiment.compare(base, up, ["alive_mean"])[0]["clear"]
    assert not experiment.compare(base, base, ["alive_mean"])[0]["clear"]
    md = experiment.table_markdown(experiment.compare(base, same, ["alive_mean"]))
    assert "alive_mean" in md
