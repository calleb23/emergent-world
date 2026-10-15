"""Run batches of worlds and compare them, so changes are judged on evidence.

    python -m emergent_world.experiment run --name baseline --seeds 8 --years 2
    python -m emergent_world.experiment run --name no-imitation --set imitation=False
    python -m emergent_world.experiment compare runs/baseline/<stamp> runs/no-imitation/<stamp>
    python -m emergent_world.experiment verify

Each batch writes runs/<name>/<stamp>/: manifest.json (commit, config, seeds),
seed_<k>.jsonl (one line per simulated day) and summary.json (one entry per
seed). One world is far too noisy to judge a change by; compare batches.
"""

import argparse
import dataclasses
import json
import platform
import subprocess
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np

from emergent_world.config import TICKS_PER_DAY, TICKS_PER_YEAR, Config
from emergent_world.metrics import Recorder

ROOT = Path(__file__).resolve().parent.parent


# --- configuration -----------------------------------------------------------

def parse_overrides(pairs: list[str]) -> dict:
    """`key=value` strings into typed Config overrides. Unknown keys are refused."""
    fields = {f.name: f for f in dataclasses.fields(Config)}
    out = {}
    for pair in pairs or []:
        if "=" not in pair:
            raise ValueError(f"expected key=value, got {pair!r}")
        key, raw = pair.split("=", 1)
        key = key.strip()
        if key not in fields:
            raise ValueError(f"unknown config field {key!r}")
        current = getattr(Config(), key)
        out[key] = _coerce(raw.strip(), current, key)
    return out


def _coerce(raw: str, current, key: str):
    if isinstance(current, bool):
        if raw.lower() in ("true", "1", "yes", "on"):
            return True
        if raw.lower() in ("false", "0", "no", "off"):
            return False
        raise ValueError(f"{key} needs true or false, got {raw!r}")
    if isinstance(current, int):
        return int(raw)
    if isinstance(current, float):
        return float(raw)
    if isinstance(current, tuple):
        return tuple(json.loads(raw))
    if current is None or isinstance(current, str):
        return raw
    raise ValueError(f"{key} can't be set from the command line")


def make_config(overrides: dict, founders: str = "founders.npz") -> Config:
    config = Config.small_world()
    if founders and (ROOT / founders).exists():
        config.founders_path = str(ROOT / founders)
    for key, value in overrides.items():
        setattr(config, key, value)
    return config


def seeds_for(base: int, count: int) -> list[int]:
    """Independent, reproducible seeds for each run in a batch (NumPy SeedSequence)."""
    children = np.random.SeedSequence(base).spawn(count)
    return [int(c.generate_state(1)[0]) for c in children]


# --- running -------------------------------------------------------------------

def run_one(job: dict) -> dict:
    """One world, start to finish. Returns its summary; writes its daily rows if asked."""
    from emergent_world.sim import Simulation
    config = make_config(job["overrides"], job.get("founders", "founders.npz"))
    sim = Simulation(config, seed=job["seed"])
    recorder = Recorder(sim)
    started = time.time()
    for _ in range(int(job["ticks"])):
        sim.tick()
        recorder.sample(sim)
        if not sim.agents and job.get("stop_when_extinct", True):
            break
    summary = recorder.summary(sim)
    summary["seed"] = job["seed"]
    summary["seconds"] = round(time.time() - started, 1)
    out = job.get("out")
    if out:
        with open(Path(out) / f"seed_{job['index']}.jsonl", "w") as f:
            for row in recorder.rows:
                f.write(json.dumps(row) + "\n")
    return summary


def git_state() -> dict:
    def git(*args):
        try:
            return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, timeout=10).stdout.strip()
        except Exception:
            return ""
    return {"commit": git("rev-parse", "HEAD"), "dirty": bool(git("status", "--porcelain"))}


def run_batch(name: str, seeds: int, years: float, overrides: dict, workers: int = 4,
              base_seed: int = 0, out_root: Path | None = None, founders: str = "founders.npz") -> Path:
    stamp = time.strftime("%Y%m%d-%H%M%S")
    out = (out_root or ROOT / "runs") / name / stamp
    out.mkdir(parents=True, exist_ok=True)
    seed_list = seeds_for(base_seed, seeds)
    config = make_config(overrides, founders)
    manifest = {
        "name": name, "stamp": stamp, "years": years, "base_seed": base_seed, "seeds": seed_list,
        "overrides": overrides, **git_state(),
        "python": platform.python_version(), "numpy": np.__version__,
        "config": {k: v for k, v in dataclasses.asdict(config).items() if k != "items"},
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1, default=str))
    jobs = [{"index": i, "seed": s, "ticks": years * TICKS_PER_YEAR, "overrides": overrides,
             "out": str(out), "founders": founders} for i, s in enumerate(seed_list)]
    started = time.time()
    if workers <= 1:
        results = [run_one(j) for j in jobs]
    else:
        with Pool(workers) as pool:
            results = pool.map(run_one, jobs)
    results.sort(key=lambda r: seed_list.index(r["seed"]))
    (out / "summary.json").write_text(json.dumps(results, indent=1))
    manifest["wall_seconds"] = round(time.time() - started, 1)
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1, default=str))
    return out


