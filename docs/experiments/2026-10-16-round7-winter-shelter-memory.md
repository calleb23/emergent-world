# Round 7: milder winters, shelter, teaching, calls and a hippocampus (2026-10-16)

8 worlds per batch, 6 years each.

## Milder winters

Winter regrowth and temperature: now 0.25 at 2 degrees; mild 0.6 at 6; milder 0.8 at 8.
Open world (strangers arrive) and closed world (`newcomer_every_days=0`):

```
batch                   alive      last yr   floor%  net/yr late  max gen
w-now-open             27.7         26.6         0%       -12.1       7.1
w-mild-open            46.9*        40.5*        0%       -15.7       8.8*
w-milder-open          47.7*        35.8         0%       -19.2*      8.9*

batch                   alive      last yr   floor%  net/yr late  max gen
w-now-closed           14.2          3.9        27%        -3.0       6.2
w-mild-closed          28.2*        18.6*       10%        -4.2       8.8
w-milder-closed        31.9*        19.5*        2%*       -6.3       8.2
```

Mild winters raise the open world's population from about 28 to about 47, life
expectancy by about 25 days, and family depth by about 1.7 generations. In a closed
world the milder setting cuts days at the two-person floor from 27% to 2%. The milder
setting (0.8 at 8 degrees) is the new default.

## Shelter drives, teaching, remembered calls (commit `6b59d45`)

Shelter-seeking and building drives, teaching, and calls remembered for six hours
each made no measurable difference on their own: shelters stayed at 0-2 per world,
because building only starts once someone has seen a shelter and almost no one had.

## Natural shelter and call incentives (commit `6e6a5f7`)

Rock overhangs and thick pines now give cover. With the shelter drives, the most
shelters standing at once rose from 0.9 to 6.1 per world (final year: 0.1 to 2.8),
both clear. Curious, needy listeners now move toward calls (52%, from 49%), and about
2,500 calls per world led someone to food or water, but the sounds still carry
almost no information about the caller's situation (about 0.001 bits).

## A hippocampus (commit `ebb6b6f`)

| metric | v7 | v7-no-hippocampus | v7-no-replay | v7-no-emulation |
|---|---|---|---|---|
| alive_mean | 45.3 | +2.37 (-9.6, +15) | +4.11 (-6.5, +15) | +4.96 (-6.5, +16) |
| alive_last_year | 37.9 | +2.99 (-12, +19) | +8.87 (-5.1, +23) | +6.18 (-8.3, +20) |
| floor_share | 0 | +0 (+0, +0) | +0 (+0, +0) | +0 (+0, +0) |
| net_growth_late | -15.1 | +1.71 (-1.2, +4.4) | +3.13 (-1, +7.8) | -0.0412 (-2.5, +2.4) |
| life_expectancy_days | 283 | -1.09 (-17, +16) | -6.18 (-26, +15) | +5.5 (-12, +23) |
| births_per_person_year | 1.11 | +0.00188 (-0.052, +0.06) | +0.0394 (-0.03, +0.11) | -0.00238 (-0.054, +0.051) |
| max_generation | 9.12 | -0.625 (-2.8, +1.8) | -0.25 (-1.9, +1.5) | +0.25 (-1.6, +2.1) |
| share_dehydration | 0.208 | **-0.0912 (-0.13, -0.043)** | **-0.116 (-0.15, -0.079)** | +0.00159 (-0.042, +0.044) |
| share_starvation | 0.449 | +0.0339 (-0.015, +0.082) | +0.0129 (-0.024, +0.052) | **-0.0278 (-0.056, -0.00015)** |
| share_poison | 0.215 | +0.0232 (-0.00039, +0.045) | **+0.0628 (+0.032, +0.093)** | +0.00503 (-0.015, +0.024) |
| discoveries | 7.88 | **-1.12 (-2, -0.38)** | -0.375 (-1.5, +0.5) | +0.25 (-0.62, +1.1) |
| count_transmission | 799 | -144 (-3.5e+02, +65) | -130 (-3.3e+02, +60) | +46.4 (-1.7e+02, +2.6e+02) |
| count_comfort | 5.16e+04 | **+7.39e+04 (+1.4e+04, +1.4e+05)** | **+8.89e+04 (+3.3e+04, +1.6e+05)** | +1.17e+04 (-1.3e+04, +3.6e+04) |
| mood_mean | -0.588 | +0.0502 (-0.057, +0.16) | +0.0264 (-0.07, +0.12) | -0.0163 (-0.13, +0.099) |

