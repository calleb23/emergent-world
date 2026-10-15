"""Watch the world live in your browser.

    python -m emergent_world.live              # opens http://localhost:8765
    python -m emergent_world.live --seed 3 --port 9000

The simulation runs on your computer; the page shows it as it happens. Pause,
change speed, click anyone to follow them. Close it with Ctrl+C.
Uses only Python's standard library for the web server (no extra installs).
"""

import argparse
import json
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from emergent_world.config import Config
from emergent_world.sim import Simulation
from emergent_world.webview import agent_rows, climate_info, page, person, plant_string, static_info

SPEEDS = (1, 6, 24, 96, 240, 720)   # hours per second


class LiveWorld:
    """A simulation stepping in a background thread at a chosen speed."""

    def __init__(self, sim: Simulation):
        self.sim = sim
        self.lock = threading.Lock()
        self.speed = 24          # hours of simulated time per real second
        self.paused = False
        self.auto = True         # follow the next of kin when the followed person dies
        self.known = {a.id: a for a in sim.agents}   # everyone who ever lived, for their stories
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        owed = 0.0
        last = time.perf_counter()
        while True:
            now = time.perf_counter()
            if not self.paused and self.sim.living:
                owed += (now - last) * self.speed
                steps = min(int(owed), 200)       # catch up, but never freeze the page
                owed -= steps
                with self.lock:
                    for _ in range(steps):
                        followed = self.sim.followed_id
                        self.sim.tick()
                        for a in self.sim.agents:
                            self.known.setdefault(a.id, a)
                        if not self.auto and followed != self.sim.followed_id:
                            self.sim.followed_id = followed   # stay with your choice, even after death
            else:
                owed = 0.0
            last = now
            time.sleep(0.01)

    def state(self) -> dict:
        with self.lock:
            sim = self.sim
            followed = self.known.get(sim.followed_id) if sim.followed_id is not None else None
            return {
                "tick": sim.tick_count,
                **climate_info(sim),
                "plants": plant_string(sim.world),
                "agents": agent_rows(sim),
                "followed": followed.id if followed else -1,
                "person": person(followed, sim.tick_count, sim) if followed else None,
                "speed": self.speed,
                "paused": self.paused,
                "auto": self.auto,
            }

    def control(self, params: dict):
        with self.lock:
            if "paused" in params:
                self.paused = params["paused"][0] == "1"
            if "speed" in params:
                self.speed = max(1, min(720, int(params["speed"][0])))
            if "auto" in params:
                self.auto = params["auto"][0] == "1"
            if "follow" in params:
                agent = self.known.get(int(params["follow"][0]))
                if agent is not None:
                    self.sim.followed_id = agent.id
                    self.auto = False


def serve(world: LiveWorld, port: int, open_browser: bool):
    home = page({**static_info(world.sim, "live"), "speeds": SPEEDS}).encode()

    class Handler(BaseHTTPRequestHandler):
        def _send(self, body: bytes, kind: str):
            self.send_response(200)
            self.send_header("Content-Type", kind)
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            path = urlparse(self.path).path
            if path == "/":
                self._send(home, "text/html; charset=utf-8")
            elif path == "/state":
                self._send(json.dumps(world.state(), separators=(",", ":")).encode(), "application/json")
            else:
                self.send_error(404)

        def do_POST(self):
            url = urlparse(self.path)
            if url.path == "/control":
                world.control(parse_qs(url.query))
                self._send(b"{}", "application/json")
            else:
                self.send_error(404)

        def log_message(self, *args):   # keep the terminal quiet
            pass

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    url = f"http://localhost:{port}"
    print(f"Watching live at {url}  (Ctrl+C to stop)")
    if open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


def main():
    parser = argparse.ArgumentParser(description="Watch the world live in your browser")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--years", type=float, default=2.0, help="average lifespan in years")
    parser.add_argument("--people", type=int, default=30)
    parser.add_argument("--max-people", type=int, default=80)
    parser.add_argument("--children", type=float, default=3.0)
    parser.add_argument("--founders", default="founders.npz")
    parser.add_argument("--no-browser", action="store_true", help="don't open a browser tab")
    args = parser.parse_args()

    config = Config.small_world(args.people, args.max_people, args.children, args.years)
    if Path(args.founders).exists():
        config.founders_path = args.founders
    sim = Simulation(config, seed=args.seed)
    sim.follow(max(sim.agents, key=lambda a: a.age, default=None))
    serve(LiveWorld(sim), args.port, not args.no_browser)


if __name__ == "__main__":
    main()
