# Emergent World

Blank neural-network agents learning to survive in a world that a god AI grows on demand.
This repo currently covers **build steps 1–4**: a grid world you can watch, agents with
bodies and needs, honest senses, tiny neural-network brains with basic instincts, evolution,
and a founder population evolved in a fast "prehistory" that starts long-lived worlds.

## Setup (Windows, macOS or Linux)

```
python -m venv .venv
.venv\Scripts\activate          # Windows (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt
```

Needs Python 3.10 or newer.

## Run

```
python -m emergent_world.live   # watch it live in your browser (opens http://localhost:8765)
python main.py                  # or watch it live in a pygame window
python main.py --headless --story   # print the followed agent's life story as it happens
python -m emergent_world.replay     # record 3 years into replay.html: open it in any browser
python main.py --people 6       # how many founders start the world (default 12, cap 40)
python main.py --children 2     # roughly how many children per lifetime (default 3)
python main.py --years 5        # average lifespan of 5 years (default 2)
python main.py --run-years 30   # how long to simulate (default 10 years)
python main.py --seed 7         # a different world; the same seed always replays the same run
python main.py --headless       # no window, runs fast, prints a progress line every 30 days
python main.py --blank          # start from random brains instead of founders
python main.py --random         # random actions instead of brains, as a baseline
python -m pytest                # run the tests
```

Every run saves `runs/seed_<n>/deaths.csv` (each death with its cause) and
`runs/seed_<n>/ticks.csv` (population, plants and average needs per tick).

## Time

**1 tick = 1 hour.** Body needs are set on that clock: with nothing to drink an agent dies
in about 10 days, with nothing to eat in 2–3 weeks, and poison acts within a day. Lifespan
is separate, and life stages scale with it: adulthood at 15% of the average lifespan, and
children spaced 10% of a lifespan apart.

## How the founders are made

Agents start with instincts, then evolve, then live long lives:

1. **Instincts** (`python -m emergent_world.instincts` → `instincts.npz`). A hand-written
   teacher (`agents/teacher.py`) acts on what things physically are, not what they look
   like: try to eat any loose solid, drink any liquid, walk toward them when hungry or
   thirsty (breathing gases will be automatic once gases exist). Brains are trained to
   copy it, like animals born with instincts. The instincts don't know which solids are
   food, so **poison gets eaten like anything else**: that's left for agents to learn.
2. **Prehistory** (`python -m emergent_world.prehistory` → `founders.npz`). The same bodies
   and hourly needs, but lives of about five weeks, so hundreds of generations pass in
   about 23 simulated years. Food limits the population, so selection is real. The
   survivors become the founders: a whole population with different brains.
3. **The real world** (`python main.py`). Starts from the founders at mixed ages, with
   long lives. Instincts depend on how fast needs drain, not on lifespan, so they carry
   over. With long lives, generations are slow; from here, learning and culture (step 5
   onward) are meant to do the heavy lifting.

Both files are reusable. Rerun both steps after changing the senses or brain size.

**Mutation matters.** Children change about 5% of their brain weights. When every weight
changed (the first version), good brains drifted apart faster than selection could keep
them ("mutational meltdown"): those founders were wiped out within three lifetimes when
put head-to-head against plain instincts. With 5% they win, holding 82–89% of a shared
world after five lifetimes.

## What's in the world

- 64x64 grid of grass with a dozen small ponds.
- **Items** (`world/items.py`): one table row per kind, saying how it looks, what eating
  it does, where it appears and how long it lasts. Agents only ever see the colors.

  | Item | Eating it | Where |
  |---|---|---|
  | green plant | good food | anywhere |
  | yellow-green plant | sick a day later | anywhere |
  | red berry | small, sweet | near water |
  | purple berry | sick within hours | near water |
  | brown mushroom | good food | near water |
  | pale mushroom | badly sick 40 hours later, so it's hard to tell why | near water |
  | nut | rich food, rare | far from water |
  | grey rock, stick | can't be eaten; agents learn to stop trying | anywhere |
  | cug | a fine meal, if you can catch one | near water |

  The **cug** is the world's first critter: small, teal and skittish. Cugs wander,
  bolt when someone gets next to them, and breed when there's room (busy in spring,
  nearly stopped in winter), up to about 120 at once.

- **Day and night, seasons and weather** (`world/climate.py`): 24-hour days; at night
  agents see only a few tiles. Four 91-day seasons: spring grows fastest, summer heat
  makes agents thirsty, winter barely grows and its cold burns energy. Weather shifts
  every few hours: clear, cloudy, rain (eases thirst, helps growth), storm, fog, and
  snow in winter. Storms, fog and snow cut visibility.
