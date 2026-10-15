import numpy as np

from emergent_world.agents.brain import Brain
from emergent_world.config import TICKS_PER_DAY, Config, days, format_time, years
from emergent_world.prehistory import load_founders, save_founders
from emergent_world.sim import Simulation


def test_clock_is_hourly():
    assert TICKS_PER_DAY == 24
    assert days(10) == 240
    assert years(1) == 8760
    assert format_time(0) == "year 1, day 1"
    assert format_time(years(1) + days(2)) == "year 2, day 3"


def test_life_stages_scale_with_lifespan():
    short = Config()
    long = Config().with_lifespan_years(2)
    assert long.average_lifespan > 15 * short.average_lifespan
    ratio_short = short.maturity_age / short.average_lifespan
    ratio_long = long.maturity_age / long.average_lifespan
    assert abs(ratio_short - ratio_long) < 0.01
    assert long.reproduce_cooldown > short.reproduce_cooldown


def test_body_needs_do_not_depend_on_lifespan():
    assert Config().water_drain == Config().with_lifespan_years(50).water_drain


def test_world_starts_from_founders_at_mixed_ages(tmp_path):
    rng = np.random.default_rng(0)
    founders = [Brain.random(rng) for _ in range(30)]
    path = tmp_path / "founders.npz"
    save_founders(founders, path, generations=12)
    loaded = load_founders(path)
    assert len(loaded) == 30
    assert np.array_equal(loaded[3].w2, founders[3].w2)

    config = Config(founders_path=str(path)).with_lifespan_years(2)
    sim = Simulation(config, seed=0)
    assert len(sim.agents) == 30
    assert len({a.age for a in sim.agents}) > 20  # not all the same age
    assert all(a.age < a.lifespan for a in sim.agents)


def test_replay_records_a_short_run(tmp_path):
    import json
    from emergent_world.replay import record, write_page
    config = Config.small_world(people=4, max_people=10).with_lifespan_years(0.2)
    data = record(config, seed=0, run_years=0.05, founders="founders.npz")
    assert len(data["frames"]) > 50
    assert data["people"] and all("events" in p for p in data["people"].values())
    out = tmp_path / "replay.html"
    write_page(data, out)
    page = out.read_text()
    assert "/*VIEWER_DATA*/null" not in page
    start = page.index("const DATA = ") + len("const DATA = ")
    assert json.loads(page[start:page.index(";\n", start)])["seed"] == 0
