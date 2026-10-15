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


def test_checkpoint_resumes_exactly(tmp_path):
    from emergent_world import checkpoint
    straight = Simulation(experiment.make_config({}), seed=4)
    for _ in range(72):
        straight.tick()
    paused = Simulation(experiment.make_config({}), seed=4)
    for _ in range(36):
        paused.tick()
    path = checkpoint.save(paused, tmp_path / "w.ckpt")
    assert checkpoint.header(path)["tick"] == 36
    resumed = checkpoint.load(path)
    for _ in range(36):
        resumed.tick()
    assert (resumed.world.plants == straight.world.plants).all()
    assert [(a.id, a.x, a.y, round(a.health, 6)) for a in resumed.agents] == \
           [(a.id, a.x, a.y, round(a.health, 6)) for a in straight.agents]
    assert resumed.history == straight.history
    assert path.stat().st_size < 20e6


def test_a_batch_can_fork_from_saved_worlds(tmp_path):
    first = experiment.run_batch("a", 2, 3 / 365, {}, workers=1, out_root=tmp_path, save_end=True)
    fork = experiment.run_batch("b", 2, 2 / 365, {"imitation": False}, workers=1, out_root=tmp_path,
                                resume_from=first)
    rows = experiment.load_summary(fork)
    assert all(r["days"] == 5 for r in rows)


def test_behaviour_ecology_and_made_activity_metrics():
    sim = Simulation(experiment.make_config({}), seed=2)
    rec = Recorder(sim)
    flake = sim.config.item_id("sharp flake")
    for t in range(40 * TICKS_PER_DAY):
        sim.tick()
        if t % TICKS_PER_DAY == 0:
            sim.world.plants[0, 0] = flake if sim.world.terrain[0, 0] == 0 else sim.world.plants[0, 0]
        rec.sample(sim)
    s = rec.summary(sim)
    assert 0 < s["action_entropy_bits"] <= 4.0
    assert 0 <= s["share_doing"] <= 1
    assert s["made_kinds_ever"] >= 1 and s["made_activity_total"] > 0
    assert "cv_food" in s and s["species_lost"] >= 0