# --- comparing ------------------------------------------------------------------

HEADLINE = ("alive_mean", "alive_end", "extinct", "life_expectancy_days", "births_per_person_year",
            "max_generation", "share_dehydration", "share_starvation", "share_poison", "share_old_age",
            "mood_mean", "discoveries", "count_comfort", "count_transmission", "genome_diversity")


def load_summary(path) -> list[dict]:
    path = Path(path)
    return json.loads((path / "summary.json" if path.is_dir() else path).read_text())


def values(rows: list[dict], key: str) -> np.ndarray:
    return np.array([float(r[key]) for r in rows if r.get(key) is not None], dtype=float)


def bootstrap_diff(a: np.ndarray, b: np.ndarray, resamples: int = 2000, seed: int = 0) -> tuple:
    """95% bootstrap interval for mean(b) - mean(a)."""
    rng = np.random.default_rng(seed)
    if len(a) == 0 or len(b) == 0:
        return (float("nan"), float("nan"))
    da = rng.choice(a, (resamples, len(a))).mean(1)
    db = rng.choice(b, (resamples, len(b))).mean(1)
    lo, hi = np.percentile(db - da, [2.5, 97.5])
    return float(lo), float(hi)


def welch_t(a: np.ndarray, b: np.ndarray) -> float:
    if len(a) < 2 or len(b) < 2:
        return float("nan")
    se = np.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))
    return float((b.mean() - a.mean()) / se) if se > 0 else float("inf") * np.sign(b.mean() - a.mean())


def compare(a_rows: list[dict], b_rows: list[dict], keys=HEADLINE) -> list[dict]:
    table = []
    for key in keys:
        a, b = values(a_rows, key), values(b_rows, key)
        lo, hi = bootstrap_diff(a, b)
        table.append({"metric": key, "a_mean": float(a.mean()) if len(a) else None,
                      "a_sd": float(a.std(ddof=1)) if len(a) > 1 else None,
                      "b_mean": float(b.mean()) if len(b) else None,
                      "b_sd": float(b.std(ddof=1)) if len(b) > 1 else None,
                      "diff_lo": lo, "diff_hi": hi, "t": welch_t(a, b),
                      "clear": bool(lo > 0 or hi < 0)})
    return table


def table_markdown(table: list[dict], a_name="A", b_name="B") -> str:
    def f(v):
        return "–" if v is None or (isinstance(v, float) and np.isnan(v)) else f"{v:.3g}"
    lines = [f"| metric | {a_name} mean ± sd | {b_name} mean ± sd | {b_name} − {a_name} (95% CI) | clear? |",
             "|---|---|---|---|---|"]
    for r in table:
        lines.append(f"| {r['metric']} | {f(r['a_mean'])} ± {f(r['a_sd'])} | {f(r['b_mean'])} ± {f(r['b_sd'])} | "
                     f"{f(r['diff_lo'])} to {f(r['diff_hi'])} | {'**yes**' if r['clear'] else 'no'} |")
    return "\n".join(lines)


def batch_markdown(rows: list[dict], keys=HEADLINE) -> str:
    lines = ["| metric | mean | sd | min | max |", "|---|---|---|---|---|"]
    for key in keys:
        v = values(rows, key)
        if len(v):
            lines.append(f"| {key} | {v.mean():.3g} | {v.std(ddof=1) if len(v) > 1 else 0:.3g} | "
                         f"{v.min():.3g} | {v.max():.3g} |")
    return "\n".join(lines)


def verify(days: int = 30, seed: int = 0) -> bool:
    """Run the same short world twice; True if the two are identical."""
    job = {"index": 0, "seed": seed, "ticks": days * TICKS_PER_DAY, "overrides": {}}
    first, second = run_one(job), run_one(job)
    return first["fingerprint"] == second["fingerprint"]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    r = sub.add_parser("run", help="run a batch of worlds")
    r.add_argument("--name", required=True)
    r.add_argument("--seeds", type=int, default=8)
    r.add_argument("--years", type=float, default=2.0)
    r.add_argument("--workers", type=int, default=4)
    r.add_argument("--base-seed", type=int, default=0)
    r.add_argument("--set", nargs="*", default=[], metavar="KEY=VALUE")
    c = sub.add_parser("compare", help="compare two batches")
    c.add_argument("a")
    c.add_argument("b")
    v = sub.add_parser("verify", help="check a world replays identically")
    v.add_argument("--days", type=int, default=30)
    args = parser.parse_args(argv)

    if args.command == "run":
        out = run_batch(args.name, args.seeds, args.years, parse_overrides(args.set), args.workers, args.base_seed)
        print(f"Wrote {out}")
        print(batch_markdown(load_summary(out)))
    elif args.command == "compare":
        print(table_markdown(compare(load_summary(args.a), load_summary(args.b)),
                             Path(args.a).parent.name or "A", Path(args.b).parent.name or "B"))
    elif args.command == "verify":
        ok = verify(args.days)
        print("identical" if ok else "NOT identical: something random isn't seeded")
        sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