| | everything on | no hippocampus | no sleep replay | no envy of others' shelter |
|---|---|---|---|---|
| most shelters at once | **15.8** | 5.5 | 6.3 | 16.8 |
| shelters standing in the final year | **9.1** | 2.6 | 2.9 | 10.9 |
| lessons taught | 2,855 | 1,687 | 1,774 | 3,232 |
| calls that led to food or water | 3,834 | 2,472 | 2,550 | 3,990 |

- **Sleep replay is what turns on shelter-building**: without it, shelters fall back
  to the no-hippocampus level. Replaying the day's experience at night teaches the
  brain to gather, carry and pile wood.
- The hippocampus also raises discoveries by about one per world (clear).
- **Replay raises deaths from thirst** (21% of deaths, against 12% without the
  hippocampus and 9% without replay) while lowering deaths from poison by 6 points.
  Population differences are within the noise.
- Seeing others sheltered (emulation) adds nothing yet: the cold itself already
  makes people want shelter.

## Replay made people walk away from water, and the fix (commit `faebbf5`)

Sleep replay trained brains to value wandering above drinking: thirsty people beside
water drank 6-11% of the time (29% without replay), because the learned value of
moving (about 19) outgrew drinking (about 12) while the built-in thirst urge stayed
at 3-5. Replaying only moments that clearly felt good or bad didn't fix it; valuing
what came next by the action actually taken made drinking look worse still. A thirst
urge that stays strong relative to learned values (15, was 5) restored drinking
(80-100% when parched beside water).

Reference `v9` = current code (thirst urge 15, replay 4 per sleeping hour); `v7` = the
previous run (thirst urge 5):

| metric | v9 | v9-no-replay | v9-replay2 | v7 |
|---|---|---|---|---|
| alive_mean | 51.1 | +0.793 (-9.9, +12) | -0.303 (-13, +12) | -5.83 (-17, +5.3) |
| alive_last_year | 50 | -8.07 (-21, +5) | -4.29 (-20, +11) | -12.1 (-26, +1.7) |
| floor_share | 0 | +0 (+0, +0) | +0 (+0, +0) | +0 (+0, +0) |
| net_growth_late | -12.8 | -2.58 (-8.7, +3.5) | -0.916 (-6, +4.1) | -2.25 (-6.6, +2.2) |
| life_expectancy_days | 305 | -16.1 (-33, +2) | -14.1 (-30, +3.3) | **-22.4 (-38, -5)** |
| births_per_person_year | 1.04 | +0.0543 (-0.018, +0.12) | +0.0448 (-0.016, +0.1) | **+0.0735 (+0.0066, +0.13)** |
| max_generation | 7.88 | +0.25 (-0.75, +1.2) | +1.12 (-0.25, +2.5) | +1.25 (-0.38, +2.9) |
| share_dehydration | 0.0686 | +0.0111 (-0.018, +0.042) | -0.00489 (-0.027, +0.017) | **+0.139 (+0.11, +0.17)** |
| share_starvation | 0.49 | -0.0257 (-0.082, +0.029) | -0.00504 (-0.092, +0.073) | -0.0406 (-0.09, +0.0086) |
| share_poison | 0.231 | **+0.0393 (+0.015, +0.065)** | +0.0223 (-0.0085, +0.053) | -0.0158 (-0.038, +0.0084) |
| discoveries | 7.5 | -0.375 (-1, +0.25) | -0.125 (-0.75, +0.5) | +0.375 (-0.38, +1.1) |
| count_transmission | 854 | **-180 (-3.6e+02, -2.7)** | -35.4 (-2.6e+02, +1.9e+02) | -54.5 (-2.7e+02, +1.6e+02) |
| count_comfort | 7.38e+04 | **+9.64e+04 (+4.4e+04, +1.5e+05)** | +2.51e+04 (-8.4e+03, +5.9e+04) | -2.22e+04 (-4.4e+04, +1.2e+03) |
| mood_mean | -0.508 | -0.0293 (-0.15, +0.088) | -0.0714 (-0.23, +0.076) | -0.0807 (-0.19, +0.024) |

| | v9 | no replay | replay 2/h | v7 |
|---|---|---|---|---|
| most shelters at once | **18.3** | 6.1 | 16.0 | 15.8 |
| shelters standing in the final year | **11.9** | 2.8 | 10.0 | 9.1 |
| lessons taught | 3,209 | 1,797 | 2,937 | 2,855 |
| calls that led to food or water | 4,516 | 2,681 | 3,954 | 3,834 |

Thirst falls from 21% of deaths to 7%, and life expectancy rises by 22 days (both
clear against `v7`). Replay still triples shelter-building (clear against no replay).
