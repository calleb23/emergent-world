# Baseline and ablations (2026-10-15)

8 worlds per batch, 2 simulated years each, `Config.small_world()` with the
prehistory founders. Code: commit `db825c1` (survival fixes on) unless noted.
Run with `python -m emergent_world.experiment run --name <name> --seeds 8 --years 2 --set ...`.

## The reference batch ("current": everything on)

| metric | mean | sd | min | max |
|---|---|---|---|---|
| alive_mean | 23.5 | 2.81 | 17.6 | 26.8 |
| alive_end | 8.38 | 3.93 | 3 | 15 |
| extinct | 0 | 0 | 0 | 0 |
| life_expectancy_days | 198 | 14.9 | 179 | 219 |
| births_per_person_year | 0.989 | 0.0848 | 0.859 | 1.08 |
| max_generation | 3.62 | 0.744 | 3 | 5 |
| share_dehydration | 0.298 | 0.0795 | 0.221 | 0.48 |
| share_starvation | 0.429 | 0.09 | 0.29 | 0.568 |
| share_poison | 0.189 | 0.026 | 0.151 | 0.219 |
| share_old_age | 0.0219 | 0.0149 | 0 | 0.0421 |
| mood_mean | -1.04 | 0.18 | -1.32 | -0.796 |
| discoveries | 5 | 0.926 | 3 | 6 |
| count_comfort | 381 | 118 | 202 | 612 |
| count_transmission | 65 | 13.2 | 37 | 82 |
| genome_diversity | 10.9 | 1.73 | 8.15 | 13.1 |
| action_entropy_bits | 3.1 | 0.0225 | 3.06 | 3.14 |
| share_doing | 0.174 | 0.00695 | 0.162 | 0.185 |
| skill_effects | 612 | 108 | 483 | 832 |
| established_made | 7.12 | 0.641 | 6 | 8 |
| new_established_late | 0.625 | 0.518 | 0 | 1 |
| cv_food | 0.405 | 0.0141 | 0.381 | 0.428 |
| cv_critter | 0.167 | 0.0294 | 0.122 | 0.211 |
| species_lost | 0 | 0 | 0 | 0 |

## What each part is worth

Each column turns one thing off (or, for `no-fixes`, all three survival fixes).

Reference: **current** (8 worlds). Each cell: difference from the reference (95% bootstrap interval); **bold** where the interval excludes zero.

