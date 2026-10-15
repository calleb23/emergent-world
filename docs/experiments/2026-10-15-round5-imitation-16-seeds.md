# Round 5: does imitation help? (16 seeds, 4 years, 2026-10-15)

Commit `d51f134`. Reference: `imitation=False`.

| metric | imit16-off | imit16-on |
|---|---|---|
| alive_mean | 28.2 | +0.431 (-3.1, +3.9) |
| alive_last_year | 24.2 | +0.436 (-4, +4.9) |
| floor_share | 0 | +0 (+0, +0) |
| net_growth_late | -12.4 | +0.406 (-2.2, +3) |
| life_expectancy_days | 235 | -0.869 (-11, +9.9) |
| births_per_person_year | 1.17 | -0.00569 (-0.073, +0.058) |
| max_generation | 5.38 | +0.25 (-0.62, +1.1) |
| share_dehydration | 0.111 | +0.0329 (-0.0016, +0.067) |
| share_starvation | 0.538 | -0.0273 (-0.075, +0.016) |
| share_poison | 0.237 | -0.00204 (-0.024, +0.021) |
| discoveries | 4.94 | **+0.75 (+0.19, +1.4)** |
| count_transmission | 0 | **+112 (+95, +1.3e+02)** |
| count_comfort | 845 | +83 (-1.8e+02, +4.3e+02) |
| mood_mean | -0.955 | -0.0236 (-0.11, +0.057) |

With 16 worlds a side, imitation has **no measurable effect on survival** (alive
+0.4, interval -3.1 to +3.9) and **reliably raises discoveries** (+0.75 of the tracked
world firsts, interval +0.19 to +1.4), passing about 112 skills between people per
world. Imitation spreads know-how and helps the world find new things; it doesn't keep
people alive. This replaces the early 4-seed claim (8 to 15 survivors), which was noise.
