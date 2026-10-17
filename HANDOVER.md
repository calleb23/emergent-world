# Emergent World: handover

Status as of 17 October 2026, commit `e8e82e7` on `main` of
https://github.com/calleb23/emergent-world (private). Everything below describes
that build. 146 tests pass (`python -m pytest -q`).

## 1. What this is

A small simulated world (64×64 tiles, 1 tick = 1 hour) where people with tiny neural
network brains have to survive: find water and food, avoid poison, get through
weather and winters, raise children, and live together. Nothing tells them how.
Behaviour comes from:

- **Drives and feelings** (hunger, thirst, tiredness, cold, pain, fear, anger,
  loneliness, boredom, joy) that make some moments feel good and others bad.
- **Built-in wiring** of the kind real animals have (taste aversion, children
  following parents, an urge to drink when parched beside water).
- **Learning**: lifetime reinforcement learning, imitation, teaching, a
  hippocampus-style episodic memory with sleep replay, and evolution of inherited
  brains and learning genes across generations.
- **A physical world** with 70 kinds of item, materials with properties (hardness,
  burning, tension, adhesion, brittleness), fire, seasons and weather, animals,
  plants and natural shelter.

The aim is emergence: tools, fire, shelters, teaching and (eventually) language
arising from these pieces rather than being scripted. The user's guiding rule has
been **"don't push them to do things; add drives and let them figure it out"**, and
**"don't turn anything off, just add features so people can figure out how to live"**.

## 2. Running it

Requirements: Python 3.10+ and NumPy (`pip install -r requirements.txt`; pygame-ce
is only for the old desktop viewer, pytest for tests).

| What | Command |
|---|---|
| Watch live in a browser (auto-updates from GitHub) | double-click `start.bat` (Windows) or run `./start.sh` |
| Watch live without auto-update | `python -m emergent_world.live` then open http://localhost:8765 |
| Record a replay page | `python -m emergent_world.replay --seed 4 --run-years 1.5 --out replay.html` |
| A hundred-year run with a replay of the end | `python -m emergent_world.century --years 100 --out <folder>` |
| A batch experiment | `python -m emergent_world.experiment run --name NAME --seeds 8 --years 6 --set key=value ...` |
| Compare batches | `python -m emergent_world.experiment report runs/A/<stamp> runs/B/<stamp> ...` |
| Check determinism | `python -m emergent_world.experiment verify` |
| Tests | `python -m pytest -q` |

`start.bat`/`start.sh` pull from GitHub, start the live server with
`--auto-update 2` (checks GitHub every 2 minutes), and restart on exit code 3 when
new code was pulled; the open page reloads itself. The repository is private, so the
user's machine needs GitHub credentials (`git config --global credential.helper
manager`, or GitHub Desktop).

**Founders.** `founders.npz` holds evolved starting brains (from an earlier
prehistory run) and is loaded by the live view, replays, experiments and century runs.
`instincts.npz` holds a brain trained to copy a simple teacher (eat anything solid,
drink any liquid, walk toward them). Brains made for fewer inputs or actions are grown
to the current shape by `Brain.fitted()`: new inputs start with zero weight, new
actions start unlikely (bias -3).

## 3. Code map

```
emergent_world/
  config.py         every setting (Config dataclass); Config.small_world() is the default world
  sim.py            the Simulation: one tick = climate, world, physics, critters, decisions,
                    actions, bodies, reproduction, memories, newcomers, chronicle
  behaviour.py      what the body feels (exposure, boredom), weather memories, activity labels
  stats.py          per-tick and per-death logs
  metrics.py        experiment metrics (daily rows, run summary, fingerprint)
  experiment.py     batch runner, comparisons, reports, determinism check
  checkpoint.py     save / resume / fork a whole world (gzipped pickle)
  live.py           live browser server (standard library HTTP), auto-update
  replay.py         record a run into one self-contained HTML page
  webview.py        what the page is sent (shared by live and replay)
  viewer.html       the browser page (map, world readings, followed person)
  century.py        long runs with yearly summaries, checkpoints every 10 years
  instincts.py, prehistory.py, viewer.py (old pygame viewer)
  agents/
    agent.py        the Agent dataclass and the 18 actions
    brain.py        the neural network, batched thinking, TD learning, imitation step
    policy.py       BrainPolicy: senses -> built-in pulls/urges -> brain -> actions;
                    lifetime learning, imitation, shelter and building drives
    senses.py       what an agent perceives (109 numbers)
    memory.py       food memory (taste aversion, trust, known non-food) and place slots
    hippocampus.py  episodic memory, recall by need, sleep replay
    emotions.py     fear, anger, loneliness, joy, grudges, personality traits
    genes.py        inherited learning genes (learning rate, imitation rate, exploration)
    teacher.py, names.py
  world/
    grid.py         terrain, items on tiles, habitats, regrowth, critters, shelters, shores
    items.py        the 70 item kinds as data, plus strike, tap and join recipes
    physics.py      striking, rubbing, fire, cooking, joining, wetness, wind, nature, fishing
    climate.py      day/night, four 91-day seasons, weather