| metric | current | no-fixes | no-restless | no-seen-water | no-orphan-kin | no-imitation | no-emotions | founder-newcomers | no-learning |
|---|---|---|---|---|---|---|---|---|---|
| alive_mean | 23.5 | -2.17 (-4.6, +0.46) | -1.51 (-4.2, +1.5) | **-5.26 (-8.4, -2.2)** | **-3.07 (-5.3, -0.57)** | -1.53 (-4.4, +1.3) | **-3.73 (-6.6, -0.51)** | -1.62 (-4.7, +1.8) | **-4.26 (-7.7, -0.77)** |
| life_expectancy_days | 198 | **-18.7 (-36, -2)** | -1.51 (-13, +10) | **-18.9 (-36, -3)** | -12.1 (-24, +0.00031) | +1.34 (-14, +18) | -13.6 (-29, +1.6) | -4.59 (-24, +13) | **-23.2 (-36, -10)** |
| births_per_person_year | 0.989 | +0.009 (-0.074, +0.094) | -0.00438 (-0.071, +0.063) | +0.0345 (-0.082, +0.15) | +0.01 (-0.068, +0.09) | -0.0634 (-0.14, +0.017) | +0.00975 (-0.054, +0.082) | -0.016 (-0.11, +0.079) | +0.0207 (-0.091, +0.13) |
| max_generation | 3.62 | -0.375 (-1.1, +0.38) | -0.25 (-0.88, +0.38) | **-0.625 (-1.2, -0.12)** | -0.375 (-1, +0.13) | -0.625 (-1.2, +0) | **-0.75 (-1.4, -0.12)** | -0.375 (-1.2, +0.5) | -0.25 (-1, +0.5) |
| share_dehydration | 0.298 | **+0.0867 (+0.0053, +0.16)** | +0.0346 (-0.037, +0.097) | **+0.0857 (+0.018, +0.14)** | +0.0112 (-0.074, +0.082) | +0.0113 (-0.058, +0.069) | +0.0131 (-0.065, +0.089) | -0.00462 (-0.075, +0.054) | -0.00501 (-0.069, +0.052) |
| share_starvation | 0.429 | -0.0479 (-0.15, +0.052) | -0.0017 (-0.069, +0.066) | **-0.0861 (-0.16, -0.015)** | -0.0186 (-0.094, +0.066) | +0.0101 (-0.07, +0.085) | -0.00643 (-0.1, +0.086) | -0.0046 (-0.074, +0.066) | -0.0361 (-0.1, +0.034) |
| share_poison | 0.189 | -0.0289 (-0.062, +0.0016) | -0.0116 (-0.048, +0.031) | **+0.0219 (+0.00072, +0.043)** | +0.0147 (-0.0091, +0.04) | +0.00269 (-0.023, +0.028) | +0.0116 (-0.022, +0.048) | +0.0164 (-0.0089, +0.04) | **+0.0729 (+0.029, +0.12)** |
| discoveries | 5 | -0.25 (-1.2, +0.75) | -0.25 (-1.1, +0.62) | -0.125 (-1, +0.75) | +0.25 (-0.5, +1) | **-0.875 (-1.6, -0.12)** | +0 (-1, +1) | -0.125 (-1, +0.75) | **-1.25 (-2.1, -0.38)** |
| count_transmission | 65 | **-17.2 (-30, -3.4)** | -11.1 (-24, +2.2) | **-24.1 (-35, -11)** | **-17.9 (-29, -6.1)** | **-65 (-73, -56)** | **-16.5 (-27, -4.2)** | **-14.4 (-27, -0.25)** | **-65 (-73, -56)** |
| count_comfort | 381 | -81.5 (-1.8e+02, +10) | -73.2 (-1.6e+02, +11) | **-107 (-2.1e+02, -11)** | **-112 (-1.9e+02, -30)** | -40 (-1.3e+02, +46) | **-102 (-2e+02, -4.9)** | -72.6 (-1.6e+02, +12) | -44.2 (-1.4e+02, +58) |
| mood_mean | -1.04 | -0.0269 (-0.16, +0.12) | +0.0296 (-0.1, +0.17) | -0.141 (-0.33, +0.032) | -0.132 (-0.31, +0.037) | +0.0343 (-0.1, +0.18) | **+0.742 (+0.63, +0.87)** | -0.0595 (-0.25, +0.11) | -0.0521 (-0.25, +0.15) |


`baseline` (commit `4cc38f2`, before the survival fixes) differs from `current` by
-2.2 alive (-4.6, +0.5), **-19 days life expectancy (-36, -2)** and **+8.7 points
of deaths from thirst (+0.5, +16)**.

## Findings

- **Remembering water you've only seen** is the strongest of the survival fixes:
  without it, 5.3 fewer people alive on average, 19 days shorter lives, and thirst
  back up to about 38% of deaths. Orphans keeping to kin adds about 3 people alive.
  Being too parched to fall asleep shows no clear effect on its own.
- **Lifetime learning matters**: without it, 4.3 fewer alive, 23 days shorter lives,
  7 points more deaths from poison and fewer discoveries. (In this batch turning
  learning off also switched imitation off; fixed since, so they're independent.)
- **Imitation's survival effect is not established.** The earlier 4-seed result
  (8 to 15 survivors) doesn't hold up: alive -1.5 (-4.4, +1.3) without it. It does
  carry skills (65 transmissions per world) and slightly raises discoveries.
- **Emotions help**: without them, 3.7 fewer alive and shallower family trees.
  Mood reads higher without them only because fear, anger and loneliness count
  against mood.
- **Newcomers from living brains** vs founder brains: no clear difference yet.
- Starvation is now the main cause of death (43%). Diagnosis: people starve beside
  plenty of safe food (median 11 safe items within 8 tiles); hungry people on food
  ate it only 14-30% of the time, because of wrongly blamed staple foods and the
  pull to follow parents and seek company. Addressed in the next changes.
- With 8 seeds, intervals on `alive_mean` are about ±3 people (sd ~2.8): enough to
  see effects of ~15% or more. Use 16 seeds for smaller ones.
