"""Day and night, seasons and weather.

Everything here follows the hourly clock (1 tick = 1 hour):

- Light rises at dawn (5-7) and fades at dusk (17-19). At night agents see only
  a few tiles.
- A year has four 91-day seasons. Spring grows fastest; winter barely grows,
  and its cold burns energy. Summer heat makes agents thirsty faster.
- Weather changes every few hours, with odds that depend on the season: clear,
  cloudy, rain, storm and fog, with snow instead of rain when it's cold.
  Rain eases thirst and helps plants grow; storms, fog and snow cut visibility.
"""

from dataclasses import dataclass

SEASONS = ("spring", "summer", "autumn", "winter")
WEATHER = ("clear", "cloudy", "rain", "storm", "fog", "snow")


@dataclass(frozen=True)
class WeatherEffect:
    visibility: float   # multiplies how far agents can see
    growth: float       # multiplies how fast items regrow
    thirst: float       # multiplies water drain
    hunger: float       # multiplies energy drain
    warmth: float       # added to the temperature (degrees C)


EFFECTS = {
    "clear":  WeatherEffect(1.0, 1.0, 1.0, 1.0, +3),
    "cloudy": WeatherEffect(0.9, 1.0, 0.9, 1.0, 0),
    "rain":   WeatherEffect(0.7, 1.6, 0.5, 1.0, -2),
    "storm":  WeatherEffect(0.4, 1.3, 0.6, 1.2, -4),
    "fog":    WeatherEffect(0.4, 1.0, 0.9, 1.0, -1),
    "snow":   WeatherEffect(0.5, 0.3, 0.9, 1.3, -4),
}

# Season: (base temperature, growth, chance per weather kind when it changes)
SEASON_TRAITS = {
    "spring": (14, 1.4, {"clear": 3, "cloudy": 3, "rain": 3, "storm": 1, "fog": 1}),
    "summer": (25, 1.0, {"clear": 6, "cloudy": 2, "rain": 1, "storm": 1, "fog": 0.3}),
    "autumn": (12, 0.8, {"clear": 2, "cloudy": 3, "rain": 3, "storm": 1.5, "fog": 2}),
    "winter": (2, 0.25, {"clear": 3, "cloudy": 3, "rain": 2, "storm": 1, "fog": 1.5}),
}


class Climate:
    def __init__(self, rng, ticks_per_day: int = 24, days_per_season: int = 91,
                 average_weather_hours: float = 10.0, winter_temperature: float = 2.0,
                 winter_growth: float = 0.25):
        self.rng = rng
        # Each season's traits, with winter's cold and growth adjustable.
        self.traits = dict(SEASON_TRAITS)
        _, _, odds = SEASON_TRAITS["winter"]
        self.traits["winter"] = (winter_temperature, winter_growth, odds)
        self.ticks_per_day = ticks_per_day
        self.days_per_season = days_per_season
        self.change_chance = 1.0 / average_weather_hours
        self.weather = "clear"
        self.tick_count = 0

    # --- the calendar --------------------------------------------------------

    @property
    def hour(self) -> int:
        return self.tick_count % self.ticks_per_day

    @property
    def season(self) -> str:
        day = self.tick_count // self.ticks_per_day
        return SEASONS[(day // self.days_per_season) % 4]

    @property
    def light(self) -> float:
        """0.15 at night, 1.0 by day, ramping through dawn and dusk."""
        h = self.hour + 0.5
        if 7 <= h <= 17:
            return 1.0
        if 5 <= h < 7:
            return 0.15 + 0.85 * (h - 5) / 2
        if 17 < h <= 19:
            return 1.0 - 0.85 * (h - 17) / 2
        return 0.15

    @property
    def is_night(self) -> bool:
        return self.light < 0.5

    # --- weather and its effects --------------------------------------------

    @property
    def effect(self) -> WeatherEffect:
        return EFFECTS[self.weather]

    @property
    def temperature(self) -> float:
        base = self.traits[self.season][0]
        daily_swing = 5.0 * (self.light - 0.575) / 0.425  # about +5 by day, -5 at night
        return base + daily_swing + self.effect.warmth

    @property
    def growth(self) -> float:
        return self.traits[self.season][1] * self.effect.growth

    @property
    def visibility(self) -> float:
        return self.light * self.effect.visibility

    @property
    def thirst(self) -> float:
        heat = 1.0 + max(0.0, self.temperature - 25.0) * 0.05   # +5% per degree over 25
        return self.effect.thirst * heat

    @property
    def hunger(self) -> float:
        cold = 1.0 + max(0.0, 8.0 - self.temperature) * 0.04    # +4% per degree under 8
        return self.effect.hunger * cold

    def tick(self):
        """Advance one hour; the weather sometimes changes."""
        self.tick_count += 1
        if self.rng.random() < self.change_chance:
            odds = self.traits[self.season][2]
            kinds = list(odds)
            weights = [odds[k] for k in kinds]
            total = sum(weights)
            pick = kinds[int(self.rng.choice(len(kinds), p=[w / total for w in weights]))]
            # Precipitation falls as snow when it's cold enough.
            if pick in ("rain", "storm") and self.traits[self.season][0] + EFFECTS[pick].warmth <= 1:
                pick = "snow"
            self.weather = pick

    def describe(self) -> str:
        return f"{self.season}, {self.weather}, {self.temperature:.0f}°C"
