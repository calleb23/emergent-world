# Round 3: making the population viable (2026-10-15)

8 worlds per batch, **6 simulated years** each (2-year runs hid the collapse: the
founders were still alive). Code: commit `23c9ba5` plus `--set` overrides.

## Why the population collapsed

- **Births never kept up.** Births fell below deaths from year 1; by years 4-10 a
  world saw 1-8 births a year and was kept going by strangers and top-ups.
- **In a mature world, 78% of deaths are strangers**, mostly of thirst in spring and
  summer; over 40% of them never found water.
- **Brains degrade over the generations.** Brains of living people in year 10, put
  30 at a time into fresh worlds, kept 15.3-15.5 of 30 alive for 120 days against
  20.3 for the original founders. It isn't lifetime learning (inherited brains are
  just as bad as learned ones): with only 5-15 people, mutations accumulate faster
  than weak selection removes them (genetic drift).

## Levers (6 years)

`*` = 95% bootstrap interval for the difference from `ref6` excludes zero.
`floor%` = share of days at the 2-person floor that top-ups guarantee.
`net/yr late` = births minus deaths per year over the second half.

```
batch                   alive      last yr   floor%  net/yr late  max gen
ref6                   12.7          6.3         5%       -14.6       4.2
lever-children         15.2          6.8         3%       -14.5       4.6
lever-mate16           14.1          8.2         3%       -14.9       4.8
lever-repro50          12.6          6.2         4%       -13.7       3.6
lever-fat180           15.3          7.6         3%       -14.8       5.2
lever-regrow           12.2          5.5         5%       -13.6       3.9
l6-founder-newcomers       16.4*         9.6         1%*      -12.9       4.5
l6-no-learning          9.9*         6.6         7%       -11.8*      3.1*
l6-combo               17.9*        11.4*        2%       -12.4       5.9
l6-all                 21.3*        18.0*        1%*      -11.4*      6.9*
l6-all-mut02           20.9*        15.2*        0%*      -13.3       6.4*
```

| batch | overrides |
|---|---|
| lever-children | `cooldown_fraction=0.189` (about 4.5 children per lifetime instead of 3) |
| lever-mate16 | `mate_range=16` (was 8) |
| lever-repro50 | `reproduce_energy=50` (was 70) |
| lever-fat180 | `max_fat=180` (was 60) |
| lever-regrow | `regrow_chance=0.0012` (was 0.0009) |
| l6-founder-newcomers | `newcomers_from_living=False` |
| l6-no-learning | `learning=False` |
| l6-combo | children + mate16 + fat180 |
| l6-all | combo + founder newcomers |
| l6-all-mut02 | all + `mutation_rate=0.02` |

## All together

| metric | ref6 | l6-all | l6-all-mut02 |
|---|---|---|---|
| alive_mean | 12.7 | **+8.67 (+5.2, +12)** | **+8.19 (+4.8, +11)** |
| life_expectancy_days | 264 | **-17.2 (-29, -5.8)** | **-19.1 (-32, -7.3)** |
| births_per_person_year | 0.862 | **+0.315 (+0.24, +0.38)** | **+0.318 (+0.24, +0.38)** |
| max_generation | 4.25 | **+2.62 (+0.88, +4.5)** | **+2.12 (+0.62, +3.9)** |
| share_dehydration | 0.373 | -0.0502 (-0.1, +0.0063) | -0.0426 (-0.091, +0.0086) |
| share_starvation | 0.374 | -0.0019 (-0.074, +0.067) | -0.0235 (-0.093, +0.039) |
| share_poison | 0.184 | **+0.0384 (+0.005, +0.072)** | **+0.0498 (+0.021, +0.074)** |
| discoveries | 4.75 | +0.75 (-0.25, +1.9) | +1 (+0, +2) |
| count_transmission | 85.1 | +21.5 (-8.1, +54) | +14.8 (-16, +46) |
| count_comfort | 2.98e+03 | **-2.16e+03 (-4.4e+03, -4.9e+02)** | **-2.26e+03 (-4.6e+03, -6e+02)** |
| mood_mean | -1.45 | **+0.336 (+0.16, +0.51)** | **+0.324 (+0.16, +0.5)** |

## Decision

New defaults: **newcomers carry founder brains**, **about 4.5 children per
lifetime** (`Config.small_world(children=4.5)`), **partners up to 16 tiles apart**,
**fat stores up to 180**. Together: average population 12.7 to 21.3, final-year
population 6.3 to 18.0, days at the floor 5% to 1%, deepest generation 4.2 to 6.9,
births per person-year +37%, mood up. Life expectancy at birth falls 17 days (more
children born, some of whom die young). A lower mutation rate added nothing. Food
regrowth and the energy needed to bear a child weren't limits. Births still trail
deaths late in a run; strangers still make up the difference.
