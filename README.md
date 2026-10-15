# Emergent World

Blank neural-network agents learning to survive in a world that a god AI grows on demand.
This repo currently covers **build steps 1–4**: a grid world you can watch, agents with
bodies and needs, honest senses, tiny neural-network brains with basic instincts, and
asexual reproduction with mutation. Populations now sustain themselves across generations.

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
python main.py --headless       # no window, runs fast, prints a progress line every 1000 ticks
python main.py --blank          # start from random brains instead of instincts
python main.py --random         # random actions instead of brains, as a baseline
python -m emergent_world.instincts   # retrain instincts.npz (needed after changing senses or brain size)
python -m pytest                # run the tests
```

Every run saves `runs/seed_<n>/deaths.csv` (each death with its cause) and
`runs/seed_<n>/ticks.csv` (population, plants and average needs per tick).

## What's in the world

- 64x64 grid of grass with a dozen small ponds.
- Food plants regrow on empty grass. About 10% of new plants are poisonous and only
  *look* slightly different (a slightly yellower green).
- Eating poison feels like food at first; sickness starts 25 ticks later.
- Plants wilt over time, so uneaten poison plants don't take over the map.
- Agents have energy, water, health and a lifespan. They can move, eat, drink (next to
  water) or rest. They die of starvation, dehydration, poison or old age.
- **Senses** (`agents/senses.py`): 8 vision rays, each with a ground layer (water) and an
  object layer (plants, agents), reporting color and closeness only, never labels. Plus
  what's underfoot, touching liquid, energy, water, health and pain.
- **Brains** (`agents/brain.py`): 72 inputs, 16 hidden, 7 actions (about 1,300 weights).
  All brains run as one batched NumPy operation.
- **Reproduction:** fed, watered adults have a child next to them with a mutated copy of
  their brain.
- **Garden curriculum:** hunger and thirst drain slowly at first and ramp to full strength.
- **Instincts** (`instincts.py`, `agents/teacher.py`): based on what things physically are,
  not what they look like. Try to eat any loose solid, drink any liquid, and walk toward
  them when hungry or thirsty (breathing gases will be automatic once gases exist). A
  hand-written teacher does this using exactly the agents' senses; brains are trained to
  copy it, and every run starts from mutated copies, like animals born with instincts.
  The instincts don't know which solids are food, so **poison gets eaten like anything
  else**: learning what's worth eating is left to the agents.
- **Bootstrap:** while the population is below a minimum, it's topped up with mutated
  copies of the fittest recent brains plus some fresh random ones.

All numbers live in `emergent_world/config.py`.

## Layout

```
emergent_world/
  config.py        all tunable numbers
  world/grid.py    terrain, water, plants
  agents/agent.py  bodies, needs, actions
  agents/senses.py what agents perceive (batched across all agents)
  agents/brain.py  tiny neural networks, mutation, batched thinking
  agents/policy.py who decides actions: brains, or random as a baseline
  agents/teacher.py the hand-written teacher behind the instincts
  instincts.py     records the teacher and trains brains to copy it
  sim.py           tick loop
  stats.py         death log and per-tick stats
  viewer.py        pygame window
main.py
tests/
```

## Next steps

Where things stand (seed 0, 60,000 ticks with instincts): the population holds at its
400-agent cap for 66 generations with no top-ups, and most agents die of old age.
Random brains average about 355 ticks of life, cloned instincts about 850–900.

4. **Tune evolution:** the population sits at the 400-agent safety cap, so births are
   limited by the cap rather than food, which weakens selection. Make food the limit.
   Agents still eat poison at the rate it grows; nothing has evolved against it yet.
5. **Learning within a lifetime:** an aversion memory from sickness and from watching
   relatives die. Done when the poison-plant test passes.
