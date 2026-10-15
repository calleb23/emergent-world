"""Food memory: learning within a lifetime what's not worth eating.

Built-in wiring, the way real animals have it: get sick, and the foods you ate
recently become unappealing (taste aversion). What's learned is *which* foods,
never *how* to avoid them. Memory is keyed only by what a food looks like
(its color), never by what it really is.

Three ways a food's aversion changes:
- Sickness: foods eaten in the last couple of days become aversive.
- Learned safety: a food eaten without getting sick afterwards becomes trusted,
  so the safe food eaten the same day as the poison doesn't stay blamed.
- Watching kin: an agent remembers what it saw relatives eat nearby. If it then
  sees one of them die of poison, those foods become aversive too.

Aversion fades slowly unless something refreshes it.
"""

from dataclasses import dataclass, field

# How the agent came to avoid something, for measuring the poison-plant test.
NAIVE = "naive"
GOT_SICK = "got_sick"
WITNESSED = "witnessed"


@dataclass
class FoodMemory:
    aversion: dict = field(default_factory=dict)      # color -> 0..1
    meals: list = field(default_factory=list)         # [tick, color] still awaiting a verdict
    seen_kin_meals: list = field(default_factory=list)  # (tick, eater id, color)
    learned_from: set = field(default_factory=set)    # {GOT_SICK, WITNESSED}

    def level(self, color) -> float:
        return self.aversion.get(color, 0.0)

    def record_meal(self, tick: int, color):
        self.meals.append([tick, color])

    def got_sick(self, tick: int, window: int, strength: float):
        """Sickness started: blame what was eaten recently."""
        blamed = [color for t, color in self.meals if tick - t <= window]
        for color in set(blamed):
            self.aversion[color] = min(1.0, self.level(color) + strength)
        self.meals = [m for m in self.meals if tick - m[0] > window]
        if blamed:
            self.learned_from.add(GOT_SICK)

    def settle_meals(self, tick: int, window: int, safety: float):
        """Meals that caused no sickness within the window count as safe."""
        while self.meals and tick - self.meals[0][0] > window:
            _, color = self.meals.pop(0)
            if color in self.aversion:
                self.aversion[color] *= (1.0 - safety)

    def saw_kin_eat(self, tick: int, eater_id: int, color):
        self.seen_kin_meals.append((tick, eater_id, color))

    def saw_kin_die_of_poison(self, tick: int, eater_id: int, window: int, strength: float):
        blamed = {color for t, who, color in self.seen_kin_meals
                  if who == eater_id and tick - t <= window}
        for color in blamed:
            self.aversion[color] = min(1.0, self.level(color) + strength)
        if blamed:
            self.learned_from.add(WITNESSED)

    def forget(self, tick: int, window: int, fade: float):
        """Called once a day: aversion fades, old observations are dropped."""
        for color in list(self.aversion):
            self.aversion[color] *= fade
            if self.aversion[color] < 0.01:
                del self.aversion[color]
        self.seen_kin_meals = [m for m in self.seen_kin_meals if tick - m[0] <= window]

    @property
    def how_learned(self) -> str:
        if WITNESSED in self.learned_from:
            return WITNESSED
        if GOT_SICK in self.learned_from:
            return GOT_SICK
        return NAIVE
