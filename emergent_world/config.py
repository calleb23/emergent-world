"""All tunable numbers in one place, so experiments change config, not code.

The clock: 1 tick = 1 hour. Body needs are set on that clock (thirst kills in
about 10 days, hunger in about 2-3 weeks, poison acts within a day). Lifespans
vary by phase: short in prehistory so generations fly by, long in the real world.
"""

from dataclasses import dataclass, field

from emergent_world.world.items import DEFAULT_ITEMS, ItemKind

TICKS_PER_DAY = 24
TICKS_PER_YEAR = TICKS_PER_DAY * 365


def days(n: float) -> int:
    return int(round(n * TICKS_PER_DAY))


def years(n: float) -> int:
    return int(round(n * TICKS_PER_YEAR))


def format_time(ticks: int) -> str:
    """'year 2, day 140' style, for progress lines and the viewer."""
    year, rest = divmod(ticks, TICKS_PER_YEAR)
    return f"year {year + 1}, day {rest // TICKS_PER_DAY + 1}"


@dataclass
class Config:
    # World
    width: int = 64
    height: int = 64
    water_lakes: int = 12           # number of ponds scattered on the map
    lake_radius: tuple = (2, 4)     # min/max pond radius in tiles
    initial_item_density: float = 0.15    # share of grass tiles that start with an item
    regrow_chance: float = 0.0009         # per empty grass tile, per tick; sets how many agents food supports
    near_water: int = 3                   # tiles from water that count as damp ("near_water" items)
    dry_distance: int = 8                 # tiles from water beyond which it's dry ("dry" items)
    items: tuple = field(default_factory=lambda: DEFAULT_ITEMS)  # every kind of item: see world/items.py


    # Agents
    initial_agents: int = 50
    max_energy: float = 100.0
    max_water: float = 100.0
    max_health: float = 100.0
    max_carry: float = 5.0                # heaviest thing one person can lift
    carry_fatigue: float = 0.001          # extra tiredness per hour, per unit of weight carried
    energy_drain: float = 0.25      # per tick
    water_drain: float = 0.4        # per tick
    starvation_damage: float = 2.0  # health lost per tick at zero energy
    dehydration_damage: float = 3.0 # health lost per tick at zero water
    healing: float = 0.2            # health regained per tick when fed and watered
    lifespan: tuple = (days(33), days(50))  # min/max ticks before old age (prehistory scale)

    # Food and drink
    drink_amount: float = 40.0

    # Day and night, seasons, weather and sleep (see world/climate.py)
    winter_temperature: float = 2.0   # winter's base temperature (degrees C); colder burns more energy
    winter_growth: float = 0.25       # how fast things regrow in winter, relative to normal
    climate: bool = True            # False: endless clear daylight, no sleep (old behavior)
    fatigue_rate: float = 0.05      # tiredness gained per waking hour (exhausted after 20 hours)
    rest_rate: float = 0.12         # tiredness lost per hour asleep (about 8 hours of sleep)
    sleep_threshold: float = 0.6    # tired enough to fall asleep once it's dark
    wake_threshold: float = 0.4     # rested enough to get up once it's light
    restless_when_needy: bool = True   # too thirsty or hungry to fall asleep (until exhausted)
    remember_seen_water: bool = True   # people remember water they've seen, not just drunk at
    orphans_follow_kin: bool = True    # a child with no parent left keeps close to kin or a friend
    storm_wind_chance: float = 0.004   # per storm hour, chance wind tears apart an unreinforced shelter
    sleep_drain: float = 0.6        # hunger and thirst slow to this share while asleep
    sleep_healing: float = 2.0      # healing runs this many times faster while asleep
    exhaustion_damage: float = 0.5  # health lost per hour while awake and exhausted

    # Body: fat, aging, voice, grief
    max_fat: float = 180.0          # the most energy an agent can store as fat (enough to bank for lean weeks)
    store_fat_above: float = 0.85   # energy share above which spare energy is stored as fat
    fat_store_rate: float = 0.5     # energy per hour moved into fat (80% kept)
    burn_fat_below: float = 0.35    # energy share below which fat is burned
    fat_burn_rate: float = 1.0      # fat per hour burned back into energy
    old_age_from: float = 0.75      # share of lifespan after which agents grow frail
    hearing_range: int = 16         # tiles: relatives hear a dying cry this far away
    grief_hours: int = 24 * 4       # how long losing a relative weighs on someone
    grief_rest: float = 1.5         # how much more grieving agents want to sit still

    # Newcomers: strangers who wander in from beyond the edge of the world, bringing
    # new families to pair with. 0 = nobody ever arrives.
    newcomer_every_days: float = 30.0

    # The world's mechanics for things people might do (see behaviour.py)
    sticks_per_shelter: int = 4     # sticks dropped on one spot that make a shelter
    exposure_damage: float = 0.25   # health lost per hour caught out in bad weather or a cold night
    exposure_hunger: float = 1.3    # hunger multiplier while exposed (keeping warm)
    boredom_window: int = 48        # hours of positions that count toward boredom
    boredom_rise: float = 0.02      # boredom added per hour while lingering
    boredom_ease: float = 0.01      # boredom eased per hour while covering new ground

    # Social memory: who people know, and how close they are
    company_range: int = 3          # tiles: near enough to count as spending time together
    bond_per_hour: float = 0.004    # bond gained per waking hour spent near someone
    bond_fade: float = 0.995        # daily multiplier; bonds fade without contact
    close_bond: float = 0.5         # bond at which two people count as close

    # Learning within a lifetime: brains drift toward actions that felt good
    learning: bool = True
    learn_rate: float = 0.01
    # Feelings and people (agents/emotions.py).
    emotions: bool = True           # False: no fear, anger, loneliness or joy (for comparison runs)
    newcomers_from_living: bool = False  # True: strangers carry a living adult's learned brain; False: a
                                         # founder's. Founders win long-term (docs/experiments, round 3):
                                         # a tiny population's brains drift and degrade, and strangers
                                         # from outside bring fresh genes.
    fear_weight: float = 0.3        # how bad an hour of fear feels
    anger_weight: float = 0.15
    lonely_weight: float = 0.2
    loneliness_rate: float = 0.006  # per hour alone, for an average temperament
    lonely_pull: float = 1.0        # lonely people are drawn toward people they can see
    thirst_urge: float = 5.0        # beside water, urge to drink, at its strongest when parched (0 = off)
    hunger_urge: float = 5.0        # urge to bite what's underfoot, at its strongest when starving (0 = off)
    hit_damage: float = 4.0         # a bare-handed blow; something hard in hand adds to it
    call_carries_fear: bool = True  # a cry's tone gives away the caller's fear
    harm_aversion: float = 2.5      # innate reluctance to hit or rob, stronger toward the loved
    touch_reward: float = 0.4       # being comforted feels good, and so does comforting
    gift_reward: float = 0.3        # being given something feels good
    imitation: bool = True          # people learn by watching each other (agents/policy.py)
    imitation_rate: float = 0.003   # how strongly one sighting shifts the onlooker's brain
    imitation_payoff: float = 5.0   # how much a visible payoff (or hurt) scales the lesson
    imitation_skill: float = 0.15   # skills with no immediate payoff are still copied this much
    discount: float = 0.95          # how much the next hour's prospects count against the reward now
    pain_weight: float = 0.05       # bad feeling per point of health lost
    exposure_weight: float = 0.05   # bad feeling per hour caught out in the weather
    boredom_weight: float = 0.03    # bad feeling per hour, times boredom
    novelty_reward: float = 0.05    # good feeling for setting foot somewhere not seen lately

    # Senses and brain
    policy: str = "brain"           # "brain" or "random" (a baseline to compare against)
    vision_range: int = 8           # tiles each vision ray reaches
    action_selection: str = "argmax"  # "argmax": take the brain's top action; "sample": draw by probability
    exploration: float = 0.1        # argmax only: chance of a random action instead
    # Learning genes (agents/genes.py): learn_rate, imitation_rate and exploration
    # are inherited per person and can evolve.
    learning_genes: bool = True     # False: genes drift but have no effect (the control)
    gene_mutation: float = 0.1      # log-scale variation per child
    gene_founder_spread: float = 0.5   # log-scale spread among founders and their stand-ins

    # Reproduction and evolution (asexual for now; two parents comes later)
    maturity_fraction: float = 0.15 # share of average lifespan before an agent can reproduce
    reproduce_energy: float = 70.0  # energy needed to reproduce
    reproduce_water: float = 50.0   # water needed too: parched agents don't breed
    reproduce_cost_energy: float = 40.0
    reproduce_cost_water: float = 20.0
    cooldown_fraction: float = 0.10 # share of average lifespan between children
    two_parents: bool = True        # False: anyone can have children alone (old behavior)
    mate_range: int = 16            # tiles: how far apart partners can be (8 starved sparse populations of births)
    mating_pull: float = 2.5        # how strongly adults ready for children are drawn to people in sight
    father_cost_energy: float = 10.0
    child_energy: float = 60.0
    child_water: float = 60.0
    mutation_scale: float = 0.05    # size of random changes to inherited weights
    mutation_rate: float = 0.05     # share of weights changed per child; too high and good
                                    # brains slowly drift apart ("mutational meltdown")
    max_population: int = 1000      # safety cap; food should normally limit population first

    # Food memory (learning within a lifetime). See agents/memory.py.
    aversion_window: int = 48       # ticks: meals this recent get blamed for sickness
    sickness_aversion: float = 0.8  # aversion added to foods blamed for getting sick
    witness_aversion: float = 0.6   # added to foods a relative ate before dying of poison
    inedible_aversion: float = 0.3  # (unused since things that can't be eaten are simply known as useless)
    useless_penalty: float = 12.0   # how firmly agents refuse to bite what they know isn't food
    trust_gain: float = 0.15        # trust gained in a food each time it proves safe
    parent_trust: float = 0.25      # trust a child gains watching a parent eat a food
    trust_pull: float = 3.0         # how much trust draws a hungry agent to eat and to approach a food
    follow_pull: float = 3.0        # how strongly children keep close to their parent
    homing_pull: float = 2.5        # how strongly agents head back to remembered water or food
    learned_safety: float = 0.3     # share of aversion removed when a food proves safe
    aversion_fade: float = 0.995    # daily multiplier; aversion halves in about 140 days
    aversion_gain: float = 10.0     # starting value of the gene that turns aversion into not eating
    steer_strength: float = 0.5     # share of that pull used to steer away from foods in sight
    social_reassurance: float = 0.1   # share of wariness lost watching a relative eat that food
    desperation_below: float = 0.5  # below this share of energy, hunger starts overriding wariness
    aversion_gain_mutation: float = 0.5  # how much that gene varies between parent and child

    # Instincts: a brain file from `python -m emergent_world.instincts`. When set,
    # new agents start as mutated copies of it instead of random brains.
    instincts_path: str = ""

    # Founders: a population file from `python -m emergent_world.prehistory`.
    # When set, the world starts with these brains (and tops up from them).
    founders_path: str = ""
    founder_count: int = 0          # how many founders enter the world (0 = all of them)

    # Bootstrapping: early random brains die fast, so top the population up
    # until reproduction can sustain it. Most new agents are mutated copies
    # of the longest-lived brains so far; the rest are fresh random brains.
    min_population: int = 20
    hall_of_fame_size: int = 20     # top-up parents: the best of the recent deaths
    hall_of_fame_window: int = 200  # how many recent deaths count; old champions age out
    child_fitness: float = 100.0    # fitness = age at death + this per child
    reseed_from_best: float = 0.5   # share of top-up agents copied from the hall of fame

    # Garden-first curriculum: hunger and thirst drain slowly at the start and
    # ramp up to full strength, so blank brains survive long enough to breed.
    garden_start: float = 0.4       # drain multiplier at tick 0
    garden_ticks: int = 30000       # ticks to reach full difficulty (0 = no garden)

    def item(self, item_id: int) -> ItemKind | None:
        """The kind of item with this map id (0 = nothing)."""
        return self.items[item_id - 1] if 0 < item_id <= len(self.items) else None

    def item_id(self, look: str) -> int:
        """The map id of the item with this look (0 if there's none)."""
        for i, kind in enumerate(self.items, start=1):
            if kind.look == look:
                return i
        return 0

    def look_of(self, color) -> str:
        for kind in self.items:
            if kind.color == color:
                return kind.look
        return "something"

    # The two original plants, by name, for code and tests that use them directly.
    @property
    def food_color(self) -> tuple:
        return self.items[0].color

    @property
    def poison_color(self) -> tuple:
        return self.items[1].color

    @property
    def average_lifespan(self) -> float:
        return (self.lifespan[0] + self.lifespan[1]) / 2

    @property
    def maturity_age(self) -> int:
        return int(self.average_lifespan * self.maturity_fraction)

    @property
    def reproduce_cooldown(self) -> int:
        return int(self.average_lifespan * self.cooldown_fraction)

    def with_lifespan_years(self, average_years: float, spread: float = 0.2) -> "Config":
        """Set lifespans to average_years, give or take `spread` (0.2 = 20%)."""
        self.lifespan = (years(average_years * (1 - spread)), years(average_years * (1 + spread)))
        return self

    @classmethod
    def small_world(cls, people: int = 30, max_people: int = 80, children: float = 4.5,
                    years: float = 2.0) -> "Config":
        """The default world for following individual lives: a few founders, long
        lives, about `children` children per lifetime, and top-ups only to
        prevent extinction."""
        config = cls(garden_ticks=0, founder_count=people, initial_agents=people,
                     max_population=max_people, min_population=2).with_lifespan_years(years)
        # Children are spaced so a full life fits about `children` of them after adulthood.
        config.cooldown_fraction = (1 - config.maturity_fraction) / max(children, 0.1)
        return config
