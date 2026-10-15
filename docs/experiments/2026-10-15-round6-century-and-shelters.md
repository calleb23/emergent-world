# Round 6: a century with everything, and missing shelters (2026-10-15)

## 100 years, seed 0 (code `821f3a3`)

`python -m emergent_world.century --years 100`. Replay of the final two years:
https://claude.ai/artifact/YFpd1emvdtn5mbdmhdtf17 (version 2).

- Population: 22-30 on average in every 20-year block (lowest 5, peak 56); 3,947
  people over the century, 2,755 births; family trees up to 15 generations deep.
- Deaths: starvation 44% (winter), poison 24%, thirst 11%, old age 7.5%.
- Social life: 2,061 skills passed between people, 22,633 comforts, 1,629 gifts,
  177 blows and 44 thefts.
- Firsts: corded stick (day 178), fire by rubbing (year 7), a log and a cracked nut
  (years 10-11), the first shelter and keeping a fire going (year 13), cooking (year
  38), a shelter lashed with a vine (year 92).

## Shelters nearly vanished

The century world built almost no lasting shelters (0-1 at a time), against 118 in
the pre-physics century run. It wasn't the storm wind: with wind 8 times weaker
(`storm_wind_chance=0.0005`), six-year worlds built none either, identical to the
default. In year 90 the map held 547 stick piles, all of 1-3 sticks (a shelter needs
4), and only 235 loose sticks among 69 kinds of item, with fires and crafting using
them too. Letting branches and poles pile up like sticks gave 2 of 8 six-year worlds
a shelter at some point (none before), with no effect on survival. Shelter-building
is an open question: more sticks in the world, fewer needed, or wait for it to emerge.
