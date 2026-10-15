# Round 4: twenty years, and thirst (2026-10-15)

## Twenty years with the round-3 defaults (commit `b8bcc42`, 8 worlds)

| metric | mean | min | max |
|---|---|---|---|
| alive_mean | 18.2 | 13.9 | 23 |
| alive_last_year | 15.7 | 6.2 | 26.8 |
| floor_share | 0.000138 | 0 | 0.0008 |
| max_generation | 7.75 | 5 | 13 |
| life_expectancy_days | 270 | 258 | 287 |
| share_dehydration | 0.331 | 0.284 | 0.36 |
| share_starvation | 0.342 | 0.313 | 0.381 |
| share_poison | 0.235 | 0.219 | 0.27 |
| discoveries | 6.88 | 6 | 8 |
| count_transmission | 247 | 139 | 385 |
| established_made | 8.38 | 8 | 9 |

Every world kept 10-25 people for twenty years and spent 0-6 days at the two-person
floor, with family trees 5-13 generations deep. Against the plan's targets: no
collapse in 8 of 8 worlds (target 7), generation depth 7.75 (target 8, borderline),
thirst 33% of deaths (target 25%, missed), life expectancy about 9 months (target
12, missed).

## Thirst

Diagnosis in the twenty-year worlds: thirst deaths were mostly people born there,
70% in summer, a median 1.5 tiles from water, and 80% of them knew where water was.
Parched people beside water drank only 37% of the time, and nothing drew anyone
toward water they could see (the homing pull only worked for remembered water out
of sight). Now thirst urges a drink beside water and draws people toward water in
sight, and thirst (like hunger) weakens the pulls to follow and seek company.
Beside water, thirsty people drink 95-100% of the time; parched hours spent away
from water fell by about three quarters.

6 years, 8 worlds, commit `c9934a3`; reference = the same code with `thirst_urge=0`:

| metric | v4-no-thirst-urge | v4 |
|---|---|---|
| alive_mean | 22.4 | **+6.45 (+3.4, +9.8)** |
| alive_last_year | 19.8 | **+8.36 (+1.5, +15)** |
| floor_share | 0 | +0 (+0, +0) |
| net_growth_late | -12.9 | +0.584 (-2.8, +3.4) |
| life_expectancy_days | 250 | -0.713 (-9.3, +8.1) |
| births_per_person_year | 1.19 | +0.0125 (-0.036, +0.058) |
| max_generation | 6.88 | +0.25 (-1.1, +1.4) |
| share_dehydration | 0.345 | **-0.223 (-0.26, -0.18)** |
| share_starvation | 0.333 | **+0.192 (+0.14, +0.25)** |
| share_poison | 0.244 | -0.0109 (-0.039, +0.016) |
| discoveries | 5.88 | -0.25 (-0.75, +0.25) |
| count_transmission | 112 | **+43.9 (+15, +74)** |
| count_comfort | 762 | **+607 (+1.8e+02, +1.2e+03)** |
| mood_mean | -1.12 | **+0.123 (+0.023, +0.22)** |

Thirst falls from 35% to 12% of deaths and the population rises by about 6.5 people.
Starvation is now the main cause of death (52%).

Births still trail deaths by about 12 a year, the same as the newcomers who arrive
(one every 30 days), so the world depends on that immigration.

## Starvation is a winter famine

In the twenty-year worlds (run on with the current code), 88% of starvation deaths
come in winter: food on the map falls to about 261 items for about 25 people, and the
median person who starves has 3 safe food items within 6 tiles (spring: 22). The
population booms to about 60 in summer and winter cuts it back. This is the world's
seasonal pressure, not a decision bug, so it's left as it is.

## A closed world isn't self-sustaining (yet)

Same code with no newcomers (`newcomer_every_days=0`), 6 years:

```
batch                   alive      last yr   floor%  net/yr late  max gen
v4                     28.9         28.1         0%       -12.3       7.1
v4-closed              15.2*         5.1*       21%*       -3.1*      6.4
```

Without strangers, 4 of 8 worlds fall to the two-person floor within six years and the
rest decline. Strangers do two jobs: they make up the shortfall in births, and they
bring fresh founder genes that counter drift. Making a closed world sustainable would
take more children per lifetime, a milder winter, or both: a design choice left open.