tests/              20 test files, 146 tests
docs/experiments/   results of every experiment round (read these before changing defaults)
```

## 4. How a person works

**Senses (109 inputs).** Eight vision rays (each: nearest water and nearest object,
as colour and closeness; night and weather shorten sight), what's underfoot, touching
water, energy, water, health, pain, what's in their hands, boredom, cold-and-wet,
light, being at a shelter, stick pile underfoot; their own feelings; the nearest
person's fear, anger, joy, bond, kinship, grudge, whether they hold something and
whether they're adjacent; the remembered call (direction, loudness, fear in it, which
of three sounds); and recalled places (direction and strength to the best remembered
water, food and shelter). They never see labels or item identities, only colours.

**Brain.** A 109 → 16 (tanh) → 18 network. Actions: N, S, E, W, EAT, DRINK, REST,
PICK_UP, DROP, GIVE, STRIKE, RUB, TAKE, HIT, COMFORT, CALL, CALL_B, CALL_C. The
highest value wins, with a chance of a random action (the inherited exploration gene,
about 10%). Lifetime learning is temporal-difference learning on the last layer
only, from a reward made of changes in comfort (needs), pain, exposure, boredom,
novelty and feelings. Children inherit the parents' **birth** brain (the genome),
mutated, not the learned one.

**Built-in wiring (policy.py).** Penalties and pulls added to the brain's values:
taste aversion and steering away from foods that made them sick; refusing known
non-food; trusting foods parents ate; desperation (hunger overrides wariness); a
hunger urge to bite what's underfoot; a thirst urge to drink beside water and a pull
toward water in sight; homing to remembered water and food; children following a
parent (orphans follow kin); company and mating pulls; loneliness pull; grief makes
people rest; reluctance to hit or rob (weaker when angry or hungry); shelter-seeking
when exposed; a building urge (gather wood, pile it) for people who know shelters and
have suffered the cold; curiosity toward calls. Hunger and thirst weaken the social
pulls.

**Memory.**
- Food memory: aversion and trust per colour, known non-food, recent meals blamed
  when sick, watching kin eat or die of poison.
- Hippocampus: up to 128 episodes (what, where, when, how much it mattered):
  drinking when parched, water seen, good meals, sheltering in bad weather, being
  hurt, seeing others sheltered while exposed, watching wood being piled. Recall by
  need feeds the place pulls and the senses. Experiences are replayed during sleep (4
  per sleeping hour) to the brain. Children near a parent get the parent's best place
  memories.
- People: bonds, grudges, kin.

**Social learning.** Imitation: onlookers lean toward what someone nearby did (more if
it paid off, away if it hurt; kin and friends watched most; children twice as much).
Teaching: when a grown-up's action works with younger kin watching, the watchers get
a stronger lesson and the teacher a small reward.

**Body and life.** Energy, water, health, fatigue, fat (up to 180), sickness, aging,
sleep at night (can't fall asleep when parched or starving), exposure damage, grief.
Two parents are needed (partners within 16 tiles, not close kin, no grudge), about
4.5 children per lifetime, lives of about 2 years (1.6 to 2.4), adulthood at about
110 days. Strangers arrive every 30 days with founder brains; top-ups keep at least 2
people alive.

**Feelings and personality.** Fear, anger (with grudges), loneliness, joy, grief,
from pain, threats, wrongs, being alone and good moments. Inherited traits:
boldness, sociability, temper, kindness.

**Communication.** Three call sounds, heard up to 16 tiles away and remembered for 6
hours as a place and a sound. Needy or lonely listeners go to see what a call was
about; callers are glad when someone who came finds food or water.

## 5. The world

- **70 item kinds** (world/items.py): plants, berries, mushrooms, nuts, trees, wood,
  stone, flint, clay, reeds and fibre, vines, resin, mud, hives, eggs, animals (cugs,
  deer, wolves, snakes, songbirds), fish, meat and cooked food, tools (flake, flint
  blade, sharpened stick, spear, stone hammer, bow, snare, pots), seeds, saplings,
  rock overhangs. Each is a row of properties; nothing about them is scripted.
- **Physics**: strike (hardness, breaks into, recipes, stings, sparks, reach of
  spears and bows, bonds that give way under strain), rub (friction heat → fire),
  fire (fuel, spread, rain, lightning, cooking, ash, burns, warmth), join (tension of
  flexible binders, adhesion of sticky ones, load limits, wet glue fails), brittle
  things smash, weight limits carrying, wetness, storm wind on shelters, rot, seeds
  and saplings grow, trees shed fruit and branches, animals graze, hunt and bite,
  fishing, warm pelts, rain fills pots.
- **Climate**: day and night, four 91-day seasons, Markov weather (clear, cloudy,
  rain, storm, fog, snow). Winter is mild by default (regrowth 0.8 at 8°C).
- **Shelter**: stick piles of 4 become shelters; rock overhangs and thick pines give
  natural cover; lashing (cord, vine) protects from wind, daubing (mud) from fire.

## 6. Measurement and experiments

One world is far too noisy to judge a change by (survivors after 1.5 years ranged
3-21 between seeds on identical code). Every change since the experiment runner was
built has been judged on batches of 8 (sometimes 16) worlds, usually over 6 years,
with 95% bootstrap intervals. Worlds are exactly reproducible by seed (checked across
processes and worker counts). Results are in `docs/experiments/`:

| Round | What it established |
|---|---|
| ablations (10-15) | Remembering seen water is the strongest survival fix; lifetime learning and emotions help survival; imitation's survival effect not established |
| round 2 | Hunger fix null; calls carry only faint information; the exploration gene is selected; the population wasn't viable over 10 years |
| round 3 | Collapse diagnosed (too few births, brains degrading by drift); founder-brain newcomers, 4.5 children, partners within 16 tiles and more fat fixed it |
| round 4 | Twenty-year stability; thirst urge cut thirst deaths from 35% to 12%; starvation was a winter famine; closed worlds weren't self-sustaining |
| round 5 | Imitation raises discoveries but not survival (16 seeds) |
| round 6 | A century with everything; shelters had nearly vanished |
| round 7 | Milder winters (population 28 → 47; closed world viable); natural shelter plus drives make shelters appear; the hippocampus (via sleep replay) triples shelter-building and adds discoveries; replay made people walk away from water until the thirst urge was strengthened (thirst 21% → 7% of deaths, life expectancy +22 days) |

**Current numbers** (batch `v9`, 8 worlds × 6 years, current defaults): about 51
people alive on average, life expectancy about 305 days, family trees about 8
generations deep, up to 18 shelters standing at once (12 in the final year),
about 7.5 tracked discoveries per world, about 3,200 lessons taught, 850 skills
copied and 4,500 calls that led someone to food or water. Deaths: starvation about
49%, poison 23%, thirst 7%.

Metrics include survival and viability (days at the population floor, net growth),
causes of death, time to each discovery, behaviour (action entropy, skills that
changed something), technology activity (made items present and established, after
Bedau and Packard), ecology (stock variability, species lost), genes, signalling
(mutual information between call sound and situation against a shuffled baseline,
approach rate), shelters, and social counts.

## 7. Known problems and open questions

- **Calls don't mean anything yet.** Information between sound and situation stays
  around 0.001-0.002 bits (out of 1.58). Listeners approach calls slightly more than
  chance, and calls do lead people to food, but no sound has come to mean anything.
  Next idea: let learning link a heard sound to what was found there (the hippocampus
  could store the sound with the episode), or make listener payoff depend on the sound.
- **Learned values outgrow built-in urges.** Sleep replay (and learning generally)
  inflated the value of wandering until a thirst urge of 5 lost to it. Raised to 15.
  Other urges (hunger 5, shelter 3, build 3) may need the same treatment; a general
  fix would scale urges to each brain's value range.
- **The closed world.** With milder winters it no longer collapses (2% of days at the
  floor), but births still trail deaths by about 12 a year, made up by newcomers.
- **Brains drift.** In small populations, inherited brains degrade over generations;
  founder-brain newcomers counter it. A larger world would select more strongly.
- **Envying others' shelter** has no measurable effect yet (the cold is enough).
- **Teaching** is frequent but has no measured survival effect.
- **Speed**: about 30-70 seconds per simulated year per world, depending on
  population. Profiling shows sense_all, emotions, critter movement and sleep replay
  as the main costs.
- **Lifespan** is about 2 years with ~10-month life expectancy; longer lives would make
  culture easier but slow every experiment.

## 8. Conventions for working on it

- Judge every behavioural change with a batch (`experiment run`) against a reference
  batch on the same code, and add a dated write-up to `docs/experiments/`.
- New behaviour should be a drive, feeling, sense, physical property or learning
  mechanism, not a script. Every new mechanism gets a `Config` switch so it can be
  ablated.
- Add tests for each mechanism (`tests/`); keep worlds deterministic (all randomness
  through `sim.rng`); `experiment verify` must pass.
- Commit messages explain the measured reason for a change.
- While long batches run, develop in a separate git worktree: each `experiment run`
  imports the code on disk when it starts.

## 9. Published pages

- Latest replay (years 4-5 of a world with the hippocampus):
  https://claude.ai/artifact/3CW6GCyCaYAc1dPW6c2anW
- Hundred-year run (final two years): https://claude.ai/artifact/YFpd1emvdtn5mbdmhdtf17

Both are private to the owner's account until shared.
