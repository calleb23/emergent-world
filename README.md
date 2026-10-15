# Emergent World

Blank neural-network agents learning to survive in a world that a god AI grows on demand.
This repo currently covers **build steps 1–2**: a grid world you can watch, and agents with
bodies and needs acting randomly.

## Setup (Windows, macOS or Linux)

```
python -m venv .venv
.venv\Scripts\activate          # Windows (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt
```

Needs Python 3.10 or newer.

## Run

```
python main.py                  # watch it live (SPACE pause, UP/DOWN speed, ESC quit)
python main.py --seed 7         # a different world; the same seed always replays the same run
python main.py --headless       # no window, runs fast, prints a summary
python -m pytest                # run the tests
```

Every run saves `runs/seed_<n>/deaths.csv` (each death with its cause) and
`runs/seed_<n>/ticks.csv` (population, plants and average needs per tick).

## What's in the world

- 64x64 grid of grass with a few lakes.
- Food plants regrow on empty grass. About 10% of new plants are poisonous and only
  *look* slightly different (a slightly yellower green).
- Eating poison feels like food at first; sickness starts 25 ticks later.
- Agents have energy, water, health and a lifespan. They can move, eat, drink (next to
  water) or rest. They die of starvation, dehydration, poison or old age.

All numbers live in `emergent_world/config.py`.

## Layout

```
emergent_world/
  config.py        all tunable numbers
  world/grid.py    terrain, water, plants
  agents/agent.py  bodies, needs, actions
  agents/policy.py who decides actions (random for now; brains in step 3)
  sim.py           tick loop
  stats.py         death log and per-tick stats
  viewer.py        pygame window
main.py
tests/
```

## Next steps

3. **Senses and a tiny brain:** vision rays plus hunger/thirst inputs into a small NumPy
   network that replaces `RandomPolicy`.
4. **Evolution only:** survivors reproduce, children inherit mutated brain weights.
   Done when agents find food and water by instinct.
5. **Learning within a lifetime:** an aversion memory from sickness and from watching
   relatives die. Done when the poison-plant test passes.