- **Sleep:** tiredness builds while awake. Tired agents sleep from dusk to dawn, wake
  early if thirst, hunger or sickness gets bad, and collapse if pushed past exhaustion.
  Sleeping slows hunger and thirst and doubles healing.
- Agents have energy, water, health, tiredness and a lifespan. They can move, eat, drink
  (next to water) or rest. They die of starvation, dehydration, poison, exhaustion or
  old age.
- **Senses** (`agents/senses.py`): 8 vision rays, each with a ground layer (water) and an
  object layer (items, agents), reporting color and closeness only, never labels. Plus
  what's underfoot, touching liquid, energy, water, health and pain.
- **Brains** (`agents/brain.py`): 72 inputs, 16 hidden, 7 actions (about 1,300 weights).
  All brains run as one batched NumPy operation.
- **Reproduction:** fed, watered adults have a child next to them with a mutated copy of
  their brain. Children inherit a `lineage` tag, for tracking whose descendants win.
- **Garden curriculum** (only for runs from random brains): hunger and thirst drain
  slowly at first and ramp to full strength.
- **Bootstrap:** if the population falls below a minimum, it's topped up with mutated
  copies of founders, instincts, or the fittest recent brains.

All numbers live in `emergent_world/config.py`.

## Layout

```
emergent_world/
  config.py         all tunable numbers, and the hourly clock
  world/grid.py     terrain, liquids, plants
  agents/agent.py   bodies, needs, actions
  agents/senses.py  what agents perceive (batched across all agents)
  agents/brain.py   tiny neural networks, mutation, batched thinking
  agents/policy.py  who decides actions: brains, or random as a baseline
  agents/teacher.py the hand-written teacher behind the instincts
  instincts.py      records the teacher and trains brains to copy it
  prehistory.py     evolves the founder population
  sim.py            tick loop
  stats.py          death log and per-tick stats
  viewer.py         pygame window
main.py
tests/
```

## Following one life

The world is deliberately small: 12 founders, about three children per lifetime, at
most 40 people. Every agent keeps a life story, written by an observer (so a plant is a
"yellow-green plant", never "poison"): first meals and drinks, getting sick and what they
became wary of, running out of water, children, seeing relatives die, and their own death.
The viewer follows one agent: their needs, what they're wary of, and their recent life.
When they die, it moves on to their oldest living child. A sample from `--story`:

```
year 1, day 111    #10   Ate a yellow-green plant despite a bad feeling about it
year 1, day 112    #10   Fell sick; now wary of yellow-green plant
year 1, day 207    #10   Had a child, #53
year 1, day 209    #10   Died of poison, aged 557 days
year 1, day 209    #53   Now following #53 (child of #10), aged 2 days
```

In small worlds (seeds 0–2, 6 years), agents live 140–435 days on average and some reach
old age; poison is now the leading cause of death.

## Food memory (step 5, in progress)

`agents/memory.py`. Built-in wiring, like real taste aversion: what's learned is *which*
foods to avoid, keyed only by what they look like.

- Getting sick blames the foods eaten in the previous two days.
- Foods eaten without getting sick afterwards earn trust (so the safe food eaten the
  same day as the poison isn't blamed for long).
- Agents notice what relatives eat nearby; if they see one die of poison, they blame
  what they saw it eat.
- Aversion holds back the urge to eat, including random tries, and steers agents away
  from foods they're wary of when they see them. How strongly is an inherited gene
  (`aversion_gain`). Aversion fades slowly (halves in about 140 days).
- Biting a rock or stick makes it mildly unappealing, so agents learn to stop trying.
- Hunger overrides disgust: below half energy, wariness fades, down to a tenth when
  starving. Without this, an agent that wrongly blames its main food (easy after the
  slow pale mushroom) can starve rather than ever learn the food was safe.

Result (seed 0, 1-year lives, 4 simulated years, memory on vs off):

| | Memory on | Memory off |
|---|---|---|
| Poison share of meals: naive agents | 13.6% | 9.8% |
| ... agents who got sick | 7.8% | 10.1% |
| ... agents who watched a relative die | 7.6% | 10.2% |
| Share of deaths from poison | 22% | 40% |
| Births | 4,735 | 3,361 |

Experienced agents eat poison about half as often as naive ones (naive agents look worse
partly because poison builds up when others avoid it). It's a partial pass: avoidance
isn't complete.

## Next steps

- Steering away from foods in sight cut poison deaths by 23% (seed 0, 4 years): agents
  who got sick now eat poison in 5.2% of meals (was 7.8%), those who watched a relative
  die 4.0% (was 7.6%).
- Prehistory still uses fast breeding (about eight children per five-week life); the
  founders haven't evolved under the small world's slower breeding.
